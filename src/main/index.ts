import { app, BrowserWindow, dialog, ipcMain, Menu } from 'electron'
import { join } from 'path'
import { buildMenu, focusOrShow } from './menu'
import { Sidecar } from './sidecar'
import { IPC } from '../shared/types'
import type { DatasetSummary, OutputObject, SidecarStatus, WindowName } from '../shared/types'

// electron-vite sets this in dev; undefined in a packaged build.
const RENDERER_URL = process.env['ELECTRON_RENDERER_URL']

const windows: Record<WindowName, BrowserWindow | null> = {
  dataeditor: null,
  viewer: null,
  syntax: null
}

const sidecar = new Sidecar()

function loadEntry(win: BrowserWindow, entry: WindowName): void {
  if (RENDERER_URL) {
    void win.loadURL(`${RENDERER_URL}/${entry}/index.html`)
  } else {
    void win.loadFile(join(__dirname, `../renderer/${entry}/index.html`))
  }
}

function createWindow(entry: WindowName, opts: Electron.BrowserWindowConstructorOptions): BrowserWindow {
  const win = new BrowserWindow({
    width: 1000,
    height: 700,
    show: false,
    ...opts,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  })
  loadEntry(win, entry)
  win.once('ready-to-show', () => win.show())
  win.webContents.on('did-fail-load', (_e, code, desc, url) =>
    console.error(`[win] ${entry} did-fail-load ${code} ${desc} ${url}`)
  )
  return win
}

function showWindow(name: WindowName): void {
  const win = windows[name]
  if (win && !win.isDestroyed()) focusOrShow(win)
}

function broadcast(channel: string, payload: unknown): void {
  for (const win of Object.values(windows)) {
    if (win && !win.isDestroyed()) win.webContents.send(channel, payload)
  }
}

function sendToViewer(objects: OutputObject[]): void {
  const viewer = windows.viewer
  if (viewer && !viewer.isDestroyed()) {
    viewer.webContents.send(IPC.outputAppend, objects)
  }
}

function createAllWindows(): void {
  // Data Editor — main window. Closing it quits the app.
  windows.dataeditor = createWindow('dataeditor', {
    title: 'Untitled1 [DataSet0] - IBM SPSS Statistics Data Editor',
    width: 1100,
    height: 720
  })
  windows.dataeditor.on('closed', () => {
    windows.dataeditor = null
    app.quit()
  })

  windows.viewer = createWindow('viewer', {
    title: 'Output1 - IBM SPSS Statistics Viewer',
    width: 1000,
    height: 720,
    x: 120,
    y: 90
  })
  windows.viewer.on('closed', () => (windows.viewer = null))

  windows.syntax = createWindow('syntax', {
    title: 'Syntax1 - IBM SPSS Statistics Syntax Editor',
    width: 820,
    height: 560,
    x: 200,
    y: 150
  })
  windows.syntax.on('closed', () => (windows.syntax = null))
}

function broadcastDataset(summary: DatasetSummary): void {
  const de = windows.dataeditor
  if (de && !de.isDestroyed()) de.webContents.send(IPC.datasetChanged, summary)
}

async function openViaDialog(): Promise<DatasetSummary | null> {
  const de = windows.dataeditor ?? undefined
  const res = await dialog.showOpenDialog(de as BrowserWindow, {
    title: 'Open Data',
    properties: ['openFile'],
    filters: [
      { name: 'SPSS Statistics (*.sav)', extensions: ['sav'] },
      { name: 'SPSS Portable (*.por)', extensions: ['por'] },
      { name: 'Stata (*.dta)', extensions: ['dta'] },
      { name: 'Excel (*.xlsx)', extensions: ['xlsx'] },
      { name: 'CSV (*.csv)', extensions: ['csv'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  })
  if (res.canceled || res.filePaths.length === 0) return null
  const summary = (await sidecar.request('dataset.open', { path: res.filePaths[0] })) as DatasetSummary
  broadcastDataset(summary)
  showWindow('dataeditor')
  return summary
}

async function saveViaDialog(): Promise<{ ok: boolean; path: string } | null> {
  const de = windows.dataeditor ?? undefined
  const res = await dialog.showSaveDialog(de as BrowserWindow, {
    title: 'Save Data As',
    filters: [
      { name: 'SPSS Statistics (*.sav)', extensions: ['sav'] },
      { name: 'CSV (*.csv)', extensions: ['csv'] },
      { name: 'Excel (*.xlsx)', extensions: ['xlsx'] }
    ]
  })
  if (res.canceled || !res.filePath) return null
  const out = (await sidecar.request('dataset.save', { path: res.filePath })) as { ok: boolean; path: string }
  return out
}

async function newDataset(): Promise<DatasetSummary> {
  const summary = (await sidecar.request('dataset.new', {})) as DatasetSummary
  broadcastDataset(summary)
  showWindow('dataeditor')
  return summary
}

function wireDatasetIpc(): void {
  ipcMain.handle(IPC.ds.new, () => newDataset())
  ipcMain.handle(IPC.ds.openDialog, () => openViaDialog())
  ipcMain.handle(IPC.ds.open, async (_e, path: string) => {
    const summary = (await sidecar.request('dataset.open', { path })) as DatasetSummary
    broadcastDataset(summary)
    return summary
  })
  ipcMain.handle(IPC.ds.save, async () => {
    try {
      return (await sidecar.request('dataset.save', {})) as { ok: boolean; path: string }
    } catch (err) {
      return { error: String(err instanceof Error ? err.message : err) }
    }
  })
  ipcMain.handle(IPC.ds.saveAs, () => saveViaDialog())
  ipcMain.handle(IPC.ds.getRows, (_e, p) => sidecar.request('dataset.getRows', p))
  ipcMain.handle(IPC.ds.setCell, (_e, p) => sidecar.request('dataset.setCell', p))
  ipcMain.handle(IPC.ds.setVariableMeta, (_e, p) => sidecar.request('dataset.setVariableMeta', p))
  ipcMain.handle(IPC.ds.insertVariable, (_e, p) => sidecar.request('dataset.insertVariable', p))
  ipcMain.handle(IPC.ds.deleteVariable, (_e, p) => sidecar.request('dataset.deleteVariable', p))
  ipcMain.handle(IPC.ds.insertCase, (_e, p) => sidecar.request('dataset.insertCase', p))
  ipcMain.handle(IPC.ds.deleteCase, (_e, p) => sidecar.request('dataset.deleteCase', p))
}

function wireIpc(): void {
  wireDatasetIpc()
  ipcMain.handle(IPC.syntaxExecute, async (_evt, text: string): Promise<OutputObject[]> => {
    try {
      const result = (await sidecar.request('syntax.execute', { text })) as OutputObject[]
      const objects = Array.isArray(result) ? result : []
      sendToViewer(objects)
      showWindow('viewer')
      return objects
    } catch (err) {
      // Sidecar down / crashed mid-request: surface as an Error object rather
      // than a hung promise, and still route it to the Viewer.
      const errObj: OutputObject[] = [{ type: 'Error', text: `Execution failed: ${String(err instanceof Error ? err.message : err)}` }]
      sendToViewer(errObj)
      showWindow('viewer')
      return errObj
    }
  })

  ipcMain.handle(IPC.sidecarStatusGet, (): SidecarStatus => sidecar.currentStatus)

  ipcMain.on(IPC.windowShow, (_evt, name: WindowName) => showWindow(name))
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(
    buildMenu({
      showWindow,
      fileNew: () => void newDataset(),
      fileOpen: () => void openViaDialog(),
      fileSave: () => {
        void sidecar
          .request('dataset.save', {})
          .catch(() => saveViaDialog())
      },
      fileSaveAs: () => void saveViaDialog()
    })
  )
  wireIpc()
  createAllWindows()

  sidecar.on('status', (status: SidecarStatus) => {
    broadcast(IPC.sidecarStatusEvent, status)
    if (status.state === 'down' && status.detail) {
      // Make crashes visible in the Viewer, per PHASE-0 crash handling.
      sendToViewer([{ type: 'Error', text: status.detail }])
    }
  })
  sidecar.start()

  if (process.env.SPSS_SELFTEST) void runSelfTest()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createAllWindows()
  })
})

// Headless end-to-end checks used for automated verification (the GUI is not
// driven). Phase 0: Syntax -> Viewer round trip. Phase 1 (SPSS_SELFTEST_SAV):
// open a .sav in the Data Editor and read the rendered grid DOM.
async function runSelfTest(): Promise<void> {
  const done = (msg: string): void => {
    console.log(`[selftest] ${msg}`)
    app.quit()
  }
  try {
    await Promise.all([whenLoaded(windows.syntax!), whenLoaded(windows.viewer!), whenLoaded(windows.dataeditor!)])
    await until(() => sidecar.currentStatus.state === 'ready', 10000)

    if (process.env.SPSS_SELFTEST_SAV) {
      await runSelfTestPhase1(process.env.SPSS_SELFTEST_SAV, done)
      return
    }

    const syntax = windows.syntax!
    const viewer = windows.viewer!
    await syntax.webContents.executeJavaScript(`window.spss.execute("TITLE 'hello'.")`)
    await syntax.webContents.executeJavaScript(`window.spss.execute("FREQUENCIES x.")`)
    await new Promise((r) => setTimeout(r, 400))
    const title = await viewer.webContents.executeJavaScript(
      `document.querySelector('.out-title')?.textContent ?? null`
    )
    const error = await viewer.webContents.executeJavaScript(
      `document.querySelector('.out-error')?.textContent ?? null`
    )
    const pass = title === 'hello' && typeof error === 'string' && error.includes('FREQUENCIES x.')
    done(`title=${JSON.stringify(title)} error=${JSON.stringify(error)} -> ${pass ? 'PASS' : 'FAIL'}`)
  } catch (err) {
    done(`ERROR ${String(err)}`)
  }
}

async function runSelfTestPhase1(sav: string, done: (m: string) => void): Promise<void> {
  const de = windows.dataeditor!
  const ev = (js: string): Promise<any> => de.webContents.executeJavaScript(js)
  const results: string[] = []
  const check = (name: string, ok: boolean, got: unknown): void => {
    results.push(`${name}:${ok ? 'PASS' : 'FAIL'}${ok ? '' : `(${JSON.stringify(got)})`}`)
  }

  // Open the file through the real renderer API; broadcast updates the store.
  await ev(`window.spss.ds.open(${JSON.stringify(sav)})`)
  await until2(async () => (await ev(`document.querySelectorAll('.row').length`)) > 0, 8000)

  const heads: string[] = await ev(`Array.from(document.querySelectorAll('.col-head')).map(e=>e.textContent)`)
  check('varnames', heads.slice(0, 5).join(',') === 'id,gender,income,agree,sname', heads)

  const row0: string[] = await ev(
    `Array.from(document.querySelectorAll('.row')[0].querySelectorAll('.cell')).map(c=>c.textContent)`
  )
  check('rawvalues', row0[0] === '1' && row0[1] === '1' && row0[2] === '50000' && row0[4] === 'al', row0)

  // Toggle value labels and re-read.
  await ev(`document.querySelector('.toggle').click()`)
  await until2(async () => {
    const c: string[] = await ev(`Array.from(document.querySelectorAll('.row')[0].querySelectorAll('.cell')).map(c=>c.textContent)`)
    return c[1] === 'Male'
  }, 5000)
  const row0lab: string[] = await ev(
    `Array.from(document.querySelectorAll('.row')[0].querySelectorAll('.cell')).map(c=>c.textContent)`
  )
  check('valuelabels', row0lab[1] === 'Male' && row0lab[3] === 'Strongly disagree', row0lab)

  // Switch to Variable View.
  await ev(`Array.from(document.querySelectorAll('.de-tab')).find(b=>b.textContent==='Variable View').click()`)
  await until2(async () => (await ev(`document.querySelectorAll('.vv th').length`)) > 0, 5000)
  const thCount: number = await ev(`document.querySelectorAll('.vv th').length`)
  check('vv_columns', thCount === 12, thCount) // rownum + 11
  const genderMissing: string = await ev(
    `(()=>{const rows=[...document.querySelectorAll('.vv tbody tr')];
       const r=rows.find(tr=>tr.querySelector('input')&&tr.querySelector('input').value==='gender');
       return r? r.querySelectorAll('.button-cell button')[2].textContent : null;})()`
  )
  check('vv_missing', String(genderMissing).includes('9'), genderMissing)
  const genderValues: string = await ev(
    `(()=>{const rows=[...document.querySelectorAll('.vv tbody tr')];
       const r=rows.find(tr=>tr.querySelector('input')&&tr.querySelector('input').value==='gender');
       return r? r.querySelectorAll('.button-cell button')[1].textContent : null;})()`
  )
  check('vv_valuelabels', String(genderValues).includes('Male'), genderValues)

  const pass = results.every((r) => r.includes('PASS'))
  done(`${pass ? 'PASS' : 'FAIL'} :: ${results.join('  ')}`)
}

async function until2(cond: () => Promise<boolean>, timeoutMs: number): Promise<void> {
  const start = Date.now()
  // eslint-disable-next-line no-constant-condition
  while (true) {
    if (await cond()) return
    if (Date.now() - start > timeoutMs) return
    await new Promise((r) => setTimeout(r, 120))
  }
}

function whenLoaded(win: BrowserWindow): Promise<void> {
  return new Promise((res) => {
    if (!win.webContents.isLoading()) return res()
    win.webContents.once('did-finish-load', () => res())
  })
}

async function until(cond: () => boolean, timeoutMs: number): Promise<void> {
  const start = Date.now()
  while (!cond()) {
    if (Date.now() - start > timeoutMs) throw new Error('timeout')
    await new Promise((r) => setTimeout(r, 100))
  }
}

// Kill the sidecar on every quit path, including force quit.
app.on('before-quit', () => sidecar.stop())
app.on('will-quit', () => sidecar.stop())

app.on('window-all-closed', () => {
  sidecar.stop()
  app.quit()
})

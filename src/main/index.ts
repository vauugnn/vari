import { app, BrowserWindow, dialog, ipcMain, Menu } from 'electron'
import { writeFile } from 'fs/promises'
import { join } from 'path'
import updaterPkg from 'electron-updater'
import { buildMenu, focusOrShow } from './menu'

const { autoUpdater } = updaterPkg
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

app.setName('Vari')

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
    icon: join(app.getAppPath(), 'build/icon.png'),
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
  win.webContents.on('console-message', (_e, level, message) => {
    if (level >= 2) console.error(`[win:${entry}] ${message}`)
  })
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
    title: 'Untitled1 [DataSet0] - Vari Data Editor',
    width: 1100,
    height: 720
  })
  windows.dataeditor.on('closed', () => {
    windows.dataeditor = null
    app.quit()
  })

  windows.viewer = createWindow('viewer', {
    title: 'Output1 - Vari Viewer',
    width: 1000,
    height: 720,
    x: 120,
    y: 90
  })
  windows.viewer.on('closed', () => (windows.viewer = null))

  windows.syntax = createWindow('syntax', {
    title: 'Syntax1 - Vari Syntax Editor',
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
      { name: 'All Supported Data', extensions: ['sav', 'por', 'dta', 'xlsx', 'xls', 'csv', 'tsv', 'txt'] },
      { name: 'SPSS Statistics (*.sav)', extensions: ['sav'] },
      { name: 'SPSS Portable (*.por)', extensions: ['por'] },
      { name: 'Stata (*.dta)', extensions: ['dta'] },
      { name: 'Excel (*.xlsx, *.xls)', extensions: ['xlsx', 'xls'] },
      { name: 'Text / CSV (*.csv, *.tsv, *.txt)', extensions: ['csv', 'tsv', 'txt'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  })
  if (res.canceled || res.filePaths.length === 0) return null
  const path = res.filePaths[0]
  // Text/CSV files go through the Import wizard for delimiter/type options.
  if (/\.(csv|txt|tsv)$/i.test(path)) {
    const de = windows.dataeditor
    if (de && !de.isDestroyed()) de.webContents.send(IPC.importText, path)
    showWindow('dataeditor')
    return null
  }
  const summary = (await sidecar.request('dataset.open', { path })) as DatasetSummary
  broadcastDataset(summary)
  showWindow('dataeditor')
  return summary
}

async function importViaDialog(): Promise<void> {
  const de = windows.dataeditor ?? undefined
  const res = await dialog.showOpenDialog(de as BrowserWindow, {
    title: 'Import Data',
    properties: ['openFile'],
    filters: [
      { name: 'Text / CSV (*.csv, *.tsv, *.txt, *.dat)', extensions: ['csv', 'tsv', 'txt', 'dat'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  })
  if (res.canceled || res.filePaths.length === 0) return
  const de2 = windows.dataeditor
  if (de2 && !de2.isDestroyed()) de2.webContents.send(IPC.importText, res.filePaths[0])
  showWindow('dataeditor')
}

// ---- auto-update (electron-updater, GitHub Releases) -----------------
let updaterWired = false

function wireUpdater(): void {
  if (updaterWired) return
  updaterWired = true
  autoUpdater.autoDownload = true
  autoUpdater.autoInstallOnAppQuit = true
  autoUpdater.on('update-downloaded', (info) => {
    const win = windows.dataeditor ?? BrowserWindow.getAllWindows()[0]
    void dialog
      .showMessageBox(win, {
        type: 'info',
        buttons: ['Restart Now', 'Later'],
        defaultId: 0,
        cancelId: 1,
        title: 'Update Ready',
        message: `Vari ${info.version} is ready to install.`,
        detail: 'Restart the app to apply the update.'
      })
      .then((r) => {
        if (r.response === 0) autoUpdater.quitAndInstall()
      })
  })
  autoUpdater.on('error', (err) => console.error('[updater]', err))
}

// Silent background check on launch (packaged builds only).
function checkForUpdatesOnStartup(): void {
  if (!app.isPackaged) return
  wireUpdater()
  autoUpdater.checkForUpdates().catch((err) => console.error('[updater] check failed', err))
}

// Manual Help ▸ Check for Updates — reports "up to date" when nothing is found.
async function checkForUpdatesManual(): Promise<void> {
  const win = windows.dataeditor ?? BrowserWindow.getAllWindows()[0]
  if (!app.isPackaged) {
    await dialog.showMessageBox(win, {
      type: 'info',
      message: 'Updates are only available in the packaged app.',
      buttons: ['OK']
    })
    return
  }
  wireUpdater()
  try {
    const result = await autoUpdater.checkForUpdates()
    const latest = result?.updateInfo?.version
    if (latest && latest !== app.getVersion()) {
      await dialog.showMessageBox(win, {
        type: 'info',
        message: `Downloading Vari ${latest}…`,
        detail: 'You will be prompted to restart when it is ready.',
        buttons: ['OK']
      })
    } else {
      await dialog.showMessageBox(win, {
        type: 'info',
        message: `Vari ${app.getVersion()} is up to date.`,
        buttons: ['OK']
      })
    }
  } catch (err) {
    await dialog.showMessageBox(win, {
      type: 'error',
      message: 'Could not check for updates.',
      detail: String(err instanceof Error ? err.message : err),
      buttons: ['OK']
    })
  }
}

async function printViewer(): Promise<void> {
  const viewer = windows.viewer
  if (!viewer || viewer.isDestroyed()) return
  const res = await dialog.showSaveDialog(viewer, {
    title: 'Print Output to PDF',
    defaultPath: 'output.pdf',
    filters: [{ name: 'PDF (*.pdf)', extensions: ['pdf'] }]
  })
  if (res.canceled || !res.filePath) return
  const data = await viewer.webContents.printToPDF({ printBackground: true })
  await writeFile(res.filePath, data)
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
  ipcMain.handle(IPC.ds.importText, async (_e, p) => {
    const summary = (await sidecar.request('dataset.importText', p)) as DatasetSummary
    broadcastDataset(summary)
    return summary
  })
}

function wireIpc(): void {
  wireDatasetIpc()
  ipcMain.handle(IPC.syntaxExecute, async (_evt, text: string): Promise<OutputObject[]> => {
    try {
      const result = (await sidecar.request('syntax.execute', { text })) as OutputObject[]
      const all = Array.isArray(result) ? result : []
      // Internal signal: a command changed the active dataset — refresh the grid.
      const objects: OutputObject[] = []
      for (const o of all) {
        if (o.type === '_DatasetChanged') {
          broadcastDataset((o as unknown as { summary: DatasetSummary }).summary)
        } else {
          objects.push(o)
        }
      }
      if (objects.length > 0) {
        sendToViewer(objects)
        showWindow('viewer')
      }
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

  ipcMain.handle(IPC.outputExportHtml, async (_e, html: string) => {
    const res = await dialog.showSaveDialog(windows.viewer as BrowserWindow, {
      title: 'Export Output as HTML',
      defaultPath: 'output.html',
      filters: [{ name: 'HTML (*.html)', extensions: ['html'] }]
    })
    if (res.canceled || !res.filePath) return null
    await writeFile(res.filePath, html, 'utf8')
    return { ok: true, path: res.filePath }
  })

  ipcMain.handle(IPC.outputExportExcel, async (_e, items: OutputObject[]) => {
    const res = await dialog.showSaveDialog(windows.viewer as BrowserWindow, {
      title: 'Export Output as Excel',
      defaultPath: 'output.xlsx',
      filters: [{ name: 'Excel (*.xlsx)', extensions: ['xlsx'] }]
    })
    if (res.canceled || !res.filePath) return null
    return (await sidecar.request('output.exportExcel', { items, path: res.filePath })) as {
      ok: boolean
      path: string
    }
  })

  ipcMain.on(IPC.windowShow, (_evt, name: WindowName) => showWindow(name))

  // Paste from a dialog: append the generated syntax to the Syntax Editor.
  ipcMain.on(IPC.syntaxPaste, (_evt, text: string) => {
    const syntax = windows.syntax
    if (syntax && !syntax.isDestroyed()) {
      syntax.webContents.send(IPC.syntaxAppend, text)
      showWindow('syntax')
    }
  })
}

function openDialog(id: string): void {
  const de = windows.dataeditor
  if (de && !de.isDestroyed()) {
    de.webContents.send(IPC.dialogOpen, id)
    showWindow('dataeditor')
  }
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
      fileSaveAs: () => void saveViaDialog(),
      filePrint: () => void printViewer(),
      fileImport: () => void importViaDialog(),
      checkUpdates: () => void checkForUpdatesManual(),
      openDialog: (id: string) => openDialog(id)
    })
  )
  wireIpc()
  createAllWindows()
  checkForUpdatesOnStartup()

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
    const ev = (js: string): Promise<any> => viewer.webContents.executeJavaScript(js)
    await syntax.webContents.executeJavaScript(`window.spss.execute("TITLE 'hello'.")`)
    await syntax.webContents.executeJavaScript(`window.spss.execute("FREQUENCIES x.")`)
    await syntax.webContents.executeJavaScript(`window.spss.execute("PIVOTDEMO.")`)
    await new Promise((r) => setTimeout(r, 500))

    const title = await ev(`document.querySelector('.out-title')?.textContent ?? null`)
    const error = await ev(`[...document.querySelectorAll('.out-error')].map(e=>e.textContent).join('|')`)
    const nTables = await ev(`document.querySelectorAll('.pt-table').length`)
    const hasMean = await ev(`document.body.innerText.includes('38.42')`)
    const genderSpan = await ev(
      `(()=>{const th=[...document.querySelectorAll('.pt-colhead')].find(e=>e.textContent==='Gender');return th?th.colSpan:0;})()`
    )
    const leafHeads = await ev(
      `[...document.querySelectorAll('.pt-colhead')].filter(e=>e.textContent==='Count'||e.textContent==='Expected').length`
    )
    // Data Editor should have auto-opened an empty spreadsheet grid.
    const de = windows.dataeditor!
    const dev = (js: string): Promise<any> => de.webContents.executeJavaScript(js)
    await until2(async () => (await dev(`document.querySelectorAll('.row').length`)) > 0, 6000)
    const emptyGrid = await dev(
      `document.querySelectorAll('.col-head--empty').length>0 && document.querySelectorAll('.row').length>0`
    )
    const statusDataset = await dev(`(document.querySelector('.statusbar')?.textContent||'').includes('DataSet')`)

    const pass =
      title === 'hello' &&
      error.toLowerCase().includes('freq') &&
      nTables === 2 &&
      hasMean === true &&
      genderSpan === 4 &&
      leafHeads === 4 &&
      emptyGrid === true &&
      statusDataset === true
    done(
      `title=${JSON.stringify(title)} tables=${nTables} mean=${hasMean} genderSpan=${genderSpan} leaf=${leafHeads} emptyGrid=${emptyGrid} status=${statusDataset} -> ${pass ? 'PASS' : 'FAIL'}`
    )
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

  const heads: string[] = await ev(`Array.from(document.querySelectorAll('.col-head-name')).map(e=>e.textContent)`)
  check('varnames', heads.slice(0, 5).join(',') === 'id,gender,income,agree,sname', heads)

  await until2(async () => {
    const c: string[] = await ev(`Array.from((document.querySelectorAll('.row')[0]||{querySelectorAll:()=>[]}).querySelectorAll('.cell')).map(c=>c.textContent)`)
    return c[0] === '1'
  }, 6000)
  const row0: string[] = await ev(
    `Array.from(document.querySelectorAll('.row')[0].querySelectorAll('.cell')).map(c=>c.textContent)`
  )
  check('rawvalues', row0[0] === '1' && row0[1] === '1' && row0[2] === '50000' && row0[4] === 'al', row0)

  // Toggle value labels and re-read.
  await ev(`[...document.querySelectorAll('.de-toolbar .tt')].find(t=>t.getAttribute('data-tip')==='Value Labels')?.querySelector('button')?.click()`)
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

  // Full syntax pipeline: run FREQUENCIES from the Syntax window; the dataset
  // opened above is the sidecar's active dataset.
  const viewer = windows.viewer!
  const vev = (js: string): Promise<any> => viewer.webContents.executeJavaScript(js)
  await windows.syntax!.webContents.executeJavaScript(
    `window.spss.execute("FREQUENCIES VARIABLES=gender /STATISTICS=MEAN.")`
  )
  await until2(async () => (await vev(`document.querySelectorAll('.pt-table').length`)) >= 2, 6000)
  const vtxt: string = await vev(`document.body.innerText`)
  check('freq_tables', (await vev(`document.querySelectorAll('.pt-table').length`)) >= 2, 'tables')
  check('freq_labels', vtxt.includes('Male') && vtxt.includes('No answer') && vtxt.includes('Statistics'), vtxt.slice(0, 80))

  // Charts: a histogram renders as inline SVG in the Viewer.
  await windows.syntax!.webContents.executeJavaScript(
    `window.spss.execute("FREQUENCIES VARIABLES=income /FORMAT=NOTABLE /HISTOGRAM.")`
  )
  await until2(async () => (await vev(`document.querySelectorAll('.out-chart svg').length`)) > 0, 6000)
  check('chart_svg', (await vev(`document.querySelectorAll('.out-chart svg').length`)) > 0, 'chart')

  // Dialog flow: Analyze ▸ Frequencies, move a variable, click OK.
  const tablesBefore: number = await vev(`document.querySelectorAll('.pt-table').length`)
  de.webContents.send(IPC.dialogOpen, 'frequencies')
  await until2(async () => (await ev(`!!document.querySelector('.af')`)) === true, 4000)
  await ev(
    `(()=>{const it=[...document.querySelectorAll('.vm-item')].find(e=>e.textContent.includes('Gender'));
       if(it){it.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));} return !!it;})()`
  )
  await until2(async () => (await ev(`document.querySelectorAll('.vm-col')[1].querySelectorAll('.vm-item').length`)) > 0, 3000)
  await ev(`[...document.querySelectorAll('.af-footer button')].find(b=>b.textContent==='OK').click()`)
  await until2(async () => (await vev(`document.querySelectorAll('.pt-table').length`)) >= tablesBefore + 2, 6000)
  const tablesAfter: number = await vev(`document.querySelectorAll('.pt-table').length`)
  check('dialog_flow', tablesAfter >= tablesBefore + 2, { tablesBefore, tablesAfter })

  // Stage 1 chrome: full toolbar + insert-variable from the toolbar.
  const toolbarBtns: number = await ev(`document.querySelectorAll('.de-toolbar .icon-btn').length`)
  check('toolbar', toolbarBtns >= 16, toolbarBtns)
  await ev(`[...document.querySelectorAll('.de-tab')].find(b=>b.textContent==='Data View')?.click()`)
  await until2(async () => (await ev(`document.querySelectorAll('.col-head-name').length`)) > 0, 4000)
  const colsBefore: number = await ev(`document.querySelectorAll('.col-head-name').length`)
  const titles: string[] = await ev(`[...document.querySelectorAll('.de-toolbar .tt')].map(t=>t.getAttribute('data-tip'))`)
  check('has_insertvar_btn', titles.includes('Insert Variable'), titles)
  await ev(`[...document.querySelectorAll('.de-toolbar .tt')].find(t=>t.getAttribute('data-tip')==='Insert Variable')?.querySelector('button')?.click()`)
  await until2(async () => (await ev(`document.querySelectorAll('.col-head-name').length`)) > colsBefore, 4000)
  const colsAfter: number = await ev(`document.querySelectorAll('.col-head-name').length`)
  check('insert_var', colsAfter > colsBefore, { colsBefore, colsAfter })

  // Stage 2: Crosstabs dialog (two movers), OK -> Crosstabulation table.
  de.webContents.send(IPC.dialogOpen, 'crosstabs')
  await until2(async () => (await ev(`document.querySelectorAll('.vm').length`)) >= 2, 4000)
  await ev(
    `(()=>{const ms=document.querySelectorAll('.vm');
      const g=[...ms[0].querySelectorAll('.vm-col')[0].querySelectorAll('.vm-item')].find(e=>e.textContent.includes('Gender'));
      if(g) g.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));
      const a=[...ms[1].querySelectorAll('.vm-col')[0].querySelectorAll('.vm-item')].find(e=>e.textContent.includes('Agreement'));
      if(a) a.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));})()`
  )
  await ev(`[...document.querySelectorAll('.af-footer button')].find(b=>b.textContent==='OK')?.click()`)
  await until2(async () => (await vev(`document.body.innerText.includes('Crosstabulation')`)) === true, 6000)
  const ctOk: boolean = await vev(`document.body.innerText.includes('Crosstabulation')`)
  check('crosstabs_dialog', ctOk === true, ctOk)

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

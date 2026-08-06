import { app, BrowserWindow, ipcMain, Menu } from 'electron'
import { join } from 'path'
import { buildMenu, focusOrShow } from './menu'
import { Sidecar } from './sidecar'
import { IPC } from '../shared/types'
import type { OutputObject, SidecarStatus, WindowName } from '../shared/types'

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

function wireIpc(): void {
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
  Menu.setApplicationMenu(buildMenu(showWindow))
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

// Headless end-to-end check of the round trip (renderer invoke -> main ->
// sidecar -> Viewer render), used for automated verification. Drives the real
// window.spss.execute() from the Syntax window, then reads the Viewer DOM.
async function runSelfTest(): Promise<void> {
  const done = (msg: string): void => {
    console.log(`[selftest] ${msg}`)
    app.quit()
  }
  try {
    const syntax = windows.syntax!
    const viewer = windows.viewer!
    await Promise.all([whenLoaded(syntax), whenLoaded(viewer)])
    await until(() => sidecar.currentStatus.state === 'ready', 10000)

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

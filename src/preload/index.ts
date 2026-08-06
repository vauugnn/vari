import { contextBridge, ipcRenderer } from 'electron'
import { IPC } from '../shared/types'
import type { OutputObject, SidecarStatus, SpssApi, WindowName } from '../shared/types'

// Which window this preload belongs to, from ?window=... on the entry URL.
function detectWindow(): WindowName {
  const q = new URLSearchParams(location.search).get('window')
  if (q === 'viewer' || q === 'syntax' || q === 'dataeditor') return q
  if (location.pathname.includes('viewer')) return 'viewer'
  if (location.pathname.includes('syntax')) return 'syntax'
  return 'dataeditor'
}

const api: SpssApi = {
  window: detectWindow(),
  execute: (text: string) => ipcRenderer.invoke(IPC.syntaxExecute, text) as Promise<OutputObject[]>,
  getSidecarStatus: () => ipcRenderer.invoke(IPC.sidecarStatusGet) as Promise<SidecarStatus>,
  onSidecarStatus: (cb) => {
    const listener = (_e: unknown, status: SidecarStatus) => cb(status)
    ipcRenderer.on(IPC.sidecarStatusEvent, listener)
    return () => ipcRenderer.removeListener(IPC.sidecarStatusEvent, listener)
  },
  onOutput: (cb) => {
    const listener = (_e: unknown, objects: OutputObject[]) => cb(objects)
    ipcRenderer.on(IPC.outputAppend, listener)
    return () => ipcRenderer.removeListener(IPC.outputAppend, listener)
  },
  showWindow: (name: WindowName) => ipcRenderer.send(IPC.windowShow, name)
}

contextBridge.exposeInMainWorld('spss', api)

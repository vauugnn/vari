import { contextBridge, ipcRenderer } from 'electron'
import { IPC } from '../shared/types'
import type {
  DatasetApi,
  DatasetSummary,
  OutputObject,
  RowWindow,
  SidecarStatus,
  SpssApi,
  VariableMetaJson,
  WindowName
} from '../shared/types'

// Which window this preload belongs to, from ?window=... on the entry URL.
function detectWindow(): WindowName {
  const q = new URLSearchParams(location.search).get('window')
  if (q === 'viewer' || q === 'syntax' || q === 'dataeditor') return q
  if (location.pathname.includes('viewer')) return 'viewer'
  if (location.pathname.includes('syntax')) return 'syntax'
  return 'dataeditor'
}

const ds: DatasetApi = {
  newDataset: () => ipcRenderer.invoke(IPC.ds.new) as Promise<DatasetSummary>,
  openDialog: () => ipcRenderer.invoke(IPC.ds.openDialog) as Promise<DatasetSummary | null>,
  open: (path: string) => ipcRenderer.invoke(IPC.ds.open, path) as Promise<DatasetSummary>,
  save: () => ipcRenderer.invoke(IPC.ds.save) as Promise<{ ok: boolean; path: string } | { error: string }>,
  saveAs: () => ipcRenderer.invoke(IPC.ds.saveAs) as Promise<{ ok: boolean; path: string } | null>,
  getRows: (offset, limit, valueLabels) =>
    ipcRenderer.invoke(IPC.ds.getRows, { offset, limit, valueLabels }) as Promise<RowWindow>,
  setCell: (row, col, value) => ipcRenderer.invoke(IPC.ds.setCell, { row, col, value }) as Promise<void>,
  setVariableMeta: (index, meta: VariableMetaJson) =>
    ipcRenderer.invoke(IPC.ds.setVariableMeta, { index, meta }) as Promise<DatasetSummary>,
  insertVariable: (index, meta) =>
    ipcRenderer.invoke(IPC.ds.insertVariable, { index, meta }) as Promise<DatasetSummary>,
  deleteVariable: (index) => ipcRenderer.invoke(IPC.ds.deleteVariable, { index }) as Promise<DatasetSummary>,
  insertCase: (index) => ipcRenderer.invoke(IPC.ds.insertCase, { index }) as Promise<{ nRows: number }>,
  deleteCase: (index) => ipcRenderer.invoke(IPC.ds.deleteCase, { index }) as Promise<{ nRows: number }>,
  undo: () => ipcRenderer.invoke(IPC.ds.undo) as Promise<DatasetSummary & { ok: boolean }>,
  redo: () => ipcRenderer.invoke(IPC.ds.redo) as Promise<DatasetSummary & { ok: boolean }>,
  importText: (path, options) =>
    ipcRenderer.invoke(IPC.ds.importText, { path, options }) as Promise<DatasetSummary>,
  onChanged: (cb) => {
    const listener = (_e: unknown, summary: DatasetSummary) => cb(summary)
    ipcRenderer.on(IPC.datasetChanged, listener)
    return () => ipcRenderer.removeListener(IPC.datasetChanged, listener)
  }
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
  showWindow: (name: WindowName) => ipcRenderer.send(IPC.windowShow, name),
  exportHtml: (html: string) =>
    ipcRenderer.invoke(IPC.outputExportHtml, html) as Promise<{ ok: boolean; path: string } | null>,
  exportExcel: (items: OutputObject[]) =>
    ipcRenderer.invoke(IPC.outputExportExcel, items) as Promise<{ ok: boolean; path: string } | null>,
  onOpenDialog: (cb) => {
    const listener = (_e: unknown, id: string) => cb(id)
    ipcRenderer.on(IPC.dialogOpen, listener)
    return () => ipcRenderer.removeListener(IPC.dialogOpen, listener)
  },
  onViewToggle: (cb) => {
    const listener = (_e: unknown, kind: string) => cb(kind)
    ipcRenderer.on(IPC.viewToggle, listener)
    return () => ipcRenderer.removeListener(IPC.viewToggle, listener)
  },
  paste: (syntax: string) => ipcRenderer.send(IPC.syntaxPaste, syntax),
  onAppendSyntax: (cb) => {
    const listener = (_e: unknown, text: string) => cb(text)
    ipcRenderer.on(IPC.syntaxAppend, listener)
    return () => ipcRenderer.removeListener(IPC.syntaxAppend, listener)
  },
  onImportText: (cb) => {
    const listener = (_e: unknown, path: string) => cb(path)
    ipcRenderer.on(IPC.importText, listener)
    return () => ipcRenderer.removeListener(IPC.importText, listener)
  },
  ds
}

contextBridge.exposeInMainWorld('spss', api)

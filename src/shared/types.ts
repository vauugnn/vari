// TS mirrors of the JSON-RPC / IPC contract (HLD 2.4). Kept deliberately small
// for Phase 0: only the round-trip surface exists here.

/** One node of the output document model (HLD 4). Phase 0 renders Title + Error. */
export interface TitleObject {
  type: 'Title'
  text: string
}

export interface ErrorObject {
  type: 'Error'
  text: string
}

/** Fallback for object types not yet modelled (PivotTable, Chart, ...). */
export interface UnknownObject {
  type: string
  text?: string
  [key: string]: unknown
}

export type OutputObject = TitleObject | ErrorObject | UnknownObject

export type SidecarState = 'starting' | 'ready' | 'down'

export interface SidecarStatus {
  state: SidecarState
  detail?: string
}

// ---- dataset / Variable View metadata --------------------------------
export type Measure = 'nominal' | 'ordinal' | 'scale'
export type Align = 'left' | 'right' | 'center'
export type Role = 'input' | 'target' | 'both' | 'none' | 'partition' | 'split'

export interface ValueLabel {
  value: number | string
  label: string
}

export interface MissingJson {
  kind: 'none' | 'discrete' | 'range'
  values: (number | string)[]
  lo: number | null
  hi: number | null
}

/** Serialized VariableMeta (server `_meta_to_json`). */
export interface VariableMetaJson {
  name: string
  type: string
  format: string
  width: number
  decimals: number
  label: string
  valueLabels: ValueLabel[]
  missing: MissingJson
  columns: number
  align: Align
  measure: Measure
  role: Role
  isString: boolean
}

export interface DatasetSummary {
  name: string
  nRows: number
  nVars: number
  sourcePath: string | null
  variables: VariableMetaJson[]
  weight?: string | null
  filter?: string | null
  split?: string[]
}

export interface RowWindow {
  offset: number
  rows: string[][]
  nRows: number
}

/** Renderer <-> main IPC channel names. */
export const IPC = {
  syntaxExecute: 'syntax.execute',
  syntaxPreview: 'syntax.preview',
  sidecarStatusGet: 'sidecar.status.get',
  sidecarStatusEvent: 'sidecar.status',
  outputAppend: 'output.append',
  outputExportHtml: 'output.exportHtml',
  outputExportExcel: 'output.exportExcel',
  outputExportSpv: 'output.exportSpv',
  outputOpenSpv: 'output.openSpv',
  scriptRun: 'script.run',
  dialogOpen: 'dialog.open',
  syntaxPaste: 'syntax.paste',
  syntaxAppend: 'syntax.append',
  importText: 'import.text',
  viewToggle: 'view.toggle',
  newScript: 'script.new',
  updateProgress: 'update.progress',
  appVersion: 'app.version',
  windowShow: 'window.show',
  datasetChanged: 'dataset.changed',
  // Version history. Main asks the Viewer and Syntax windows for their state before a snapshot.
  chartExport: 'chart.export',
  docCollect: 'doc.collect',
  docCollected: 'doc.collected',
  outputReplace: 'output.replace',
  syntaxSet: 'syntax.set',
  history: {
    list: 'history.list',
    create: 'history.create',
    rename: 'history.rename',
    delete: 'history.delete',
    diff: 'history.diff',
    restore: 'history.restore'
  },
  ds: {
    new: 'ds.new',
    openDialog: 'ds.openDialog',
    open: 'ds.open',
    save: 'ds.save',
    saveAs: 'ds.saveAs',
    getRows: 'ds.getRows',
    setCell: 'ds.setCell',
    setVariableMeta: 'ds.setVariableMeta',
    insertVariable: 'ds.insertVariable',
    deleteVariable: 'ds.deleteVariable',
    insertCase: 'ds.insertCase',
    deleteCase: 'ds.deleteCase',
    undo: 'ds.undo',
    redo: 'ds.redo',
    find: 'ds.find',
    openDatabase: 'ds.openDatabase',
    importText: 'ds.importText'
  }
} as const

export interface ImportOptions {
  delimiter: string
  firstRowNames: boolean
  decimal: string
}

export type WindowName = 'dataeditor' | 'viewer' | 'syntax'

export interface DatasetApi {
  newDataset: () => Promise<DatasetSummary>
  openDialog: () => Promise<DatasetSummary | null>
  open: (path: string) => Promise<DatasetSummary>
  save: () => Promise<{ ok: boolean; path: string } | { error: string }>
  saveAs: () => Promise<{ ok: boolean; path: string } | null>
  getRows: (offset: number, limit: number, valueLabels: boolean) => Promise<RowWindow>
  setCell: (row: number, col: number, value: string) => Promise<void>
  setVariableMeta: (index: number, meta: VariableMetaJson) => Promise<DatasetSummary>
  insertVariable: (index: number | null, meta: VariableMetaJson | null) => Promise<DatasetSummary>
  deleteVariable: (index: number) => Promise<DatasetSummary>
  insertCase: (index: number | null) => Promise<{ nRows: number }>
  deleteCase: (index: number) => Promise<{ nRows: number }>
  undo: () => Promise<DatasetSummary & { ok: boolean }>
  redo: () => Promise<DatasetSummary & { ok: boolean }>
  find: (query: string, row: number, col: number, colIndex: number | null) => Promise<{ found: boolean; row?: number; col?: number }>
  openDatabase: (conn: string, query: string) => Promise<DatasetSummary>
  importText: (path: string, options: ImportOptions) => Promise<DatasetSummary>
  onChanged: (cb: (summary: DatasetSummary) => void) => () => void
}

/** Shape exposed to the renderer via contextBridge as `window.spss`. */
export interface HistoryVersion {
  id: string
  time: number // seconds since the epoch
  kind: 'auto' | 'save' | 'manual' | 'pre-op' | 'restore' | 'open'
  name: string
  rows: number
  vars: number
  outputItems: number
  bytes: number
}

export interface HistoryDiff {
  rows: { from: number; to: number }
  variables: {
    added: string[]
    removed: string[]
    changed: { variable: string; field: string; from: unknown; to: unknown }[]
  }
  cells: { changed: number; examples: { case: number; variable: string; from: unknown; to: unknown }[] }
  syntaxDiff: string[]
  outputItems: { from: number; to: number }
  identical: boolean
}

export interface HistoryApi {
  list: () => Promise<{ docId: string; versions: HistoryVersion[] }>
  create: (name?: string) => Promise<HistoryVersion | null>
  rename: (id: string, name: string) => Promise<HistoryVersion>
  remove: (id: string) => Promise<void>
  /** Differences from version `a` to version `b`, or to the current state when `b` is omitted. */
  diff: (a: string, b?: string) => Promise<HistoryDiff>
  restore: (id: string) => Promise<DatasetSummary>
}

export interface DocState {
  syntax?: string
  output?: OutputObject[]
}

export interface SpssApi {
  window: WindowName
  appVersion: string
  execute: (text: string) => Promise<OutputObject[]>
  preview: (text: string) => Promise<OutputObject[]>
  getSidecarStatus: () => Promise<SidecarStatus>
  onSidecarStatus: (cb: (status: SidecarStatus) => void) => () => void
  onOutput: (cb: (objects: OutputObject[]) => void) => () => void
  showWindow: (name: WindowName) => void
  exportHtml: (html: string) => Promise<{ ok: boolean; path: string } | null>
  exportExcel: (items: OutputObject[]) => Promise<{ ok: boolean; path: string } | null>
  exportSpv: (items: OutputObject[]) => Promise<{ ok: boolean; path: string } | null>
  openOutput: () => Promise<OutputObject[] | null>
  onOpenDialog: (cb: (dialogId: string) => void) => () => void
  onViewToggle: (cb: (kind: string) => void) => () => void
  runScript: (code: string) => Promise<{ output: string; error: string | null; summary?: DatasetSummary }>
  onNewScript: (cb: () => void) => () => void
  onUpdateProgress: (cb: (p: { percent: number; transferred: number; total: number }) => void) => () => void
  paste: (syntax: string) => void
  onAppendSyntax: (cb: (syntax: string) => void) => () => void
  onImportText: (cb: (path: string) => void) => () => void
  ds: DatasetApi
  history: HistoryApi
  /** The Viewer and Syntax windows register what they hold, so snapshots can include it. */
  provideDocState: (provider: () => DocState) => void
  onOutputReplace: (cb: (items: OutputObject[]) => void) => () => void
  onSetSyntax: (cb: (text: string) => void) => () => void
  /** Save a chart as PNG, SVG or PDF through a save dialog. Returns the path, or null if cancelled. */
  exportChart: (format: 'png' | 'svg' | 'pdf', svg: string, png?: string) => Promise<string | null>
}

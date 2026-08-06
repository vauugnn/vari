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
  sidecarStatusGet: 'sidecar.status.get',
  sidecarStatusEvent: 'sidecar.status',
  outputAppend: 'output.append',
  outputExportHtml: 'output.exportHtml',
  dialogOpen: 'dialog.open',
  syntaxPaste: 'syntax.paste',
  syntaxAppend: 'syntax.append',
  windowShow: 'window.show',
  datasetChanged: 'dataset.changed',
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
    deleteCase: 'ds.deleteCase'
  }
} as const

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
  onChanged: (cb: (summary: DatasetSummary) => void) => () => void
}

/** Shape exposed to the renderer via contextBridge as `window.spss`. */
export interface SpssApi {
  window: WindowName
  execute: (text: string) => Promise<OutputObject[]>
  getSidecarStatus: () => Promise<SidecarStatus>
  onSidecarStatus: (cb: (status: SidecarStatus) => void) => () => void
  onOutput: (cb: (objects: OutputObject[]) => void) => () => void
  showWindow: (name: WindowName) => void
  exportHtml: (html: string) => Promise<{ ok: boolean; path: string } | null>
  onOpenDialog: (cb: (dialogId: string) => void) => () => void
  paste: (syntax: string) => void
  onAppendSyntax: (cb: (syntax: string) => void) => () => void
  ds: DatasetApi
}

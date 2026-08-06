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

/** Renderer <-> main IPC channel names. */
export const IPC = {
  syntaxExecute: 'syntax.execute',
  sidecarStatusGet: 'sidecar.status.get',
  sidecarStatusEvent: 'sidecar.status',
  outputAppend: 'output.append',
  windowShow: 'window.show'
} as const

export type WindowName = 'dataeditor' | 'viewer' | 'syntax'

/** Shape exposed to the renderer via contextBridge as `window.spss`. */
export interface SpssApi {
  window: WindowName
  execute: (text: string) => Promise<OutputObject[]>
  getSidecarStatus: () => Promise<SidecarStatus>
  onSidecarStatus: (cb: (status: SidecarStatus) => void) => () => void
  onOutput: (cb: (objects: OutputObject[]) => void) => () => void
  showWindow: (name: WindowName) => void
}

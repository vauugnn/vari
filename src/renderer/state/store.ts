import { create } from 'zustand'
import type { DatasetSummary, VariableMetaJson } from '../../shared/types'

interface DataState {
  summary: DatasetSummary | null
  showValueLabels: boolean
  showGridLines: boolean
  showStatusBar: boolean
  /** Bumped on every data/metadata mutation so grids invalidate their caches. */
  revision: number
  activeTab: 'data' | 'variable'
  lastError: string | null

  setSummary: (s: DatasetSummary) => void
  bumpRevision: () => void
  toggleValueLabels: () => void
  toggleGridLines: () => void
  toggleStatusBar: () => void
  setActiveTab: (t: 'data' | 'variable') => void
  setError: (msg: string | null) => void
  updateVariable: (index: number, meta: VariableMetaJson) => void

  /** Toolbar buttons hidden via Customize (by id). */
  hiddenTools: string[]
  toggleTool: (id: string) => void
}

export const useStore = create<DataState>((set) => ({
  summary: null,
  showValueLabels: false,
  showGridLines: true,
  showStatusBar: true,
  revision: 0,
  activeTab: 'data',
  lastError: null,

  setSummary: (s) => set((st) => ({ summary: s, revision: st.revision + 1 })),
  bumpRevision: () => set((st) => ({ revision: st.revision + 1 })),
  toggleValueLabels: () => set((st) => ({ showValueLabels: !st.showValueLabels })),
  toggleGridLines: () => set((st) => ({ showGridLines: !st.showGridLines })),
  toggleStatusBar: () => set((st) => ({ showStatusBar: !st.showStatusBar })),
  setActiveTab: (t) => set({ activeTab: t }),
  setError: (msg) => set({ lastError: msg }),
  updateVariable: (index, meta) =>
    set((st) => {
      if (!st.summary) return {}
      const variables = st.summary.variables.slice()
      variables[index] = meta
      return { summary: { ...st.summary, variables }, revision: st.revision + 1 }
    }),

  hiddenTools: [],
  toggleTool: (id) =>
    set((st) => ({
      hiddenTools: st.hiddenTools.includes(id)
        ? st.hiddenTools.filter((x) => x !== id)
        : [...st.hiddenTools, id]
    }))
}))

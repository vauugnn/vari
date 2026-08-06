import { useEffect, useRef, useState } from 'react'
import type { SidecarStatus } from '../../shared/types'
import { useStore } from '../state/store'
import { DataViewGrid } from '../grid/DataViewGrid'
import { VariableViewGrid } from '../grid/VariableViewGrid'
import './dataeditor.css'

export function DataEditor(): JSX.Element {
  const summary = useStore((s) => s.summary)
  const activeTab = useStore((s) => s.activeTab)
  const setActiveTab = useStore((s) => s.setActiveTab)
  const showValueLabels = useStore((s) => s.showValueLabels)
  const toggleValueLabels = useStore((s) => s.toggleValueLabels)
  const setSummary = useStore((s) => s.setSummary)
  const lastError = useStore((s) => s.lastError)
  const setError = useStore((s) => s.setError)

  const [status, setStatus] = useState<SidecarStatus>({ state: 'starting' })
  const initedRef = useRef(false)

  useEffect(() => window.spss.ds.onChanged(setSummary), [setSummary])
  useEffect(() => {
    void window.spss.getSidecarStatus().then(setStatus)
    return window.spss.onSidecarStatus(setStatus)
  }, [])

  // Open an empty dataset on first ready, so the grid shows immediately like
  // SPSS (an empty spreadsheet) rather than a placeholder.
  useEffect(() => {
    if (status.state === 'ready' && !summary && !initedRef.current) {
      initedRef.current = true
      void window.spss.ds.newDataset().then(setSummary).catch(() => (initedRef.current = false))
    }
  }, [status, summary, setSummary])

  const open = async (): Promise<void> => {
    const s = await window.spss.ds.openDialog()
    if (s) setSummary(s)
  }
  const save = async (): Promise<void> => {
    const res = await window.spss.ds.save()
    if ('error' in res) {
      const alt = await window.spss.ds.saveAs()
      if (alt && 'error' in (alt as object)) setError((alt as unknown as { error: string }).error)
    }
  }

  return (
    <div className="de-root">
      <div className="de-toolbar">
        <button onClick={open}>Open</button>
        <button onClick={save} disabled={!summary}>
          Save
        </button>
        <span className="de-sep" />
        <button
          className={showValueLabels ? 'toggle toggle--on' : 'toggle'}
          onClick={toggleValueLabels}
          disabled={!summary}
          title="Display value labels"
        >
          Value Labels
        </button>
      </div>

      {lastError && (
        <div className="de-error" onClick={() => setError(null)}>
          {lastError} (click to dismiss)
        </div>
      )}

      <div className="de-body">
        {!summary ? (
          <div className="de-placeholder">No dataset open. Use File ▸ Open ▸ Data… or the Open button.</div>
        ) : activeTab === 'data' ? (
          <DataViewGrid summary={summary} />
        ) : (
          <VariableViewGrid summary={summary} />
        )}
      </div>

      <div className="de-tabs">
        <button className={activeTab === 'data' ? 'de-tab de-tab--active' : 'de-tab'} onClick={() => setActiveTab('data')}>
          Data View
        </button>
        <button
          className={activeTab === 'variable' ? 'de-tab de-tab--active' : 'de-tab'}
          onClick={() => setActiveTab('variable')}
        >
          Variable View
        </button>
      </div>

      <div className="statusbar">
        {summary
          ? `${summary.name}  •  ${summary.nVars} variables  •  ${summary.nRows} cases`
          : 'IBM SPSS Statistics Processor is ' +
            (status.state === 'ready' ? 'ready' : status.state === 'down' ? 'unavailable' : 'starting')}
      </div>
    </div>
  )
}

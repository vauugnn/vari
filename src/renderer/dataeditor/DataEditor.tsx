import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { SidecarStatus } from '../../shared/types'
import { useStore } from '../state/store'
import { DataViewGrid } from '../grid/DataViewGrid'
import { VariableViewGrid } from '../grid/VariableViewGrid'
import {
  DescMuIcon,
  FindIcon,
  GotoCaseIcon,
  GotoVarIcon,
  InsertCaseIcon,
  InsertVarIcon,
  NewIcon,
  OpenIcon,
  PrintIcon,
  RecallIcon,
  RedoIcon,
  SaveIcon,
  SelectCasesIcon,
  ShowAllVarsIcon,
  SplitFileIcon,
  UndoIcon,
  ValueLabelsIcon,
  VariablesIcon,
  VarSetsIcon,
  WeightIcon
} from '../common/icons'
import { FrequenciesDialog } from '../dialogs/analysis/FrequenciesDialog'
import { DescriptivesDialog } from '../dialogs/analysis/DescriptivesDialog'
import { CrosstabsDialog } from '../dialogs/analysis/CrosstabsDialog'
import { OneSampleTTestDialog, IndependentTTestDialog, PairedTTestDialog } from '../dialogs/analysis/TTestDialogs'
import { BivariateCorrelationsDialog } from '../dialogs/analysis/CorrelateDialog'
import './dataeditor.css'

function TB({
  title,
  onClick,
  active,
  disabled,
  children
}: {
  title: string
  onClick?: () => void
  active?: boolean
  disabled?: boolean
  children: ReactNode
}): JSX.Element {
  return (
    <span className="tt" data-tip={title}>
      <button
        className={'icon-btn' + (active ? ' icon-btn--on' : '')}
        disabled={disabled}
        onClick={onClick}
      >
        {children}
      </button>
    </span>
  )
}

export function DataEditor(): JSX.Element {
  const summary = useStore((s) => s.summary)
  const activeTab = useStore((s) => s.activeTab)
  const setActiveTab = useStore((s) => s.setActiveTab)
  const showValueLabels = useStore((s) => s.showValueLabels)
  const toggleValueLabels = useStore((s) => s.toggleValueLabels)
  const setSummary = useStore((s) => s.setSummary)
  const bumpRevision = useStore((s) => s.bumpRevision)
  const lastError = useStore((s) => s.lastError)
  const setError = useStore((s) => s.setError)

  const [status, setStatus] = useState<SidecarStatus>({ state: 'starting' })
  const [dialogId, setDialogId] = useState<string | null>(null)
  const initedRef = useRef(false)

  useEffect(() => window.spss.ds.onChanged(setSummary), [setSummary])
  useEffect(() => window.spss.onOpenDialog(setDialogId), [])
  useEffect(() => {
    void window.spss.getSidecarStatus().then(setStatus)
    return window.spss.onSidecarStatus(setStatus)
  }, [])

  useEffect(() => {
    if (status.state === 'ready' && !summary && !initedRef.current) {
      initedRef.current = true
      void window.spss.ds.newDataset().then(setSummary).catch(() => (initedRef.current = false))
    }
  }, [status, summary, setSummary])

  const newDs = async (): Promise<void> => setSummary(await window.spss.ds.newDataset())
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
  const insertVar = async (): Promise<void> => setSummary(await window.spss.ds.insertVariable(null, null))
  const insertCase = async (): Promise<void> => {
    if (!summary) return
    const res = await window.spss.ds.insertCase(null)
    setSummary({ ...summary, nRows: res.nRows })
    bumpRevision()
  }
  const has = !!summary

  return (
    <div className="de-root">
      <div className="de-toolbar">
        <TB title="New" onClick={newDs}>
          <NewIcon />
        </TB>
        <TB title="Open" onClick={open}>
          <OpenIcon />
        </TB>
        <TB title="Save" onClick={save} disabled={!has}>
          <SaveIcon />
        </TB>
        <TB title="Print" disabled={!has}>
          <PrintIcon />
        </TB>
        <span className="de-sep" />
        <TB title="Recall recently used dialogs">
          <RecallIcon />
        </TB>
        <TB title="Undo" disabled>
          <UndoIcon />
        </TB>
        <TB title="Redo" disabled>
          <RedoIcon />
        </TB>
        <span className="de-sep" />
        <TB title="Go to case" disabled={!has}>
          <GotoCaseIcon />
        </TB>
        <TB title="Go to variable" disabled={!has}>
          <GotoVarIcon />
        </TB>
        <TB title="Variables" disabled={!has}>
          <VariablesIcon />
        </TB>
        <TB title="Run Descriptive Statistics" onClick={() => setDialogId('descriptives')} disabled={!has}>
          <DescMuIcon />
        </TB>
        <TB title="Find" disabled={!has}>
          <FindIcon />
        </TB>
        <span className="de-sep" />
        <TB title="Insert Cases" onClick={insertCase} disabled={!has}>
          <InsertCaseIcon />
        </TB>
        <TB title="Insert Variable" onClick={insertVar} disabled={!has}>
          <InsertVarIcon />
        </TB>
        <span className="de-sep" />
        <TB title="Split File" onClick={() => setDialogId('splitfile')} disabled={!has}>
          <SplitFileIcon />
        </TB>
        <TB title="Weight Cases" onClick={() => setDialogId('weight')} disabled={!has}>
          <WeightIcon />
        </TB>
        <TB title="Select Cases" onClick={() => setDialogId('selectcases')} disabled={!has}>
          <SelectCasesIcon />
        </TB>
        <span className="de-sep" />
        <TB title="Value Labels" onClick={toggleValueLabels} active={showValueLabels} disabled={!has}>
          <ValueLabelsIcon />
        </TB>
        <TB title="Use Variable Sets" disabled={!has}>
          <VarSetsIcon />
        </TB>
        <TB title="Show All Variables" disabled={!has}>
          <ShowAllVarsIcon />
        </TB>
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
        <span className="sb-seg">
          IBM SPSS Statistics Processor is {status.state === 'ready' ? 'ready' : status.state === 'down' ? 'unavailable' : 'starting'}
        </span>
        {summary && <span className="sb-seg">{summary.name}</span>}
        {summary && <span className="sb-seg">{summary.nVars} variables</span>}
        {summary && <span className="sb-seg">{summary.nRows} cases</span>}
        <span className="sb-seg">Weight Off</span>
        <span className="sb-seg">Split Off</span>
        <span className="sb-seg">Filter Off</span>
      </div>

      {(() => {
        if (!dialogId || !summary) return null
        const p = { variables: summary.variables, onClose: () => setDialogId(null) }
        switch (dialogId) {
          case 'frequencies':
            return <FrequenciesDialog {...p} />
          case 'descriptives':
            return <DescriptivesDialog {...p} />
          case 'crosstabs':
            return <CrosstabsDialog {...p} />
          case 'ttest-one':
            return <OneSampleTTestDialog {...p} />
          case 'ttest-ind':
            return <IndependentTTestDialog {...p} />
          case 'ttest-paired':
            return <PairedTTestDialog {...p} />
          case 'correlate':
            return <BivariateCorrelationsDialog {...p} />
          default:
            return null
        }
      })()}
    </div>
  )
}

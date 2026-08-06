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
  WeightIcon,
  SyntaxWinIcon,
  ViewerWinIcon,
  GearIcon
} from '../common/icons'
import { Modal } from '../dialogs/Modal'
import { FrequenciesDialog } from '../dialogs/analysis/FrequenciesDialog'
import { DescriptivesDialog } from '../dialogs/analysis/DescriptivesDialog'
import { CrosstabsDialog } from '../dialogs/analysis/CrosstabsDialog'
import { OneSampleTTestDialog, IndependentTTestDialog, PairedTTestDialog } from '../dialogs/analysis/TTestDialogs'
import { BivariateCorrelationsDialog } from '../dialogs/analysis/CorrelateDialog'
import { OneWayAnovaDialog } from '../dialogs/analysis/OneWayAnovaDialog'
import { ReliabilityDialog } from '../dialogs/analysis/ReliabilityDialog'
import { LinearRegressionDialog } from '../dialogs/analysis/RegressionDialog'
import { MeansDialog } from '../dialogs/analysis/MeansDialog'
import { ComputeDialog } from '../dialogs/analysis/ComputeDialog'
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

  const hiddenTools = useStore((s) => s.hiddenTools)
  const toggleTool = useStore((s) => s.toggleTool)

  const [status, setStatus] = useState<SidecarStatus>({ state: 'starting' })
  const [dialogId, setDialogId] = useState<string | null>(null)
  const [customize, setCustomize] = useState(false)
  const initedRef = useRef(false)

  useEffect(() => window.spss.ds.onChanged(setSummary), [setSummary])
  useEffect(
    () =>
      window.spss.onOpenDialog((id) => {
        if (id === 'customize-toolbar') setCustomize(true)
        else setDialogId(id)
      }),
    []
  )
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

  type Tool = { id: string; tip: string; icon: ReactNode; onClick?: () => void; disabled?: boolean; active?: boolean }
  const tools: (Tool | 'sep')[] = [
    { id: 'new', tip: 'New', icon: <NewIcon />, onClick: newDs },
    { id: 'open', tip: 'Open', icon: <OpenIcon />, onClick: open },
    { id: 'save', tip: 'Save', icon: <SaveIcon />, onClick: save, disabled: !has },
    { id: 'print', tip: 'Print', icon: <PrintIcon />, disabled: !has },
    'sep',
    { id: 'recall', tip: 'Recall recently used dialogs', icon: <RecallIcon /> },
    { id: 'undo', tip: 'Undo', icon: <UndoIcon />, disabled: true },
    { id: 'redo', tip: 'Redo', icon: <RedoIcon />, disabled: true },
    'sep',
    { id: 'gotocase', tip: 'Go to case', icon: <GotoCaseIcon />, disabled: !has },
    { id: 'gotovar', tip: 'Go to variable', icon: <GotoVarIcon />, disabled: !has },
    { id: 'variables', tip: 'Variables', icon: <VariablesIcon />, disabled: !has },
    { id: 'descmu', tip: 'Run Descriptive Statistics', icon: <DescMuIcon />, onClick: () => setDialogId('descriptives'), disabled: !has },
    { id: 'find', tip: 'Find', icon: <FindIcon />, disabled: !has },
    'sep',
    { id: 'insertcase', tip: 'Insert Cases', icon: <InsertCaseIcon />, onClick: insertCase, disabled: !has },
    { id: 'insertvar', tip: 'Insert Variable', icon: <InsertVarIcon />, onClick: insertVar, disabled: !has },
    'sep',
    { id: 'split', tip: 'Split File', icon: <SplitFileIcon />, onClick: () => setDialogId('splitfile'), disabled: !has },
    { id: 'weight', tip: 'Weight Cases', icon: <WeightIcon />, onClick: () => setDialogId('weight'), disabled: !has },
    { id: 'select', tip: 'Select Cases', icon: <SelectCasesIcon />, onClick: () => setDialogId('selectcases'), disabled: !has },
    'sep',
    { id: 'valuelabels', tip: 'Value Labels', icon: <ValueLabelsIcon />, onClick: toggleValueLabels, active: showValueLabels, disabled: !has },
    { id: 'varsets', tip: 'Use Variable Sets', icon: <VarSetsIcon />, disabled: !has },
    { id: 'showall', tip: 'Show All Variables', icon: <ShowAllVarsIcon />, disabled: !has },
    'sep',
    { id: 'syntax', tip: 'Go to Syntax Editor', icon: <SyntaxWinIcon />, onClick: () => window.spss.showWindow('syntax') },
    { id: 'viewer', tip: 'Go to Output Viewer', icon: <ViewerWinIcon />, onClick: () => window.spss.showWindow('viewer') }
  ]
  const hid = (id: string): boolean => hiddenTools.includes(id)

  return (
    <div className="de-root">
      <div className="de-toolbar">
        {tools.map((t, i) =>
          t === 'sep' ? (
            <span key={'s' + i} className="de-sep" />
          ) : hid(t.id) ? null : (
            <TB key={t.id} title={t.tip} onClick={t.onClick} active={t.active} disabled={t.disabled}>
              {t.icon}
            </TB>
          )
        )}
        <span className="de-sep" />
        <TB title="Customize toolbar" onClick={() => setCustomize(true)}>
          <GearIcon />
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
          case 'oneway':
            return <OneWayAnovaDialog {...p} />
          case 'reliability':
            return <ReliabilityDialog {...p} />
          case 'regression':
            return <LinearRegressionDialog {...p} />
          case 'means':
            return <MeansDialog {...p} />
          case 'compute':
            return <ComputeDialog {...p} />
          default:
            return null
        }
      })()}

      {customize && (
        <Modal title="Customize Toolbar" onOk={() => setCustomize(false)} onCancel={() => setCustomize(false)}>
          <div style={{ maxHeight: 260, overflow: 'auto' }}>
            <div style={{ marginBottom: 6, color: '#555' }}>Show these toolbar buttons:</div>
            {tools
              .filter((t): t is Tool => t !== 'sep')
              .map((t) => (
                <label key={t.id} style={{ display: 'flex', gap: 6, padding: '1px 0' }}>
                  <input type="checkbox" checked={!hid(t.id)} onChange={() => toggleTool(t.id)} />
                  {t.tip}
                </label>
              ))}
          </div>
        </Modal>
      )}
    </div>
  )
}

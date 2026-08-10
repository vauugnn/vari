import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { SidecarStatus } from '../../shared/types'
import { useStore } from '../state/store'
import { DataViewGrid } from '../grid/DataViewGrid'
import { VariableViewGrid } from '../grid/VariableViewGrid'
import { OverviewPanel } from './OverviewPanel'
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
import { HistogramDialog, BarChartDialog, PieChartDialog, ScatterDialog, BoxplotDialog, HighLowDialog, PyramidDialog, Bar3dDialog } from '../dialogs/analysis/GraphDialogs'
import { MultivariateDialog, DistancesDialog, CanonicalDialog } from '../dialogs/analysis/MultivariateDialogs'
import { ProbitDialog, PlsDialog, TslsDialog, VarcompDialog, RepeatedDialog } from '../dialogs/analysis/Regression2Dialogs'
import { GenlinDialog, GeeDialog, MixedDialog, GenlogDialog } from '../dialogs/analysis/Glm3Dialogs'
import { KaplanMeierDialog, CoxDialog, LifeTableDialog } from '../dialogs/analysis/SurvivalDialogs'
import { ArimaDialog, SeasonDialog, SpectraDialog, CsDescriptivesDialog, CsTabulateDialog } from '../dialogs/analysis/ForecastCsDialogs'
import { TwoStepDialog, NearestNeighborDialog, CorrespondenceDialog, ProxscalDialog, AlscalDialog, PrefscalDialog, MlpDialog, RbfDialog } from '../dialogs/analysis/Wave5Dialogs'
import { OlapDialog, CtablesDialog, MultiResponseDialog, ControlChartDialog, ParetoDialog, BayesNormalDialog, BayesBinomialDialog, BayesPoissonDialog } from '../dialogs/analysis/Wave6Dialogs'
import { VarsToCasesDialog, CasesToVarsDialog, VisualBinDialog } from '../dialogs/analysis/Wave7Dialogs'
import { FindDialog, GoToCaseDialog, GoToVariableDialog } from '../dialogs/analysis/FindGotoDialogs'
import { SelectCasesDialog, WeightCasesDialog, SplitFileDialog, SortCasesDialog } from '../dialogs/analysis/DataOpsDialogs'
import { ExploreDialog, PartialCorrDialog } from '../dialogs/analysis/ExploreDialog'
import { ImportWizard } from '../dialogs/ImportWizard'
import {
  ChiSquareDialog,
  BinomialDialog,
  RunsDialog,
  OneSampleKSDialog,
  TwoIndependentDialog,
  KIndependentDialog,
  TwoRelatedDialog,
  KRelatedDialog
} from '../dialogs/analysis/NparDialogs'
import {
  RankCasesDialog,
  AutoRecodeDialog,
  CountValuesDialog,
  ReplaceMissingDialog,
  RecodeDifferentDialog,
  RecodeSameDialog,
  ShiftValuesDialog,
  RandomSeedDialog
} from '../dialogs/analysis/TransformDialogs'
import { TransposeDialog, AggregateDialog, AddCasesDialog, AddVariablesDialog } from '../dialogs/analysis/DataStructDialogs'
import {
  UnivariateDialog,
  FactorDialog,
  BinaryLogisticDialog,
  MultinomialDialog,
  OrdinalDialog,
  KMeansDialog,
  HierarchicalDialog,
  DiscriminantDialog
} from '../dialogs/analysis/Tier2Dialogs'
import {
  CaseSummariesDialog,
  CodebookDialog,
  CurveEstimationDialog,
  RocDialog,
  LineDialog,
  AreaDialog,
  ErrorBarDialog,
  QQPlotDialog,
  PPPlotDialog,
  RatioDialog,
  KappaDialog
} from '../dialogs/analysis/MoreDialogs'
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
  const showGridLines = useStore((s) => s.showGridLines)
  const showStatusBar = useStore((s) => s.showStatusBar)
  const setSummary = useStore((s) => s.setSummary)
  const bumpRevision = useStore((s) => s.bumpRevision)
  const lastError = useStore((s) => s.lastError)
  const setError = useStore((s) => s.setError)

  const hiddenTools = useStore((s) => s.hiddenTools)
  const toggleTool = useStore((s) => s.toggleTool)

  const [status, setStatus] = useState<SidecarStatus>({ state: 'starting' })
  const [dialogId, setDialogId] = useState<string | null>(null)
  const [customize, setCustomize] = useState(false)
  const [importPath, setImportPath] = useState<string | null>(null)
  const initedRef = useRef(false)

  useEffect(() => window.spss.onImportText(setImportPath), [])

  useEffect(() => window.spss.ds.onChanged(setSummary), [setSummary])
  useEffect(
    () =>
      window.spss.onOpenDialog((id) => {
        if (id === 'customize-toolbar') setCustomize(true)
        else setDialogId(id)
      }),
    []
  )
  useEffect(
    () =>
      window.spss.onViewToggle((kind) => {
        if (kind === 'valuelabels') useStore.getState().toggleValueLabels()
        else if (kind === 'gridlines') useStore.getState().toggleGridLines()
        else if (kind === 'statusbar') useStore.getState().toggleStatusBar()
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
  const undo = async (): Promise<void> => {
    const s = await window.spss.ds.undo()
    if (s.ok) {
      setSummary(s)
      bumpRevision()
    }
  }
  const redo = async (): Promise<void> => {
    const s = await window.spss.ds.redo()
    if (s.ok) {
      setSummary(s)
      bumpRevision()
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
    { id: 'undo', tip: 'Undo', icon: <UndoIcon />, onClick: undo, disabled: !has },
    { id: 'redo', tip: 'Redo', icon: <RedoIcon />, onClick: redo, disabled: !has },
    'sep',
    { id: 'gotocase', tip: 'Go to case', icon: <GotoCaseIcon />, onClick: () => setDialogId('gotocase'), disabled: !has },
    { id: 'gotovar', tip: 'Go to variable', icon: <GotoVarIcon />, onClick: () => setDialogId('gotovar'), disabled: !has },
    { id: 'variables', tip: 'Variables', icon: <VariablesIcon />, onClick: () => setActiveTab('variable'), disabled: !has },
    { id: 'descmu', tip: 'Run Descriptive Statistics', icon: <DescMuIcon />, onClick: () => setDialogId('descriptives'), disabled: !has },
    { id: 'find', tip: 'Find', icon: <FindIcon />, onClick: () => setDialogId('find'), disabled: !has },
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

      <div className={'de-body' + (showGridLines ? '' : ' de-body--nolines')}>
        {!summary ? (
          <div className="de-placeholder">No dataset open. Use File ▸ Open ▸ Data… or the Open button.</div>
        ) : activeTab === 'data' ? (
          <DataViewGrid summary={summary} />
        ) : activeTab === 'variable' ? (
          <VariableViewGrid summary={summary} />
        ) : (
          <OverviewPanel summary={summary} />
        )}
      </div>

      <div className="de-tabs">
        <button className={activeTab === 'overview' ? 'de-tab de-tab--active' : 'de-tab'} onClick={() => setActiveTab('overview')}>
          Overview
        </button>
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

      {showStatusBar && (
      <div className="statusbar">
        <span className="sb-seg">
          Vari Processor is {status.state === 'ready' ? 'ready' : status.state === 'down' ? 'unavailable' : 'starting'}
        </span>
        {summary && <span className="sb-seg">{summary.name}</span>}
        {summary && <span className="sb-seg">{summary.nVars} variables</span>}
        {summary && <span className="sb-seg">{summary.nRows} cases</span>}
        <span className="sb-seg">{summary?.weight ? `Weight On (${summary.weight})` : 'Weight Off'}</span>
        <span className="sb-seg">{summary?.split && summary.split.length ? `Split On (${summary.split.join(', ')})` : 'Split Off'}</span>
        <span className="sb-seg">{summary?.filter ? `Filter On (${summary.filter})` : 'Filter Off'}</span>
      </div>
      )}

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
          case 'graph-histogram':
            return <HistogramDialog {...p} />
          case 'graph-bar':
            return <BarChartDialog {...p} />
          case 'graph-pie':
            return <PieChartDialog {...p} />
          case 'graph-scatter':
            return <ScatterDialog {...p} />
          case 'graph-boxplot':
            return <BoxplotDialog {...p} />
          case 'graph-highlow':
            return <HighLowDialog {...p} />
          case 'graph-pyramid':
            return <PyramidDialog {...p} />
          case 'graph-bar3d':
            return <Bar3dDialog {...p} />
          case 'multivariate-glm':
            return <MultivariateDialog {...p} />
          case 'distances':
            return <DistancesDialog {...p} />
          case 'cancorr':
            return <CanonicalDialog {...p} />
          case 'probit':
            return <ProbitDialog {...p} />
          case 'pls':
            return <PlsDialog {...p} />
          case 'tsls':
            return <TslsDialog {...p} />
          case 'varcomp':
            return <VarcompDialog {...p} />
          case 'glm-repeated':
            return <RepeatedDialog {...p} />
          case 'genlin':
            return <GenlinDialog {...p} />
          case 'gee':
            return <GeeDialog {...p} />
          case 'mixed':
            return <MixedDialog {...p} />
          case 'genlog':
            return <GenlogDialog {...p} />
          case 'km':
            return <KaplanMeierDialog {...p} />
          case 'coxreg':
            return <CoxDialog {...p} />
          case 'lifetable':
            return <LifeTableDialog {...p} />
          case 'arima':
            return <ArimaDialog {...p} />
          case 'season':
            return <SeasonDialog {...p} />
          case 'spectra':
            return <SpectraDialog {...p} />
          case 'csdescr':
            return <CsDescriptivesDialog {...p} />
          case 'cstab':
            return <CsTabulateDialog {...p} />
          case 'twostep':
            return <TwoStepDialog {...p} />
          case 'knn':
            return <NearestNeighborDialog {...p} />
          case 'correspondence':
            return <CorrespondenceDialog {...p} />
          case 'proxscal':
            return <ProxscalDialog {...p} />
          case 'alscal':
            return <AlscalDialog {...p} />
          case 'prefscal':
            return <PrefscalDialog {...p} />
          case 'mlp':
            return <MlpDialog {...p} />
          case 'rbf':
            return <RbfDialog {...p} />
          case 'olap':
            return <OlapDialog {...p} />
          case 'ctables':
            return <CtablesDialog {...p} />
          case 'multiresponse':
            return <MultiResponseDialog {...p} />
          case 'spchart':
            return <ControlChartDialog {...p} />
          case 'pareto':
            return <ParetoDialog {...p} />
          case 'bayes-normal':
            return <BayesNormalDialog {...p} />
          case 'bayes-binomial':
            return <BayesBinomialDialog {...p} />
          case 'bayes-poisson':
            return <BayesPoissonDialog {...p} />
          case 'varstocases':
            return <VarsToCasesDialog {...p} />
          case 'casestovars':
            return <CasesToVarsDialog {...p} />
          case 'visualbin':
            return <VisualBinDialog {...p} />
          case 'find':
            return <FindDialog {...p} />
          case 'gotocase':
            return <GoToCaseDialog {...p} />
          case 'gotovar':
            return <GoToVariableDialog {...p} />
          case 'selectcases':
            return <SelectCasesDialog {...p} />
          case 'weight':
            return <WeightCasesDialog {...p} />
          case 'splitfile':
            return <SplitFileDialog {...p} />
          case 'sort':
            return <SortCasesDialog {...p} />
          case 'explore':
            return <ExploreDialog {...p} />
          case 'partial':
            return <PartialCorrDialog {...p} />
          case 'npar-chisquare':
            return <ChiSquareDialog {...p} />
          case 'npar-binomial':
            return <BinomialDialog {...p} />
          case 'npar-runs':
            return <RunsDialog {...p} />
          case 'npar-ks':
            return <OneSampleKSDialog {...p} />
          case 'npar-2indep':
            return <TwoIndependentDialog {...p} />
          case 'npar-kindep':
            return <KIndependentDialog {...p} />
          case 'npar-2related':
            return <TwoRelatedDialog {...p} />
          case 'npar-krelated':
            return <KRelatedDialog {...p} />
          case 'rank':
            return <RankCasesDialog {...p} />
          case 'autorecode':
            return <AutoRecodeDialog {...p} />
          case 'count':
            return <CountValuesDialog {...p} />
          case 'rmv':
            return <ReplaceMissingDialog {...p} />
          case 'recode-different':
            return <RecodeDifferentDialog {...p} />
          case 'recode-same':
            return <RecodeSameDialog {...p} />
          case 'shift-values':
            return <ShiftValuesDialog {...p} />
          case 'random-seed':
            return <RandomSeedDialog {...p} />
          case 'transpose':
            return <TransposeDialog {...p} />
          case 'aggregate':
            return <AggregateDialog {...p} />
          case 'add-cases':
            return <AddCasesDialog {...p} />
          case 'add-variables':
            return <AddVariablesDialog {...p} />
          case 'univariate':
            return <UnivariateDialog {...p} />
          case 'factor':
            return <FactorDialog {...p} />
          case 'logistic':
            return <BinaryLogisticDialog {...p} />
          case 'multinomial':
            return <MultinomialDialog {...p} />
          case 'ordinal':
            return <OrdinalDialog {...p} />
          case 'kmeans':
            return <KMeansDialog {...p} />
          case 'hierarchical':
            return <HierarchicalDialog {...p} />
          case 'discriminant':
            return <DiscriminantDialog {...p} />
          case 'summarize':
            return <CaseSummariesDialog {...p} />
          case 'codebook':
            return <CodebookDialog {...p} />
          case 'curvefit':
            return <CurveEstimationDialog {...p} />
          case 'roc':
            return <RocDialog {...p} />
          case 'graph-line':
            return <LineDialog {...p} />
          case 'graph-area':
            return <AreaDialog {...p} />
          case 'graph-errorbar':
            return <ErrorBarDialog {...p} />
          case 'qqplot':
            return <QQPlotDialog {...p} />
          case 'ppplot':
            return <PPPlotDialog {...p} />
          case 'ratio':
            return <RatioDialog {...p} />
          case 'kappa':
            return <KappaDialog {...p} />
          default:
            return null
        }
      })()}

      {importPath && (
        <ImportWizard path={importPath} onClose={() => setImportPath(null)} onDone={setSummary} />
      )}

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

import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

type Props = { variables: VariableMetaJson[]; onClose: () => void }
const num = (v: VariableMetaJson) => !v.isString

function go(s: string, onClose: () => void) {
  void window.spss.execute(s)
  onClose()
}

export function OlapDialog({ variables, onClose }: Props): JSX.Element {
  const [dep, setDep] = useState<string[]>([])
  const [factors, setFactors] = useState<string[]>([])
  const s = () => `OLAP ${dep[0]} BY ${factors.join(' ')}.`
  return (
    <AnalysisFrame title="OLAP Cubes" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setDep([]); setFactors([]) }} onCancel={onClose} okDisabled={!dep.length || !factors.length}>
      <VarMover variables={variables} value={dep} onChange={(v) => setDep(v.slice(-1))} label="Summary Variable:" accept={num} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={factors} onChange={setFactors} label="Grouping Variable(s):" />
    </AnalysisFrame>
  )
}

export function CtablesDialog({ variables, onClose }: Props): JSX.Element {
  const [row, setRow] = useState<string[]>([])
  const [col, setCol] = useState<string[]>([])
  const [stat, setStat] = useState('COUNT')
  const s = () => `CTABLES\n  /TABLE ${row[0]}${col[0] ? ' BY ' + col[0] : ''}\n  /STATISTICS ${stat}.`
  return (
    <AnalysisFrame title="Custom Tables" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setRow([]); setCol([]) }} onCancel={onClose} okDisabled={!row.length}>
      <VarMover variables={variables} value={row} onChange={(v) => setRow(v.slice(-1))} label="Rows:" />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={col} onChange={(v) => setCol(v.slice(-1))} label="Columns (optional):" />
      <div className="field-row" style={{ marginTop: 6 }}><span>Statistic:</span>
        <select value={stat} onChange={(e) => setStat(e.target.value)}>
          <option>COUNT</option><option>ROWPCT</option><option>COLPCT</option>
        </select>
      </div>
    </AnalysisFrame>
  )
}

export function MultiResponseDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [value, setValue] = useState('1')
  const s = () => `MULTRESPONSE\n  /FREQUENCIES ${vars.join(' ')}\n  /VALUE=${value}.`
  return (
    <AnalysisFrame title="Multiple Response Frequencies" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={!vars.length}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Dichotomy Variables:" accept={num} />
      <div className="field-row" style={{ marginTop: 6 }}><span>Counted value:</span><input value={value} onChange={(e) => setValue(e.target.value)} style={{ width: 50 }} /></div>
    </AnalysisFrame>
  )
}

export function ControlChartDialog({ variables, onClose }: Props): JSX.Element {
  const [v, setV] = useState<string[]>([])
  const [sub, setSub] = useState<string[]>([])
  const type = sub[0] ? 'XR' : 'I'
  const s = () => `SPCHART ${v[0]}${sub[0] ? ' BY ' + sub[0] : ''}\n  /TYPE=${type}.`
  return (
    <AnalysisFrame title="Control Charts" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setV([]); setSub([]) }} onCancel={onClose} okDisabled={!v.length}>
      <VarMover variables={variables} value={v} onChange={(x) => setV(x.slice(-1))} label="Measurement:" accept={num} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={sub} onChange={(x) => setSub(x.slice(-1))} label="Subgroups (X-bar/R, optional):" />
    </AnalysisFrame>
  )
}

export function ParetoDialog({ variables, onClose }: Props): JSX.Element {
  const [v, setV] = useState<string[]>([])
  const s = () => `PARETO ${v[0]}.`
  return (
    <AnalysisFrame title="Pareto Charts" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setV([])} onCancel={onClose} okDisabled={!v.length}>
      <VarMover variables={variables} value={v} onChange={(x) => setV(x.slice(-1))} label="Category Variable:" />
    </AnalysisFrame>
  )
}

function bayesDialog(title: string, type: string) {
  return function Dialog({ variables, onClose }: Props): JSX.Element {
    const [vars, setVars] = useState<string[]>([])
    const s = () => `BAYES ${vars.join(' ')}\n  /TEST TYPE=${type}.`
    return (
      <AnalysisFrame title={title} onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={!vars.length}>
        <VarMover variables={variables} value={vars} onChange={setVars} label="Test Variable(s):" accept={num} />
      </AnalysisFrame>
    )
  }
}

export const BayesNormalDialog = bayesDialog('Bayesian One-Sample Normal', 'NORMAL')
export const BayesBinomialDialog = bayesDialog('Bayesian One-Sample Binomial', 'BINOMIAL')
export const BayesPoissonDialog = bayesDialog('Bayesian One-Sample Poisson', 'POISSON')

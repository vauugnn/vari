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

export function ArimaDialog({ variables, onClose }: Props): JSX.Element {
  const [v, setV] = useState<string[]>([])
  const [p, setP] = useState('1')
  const [d, setD] = useState('0')
  const [q, setQ] = useState('0')
  const s = () => `TSMODEL ${v[0]}\n  /ARIMA ${p} ${d} ${q}.`
  return (
    <AnalysisFrame title="Time Series Modeler (ARIMA)" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setV([])} onCancel={onClose} okDisabled={!v.length}>
      <VarMover variables={variables} value={v} onChange={(x) => setV(x.slice(-1))} label="Dependent Series:" accept={num} />
      <div className="field-row" style={{ marginTop: 6 }}>
        <span>ARIMA (p d q):</span>
        <input value={p} onChange={(e) => setP(e.target.value)} style={{ width: 44 }} />
        <input value={d} onChange={(e) => setD(e.target.value)} style={{ width: 44 }} />
        <input value={q} onChange={(e) => setQ(e.target.value)} style={{ width: 44 }} />
      </div>
    </AnalysisFrame>
  )
}

export function SeasonDialog({ variables, onClose }: Props): JSX.Element {
  const [v, setV] = useState<string[]>([])
  const [period, setPeriod] = useState('12')
  const s = () => `SEASON ${v[0]}\n  /PERIOD ${period}.`
  return (
    <AnalysisFrame title="Seasonal Decomposition" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setV([])} onCancel={onClose} okDisabled={!v.length}>
      <VarMover variables={variables} value={v} onChange={(x) => setV(x.slice(-1))} label="Series:" accept={num} />
      <div className="field-row" style={{ marginTop: 6 }}><span>Periodicity:</span><input value={period} onChange={(e) => setPeriod(e.target.value)} style={{ width: 60 }} /></div>
    </AnalysisFrame>
  )
}

export function SpectraDialog({ variables, onClose }: Props): JSX.Element {
  const [v, setV] = useState<string[]>([])
  const s = () => `SPECTRA ${v[0]}.`
  return (
    <AnalysisFrame title="Spectral Analysis" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setV([])} onCancel={onClose} okDisabled={!v.length}>
      <VarMover variables={variables} value={v} onChange={(x) => setV(x.slice(-1))} label="Series:" accept={num} />
    </AnalysisFrame>
  )
}

export function CsDescriptivesDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [weight, setWeight] = useState<string[]>([])
  const [strata, setStrata] = useState<string[]>([])
  const s = () => `CSDESCRIPTIVES\n  /SUMMARY VARIABLES=${vars.join(' ')}\n  /WEIGHT=${weight[0]}${strata[0] ? '\n  /STRATA=' + strata[0] : ''}.`
  return (
    <AnalysisFrame title="Complex Samples Descriptives" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setVars([]); setWeight([]); setStrata([]) }} onCancel={onClose} okDisabled={!vars.length || !weight.length}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Measures:" accept={num} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={weight} onChange={(v) => setWeight(v.slice(-1))} label="Sample Weight:" accept={num} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={strata} onChange={(v) => setStrata(v.slice(-1))} label="Strata (optional):" />
    </AnalysisFrame>
  )
}

export function CsTabulateDialog({ variables, onClose }: Props): JSX.Element {
  const [row, setRow] = useState<string[]>([])
  const [col, setCol] = useState<string[]>([])
  const [weight, setWeight] = useState<string[]>([])
  const s = () => `CSTABULATE\n  /TABLES VARIABLES=${row[0]} BY ${col[0]}\n  /WEIGHT=${weight[0]}.`
  return (
    <AnalysisFrame title="Complex Samples Crosstabs" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setRow([]); setCol([]); setWeight([]) }} onCancel={onClose} okDisabled={!row.length || !col.length || !weight.length}>
      <VarMover variables={variables} value={row} onChange={(v) => setRow(v.slice(-1))} label="Rows:" />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={col} onChange={(v) => setCol(v.slice(-1))} label="Columns:" />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={weight} onChange={(v) => setWeight(v.slice(-1))} label="Sample Weight:" accept={num} />
    </AnalysisFrame>
  )
}

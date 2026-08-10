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

export function TwoStepDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const s = () => `TWOSTEP ${vars.join(' ')}.`
  return (
    <AnalysisFrame title="TwoStep Cluster Analysis" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={!vars.length}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Continuous Variables:" accept={num} />
    </AnalysisFrame>
  )
}

export function NearestNeighborDialog({ variables, onClose }: Props): JSX.Element {
  const [target, setTarget] = useState<string[]>([])
  const [feats, setFeats] = useState<string[]>([])
  const [k, setK] = useState('3')
  const s = () => `KNN ${target[0]} BY ${feats.join(' ')}\n  /K ${k}.`
  return (
    <AnalysisFrame title="Nearest Neighbor Analysis" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setTarget([]); setFeats([]) }} onCancel={onClose} okDisabled={!target.length || !feats.length}>
      <VarMover variables={variables} value={target} onChange={(v) => setTarget(v.slice(-1))} label="Target:" />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={feats} onChange={setFeats} label="Features:" accept={num} />
      <div className="field-row" style={{ marginTop: 6 }}><span>Neighbors (k):</span><input value={k} onChange={(e) => setK(e.target.value)} style={{ width: 50 }} /></div>
    </AnalysisFrame>
  )
}

export function CorrespondenceDialog({ variables, onClose }: Props): JSX.Element {
  const [row, setRow] = useState<string[]>([])
  const [col, setCol] = useState<string[]>([])
  const s = () => `CORRESPONDENCE TABLE=${row[0]} BY ${col[0]}.`
  return (
    <AnalysisFrame title="Correspondence Analysis" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setRow([]); setCol([]) }} onCancel={onClose} okDisabled={!row.length || !col.length}>
      <VarMover variables={variables} value={row} onChange={(v) => setRow(v.slice(-1))} label="Row:" />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={col} onChange={(v) => setCol(v.slice(-1))} label="Column:" />
    </AnalysisFrame>
  )
}

function mdsDialog(title: string, cmd: string) {
  return function Dialog({ variables, onClose }: Props): JSX.Element {
    const [vars, setVars] = useState<string[]>([])
    const [dims, setDims] = useState('2')
    const s = () => `${cmd} ${vars.join(' ')}\n  /DIMENSIONS ${dims}.`
    return (
      <AnalysisFrame title={title} onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={vars.length < 2}>
        <VarMover variables={variables} value={vars} onChange={setVars} label="Variables:" accept={num} />
        <div className="field-row" style={{ marginTop: 6 }}><span>Dimensions:</span><input value={dims} onChange={(e) => setDims(e.target.value)} style={{ width: 50 }} /></div>
      </AnalysisFrame>
    )
  }
}

export const ProxscalDialog = mdsDialog('Multidimensional Scaling (PROXSCAL)', 'PROXSCAL')
export const AlscalDialog = mdsDialog('Multidimensional Scaling (ALSCAL)', 'ALSCAL')
export const PrefscalDialog = mdsDialog('Multidimensional Unfolding (PREFSCAL)', 'PREFSCAL')

function netDialog(title: string, cmd: string) {
  return function Dialog({ variables, onClose }: Props): JSX.Element {
    const [target, setTarget] = useState<string[]>([])
    const [covars, setCovars] = useState<string[]>([])
    const s = () => `${cmd} ${target[0]} WITH ${covars.join(' ')}.`
    return (
      <AnalysisFrame title={title} onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setTarget([]); setCovars([]) }} onCancel={onClose} okDisabled={!target.length || !covars.length}>
        <VarMover variables={variables} value={target} onChange={(v) => setTarget(v.slice(-1))} label="Dependent:" />
        <div style={{ height: 6 }} />
        <VarMover variables={variables} value={covars} onChange={setCovars} label="Covariates:" accept={num} />
      </AnalysisFrame>
    )
  }
}

export const MlpDialog = netDialog('Multilayer Perceptron', 'MLP')
export const RbfDialog = netDialog('Radial Basis Function', 'RBF')

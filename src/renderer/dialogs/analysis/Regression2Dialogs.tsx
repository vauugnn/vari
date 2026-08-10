import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

type Props = { variables: VariableMetaJson[]; onClose: () => void }
const num = (v: VariableMetaJson) => !v.isString

function go(syntax: string, onClose: () => void) {
  void window.spss.execute(syntax)
  onClose()
}

function depWith(title: string, cmd: string, depLabel: string, predLabel: string, minPred = 1) {
  return function Dialog({ variables, onClose }: Props): JSX.Element {
    const [dep, setDep] = useState<string[]>([])
    const [preds, setPreds] = useState<string[]>([])
    const s = () => `${cmd} ${dep[0]} WITH ${preds.join(' ')}.`
    return (
      <AnalysisFrame title={title} onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setDep([]); setPreds([]) }} onCancel={onClose} okDisabled={!dep.length || preds.length < minPred}>
        <VarMover variables={variables} value={dep} onChange={(v) => setDep(v.slice(-1))} label={depLabel} accept={num} />
        <div style={{ height: 8 }} />
        <VarMover variables={variables} value={preds} onChange={setPreds} label={predLabel} accept={num} />
      </AnalysisFrame>
    )
  }
}

export const ProbitDialog = depWith('Probit Analysis', 'PROBIT', 'Response (0/1):', 'Covariate(s):')
export const PlsDialog = depWith('Partial Least Squares', 'PLS', 'Dependent:', 'Predictors:')

export function TslsDialog({ variables, onClose }: Props): JSX.Element {
  const [dep, setDep] = useState<string[]>([])
  const [reg, setReg] = useState<string[]>([])
  const [inst, setInst] = useState<string[]>([])
  const s = () => `2SLS ${dep[0]} WITH ${reg.join(' ')}\n  /INSTRUMENTS ${inst.join(' ')}.`
  return (
    <AnalysisFrame title="2-Stage Least Squares" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setDep([]); setReg([]); setInst([]) }} onCancel={onClose} okDisabled={!dep.length || !reg.length || !inst.length}>
      <VarMover variables={variables} value={dep} onChange={(v) => setDep(v.slice(-1))} label="Dependent:" accept={num} />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={reg} onChange={setReg} label="Explanatory:" accept={num} />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={inst} onChange={setInst} label="Instrumental:" accept={num} />
    </AnalysisFrame>
  )
}

export function VarcompDialog({ variables, onClose }: Props): JSX.Element {
  const [dep, setDep] = useState<string[]>([])
  const [factor, setFactor] = useState<string[]>([])
  const s = () => `VARCOMP ${dep[0]} BY ${factor[0]}\n  /RANDOM=${factor[0]}.`
  return (
    <AnalysisFrame title="Variance Components" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setDep([]); setFactor([]) }} onCancel={onClose} okDisabled={!dep.length || !factor.length}>
      <VarMover variables={variables} value={dep} onChange={(v) => setDep(v.slice(-1))} label="Dependent:" accept={num} />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={factor} onChange={(v) => setFactor(v.slice(-1))} label="Random Factor:" />
    </AnalysisFrame>
  )
}

export function RepeatedDialog({ variables, onClose }: Props): JSX.Element {
  const [levels, setLevels] = useState<string[]>([])
  const [name, setName] = useState('factor1')
  const s = () => `GLMRM ${levels.join(' ')}\n  /WSFACTOR ${name || 'factor1'} ${levels.length}.`
  return (
    <AnalysisFrame title="Repeated Measures" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setLevels([])} onCancel={onClose} okDisabled={levels.length < 2}>
      <div className="field-row"><span>Within-Subject Factor Name:</span><input value={name} onChange={(e) => setName(e.target.value)} style={{ width: 120 }} /></div>
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={levels} onChange={setLevels} label="Level Variables (in order):" accept={num} />
    </AnalysisFrame>
  )
}

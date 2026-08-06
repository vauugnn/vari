import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

type Props = { variables: VariableMetaJson[]; onClose: () => void }

function run(syntax: string, onClose: () => void) {
  void window.spss.execute(syntax)
  onClose()
}

export function RankCasesDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const s = () => `RANK VARIABLES=${vars.join(' ')} (A).`
  return (
    <AnalysisFrame title="Rank Cases" onOk={() => run(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={!vars.length}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Variable(s):" accept={(v) => !v.isString} />
    </AnalysisFrame>
  )
}

export function AutoRecodeDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [into, setInto] = useState('')
  const s = () => `AUTORECODE VARIABLES=${vars.join(' ')}\n  /INTO ${into}.`
  return (
    <AnalysisFrame title="Automatic Recode" onOk={() => run(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setVars([]); setInto('') }} onCancel={onClose} okDisabled={!vars.length || !into.trim()}>
      <VarMover variables={variables} value={vars} onChange={(v) => setVars(v.slice(-1))} label="Variable:" />
      <div className="field-row" style={{ marginTop: 6 }}><span>New Name:</span><input value={into} onChange={(e) => setInto(e.target.value)} style={{ width: 140 }} /></div>
    </AnalysisFrame>
  )
}

export function CountValuesDialog({ variables, onClose }: Props): JSX.Element {
  const [target, setTarget] = useState('')
  const [vars, setVars] = useState<string[]>([])
  const [values, setValues] = useState('1')
  const s = () => `COUNT ${target} = ${vars.join(' ')} (${values}).`
  return (
    <AnalysisFrame title="Count Occurrences of Values within Cases" onOk={() => run(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setTarget(''); setVars([]) }} onCancel={onClose} okDisabled={!target.trim() || !vars.length}>
      <div className="field-row"><span>Target Variable:</span><input value={target} onChange={(e) => setTarget(e.target.value)} style={{ width: 140 }} /></div>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Numeric Variables:" accept={(v) => !v.isString} />
      <div className="field-row" style={{ marginTop: 6 }}><span>Values to count:</span><input value={values} onChange={(e) => setValues(e.target.value)} style={{ width: 160 }} /></div>
    </AnalysisFrame>
  )
}

export function ReplaceMissingDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const s = () => `RMV ${vars.map((v) => `${v}_1=SMEAN(${v})`).join(' ')}.`
  return (
    <AnalysisFrame title="Replace Missing Values" onOk={() => run(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={!vars.length}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Variables (→ series mean):" accept={(v) => !v.isString} />
    </AnalysisFrame>
  )
}

export function RecodeDifferentDialog({ variables, onClose }: Props): JSX.Element {
  const [src, setSrc] = useState<string[]>([])
  const [target, setTarget] = useState('')
  const [rules, setRules] = useState('(1 THRU 5=1)(6 THRU 10=2)(ELSE=SYSMIS)')
  const s = () => `RECODE ${src[0]} ${rules} INTO ${target}.`
  return (
    <AnalysisFrame title="Recode into Different Variables" onOk={() => run(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setSrc([]); setTarget('') }} onCancel={onClose} okDisabled={!src.length || !target.trim()}>
      <VarMover variables={variables} value={src} onChange={(v) => setSrc(v.slice(-1))} label="Input Variable:" accept={(v) => !v.isString} />
      <div className="field-row" style={{ marginTop: 6 }}><span>Output Name:</span><input value={target} onChange={(e) => setTarget(e.target.value)} style={{ width: 140 }} /></div>
      <div style={{ marginTop: 6 }}>Old → New rules:</div>
      <input value={rules} onChange={(e) => setRules(e.target.value)} style={{ width: '100%', fontFamily: 'Menlo, monospace', fontSize: 12 }} />
      <div style={{ fontSize: 11, color: '#666', marginTop: 3 }}>e.g. (1 THRU 5=1)(6 THRU 10=2)(ELSE=SYSMIS)</div>
    </AnalysisFrame>
  )
}

import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'
import { OldNewValuesDialog } from './OldNewValues'

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

export function ShiftValuesDialog({ variables, onClose }: Props): JSX.Element {
  const [src, setSrc] = useState<string[]>([])
  const [fn, setFn] = useState<'LAG' | 'LEAD'>('LAG')
  const [n, setN] = useState('1')
  const [name, setName] = useState('')
  const target = name.trim() || (src[0] ? `${src[0]}_${fn.toLowerCase()}` : '')
  const s = () => `CREATE ${target} = ${fn}(${src[0]}, ${n || 1}).`
  return (
    <AnalysisFrame title="Shift Values" onOk={() => run(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setSrc([]); setName('') }} onCancel={onClose} okDisabled={!src.length || !target}>
      <VarMover variables={variables} value={src} onChange={(v) => setSrc(v.slice(-1))} label="Variable:" accept={(v) => !v.isString} />
      <div className="field-row" style={{ marginTop: 6 }}>
        <span>Function:</span>
        <label><input type="radio" checked={fn === 'LAG'} onChange={() => setFn('LAG')} /> Lag (previous)</label>
        <label><input type="radio" checked={fn === 'LEAD'} onChange={() => setFn('LEAD')} /> Lead (next)</label>
      </div>
      <div className="field-row"><span>Order (n):</span><input type="number" min={1} value={n} onChange={(e) => setN(e.target.value)} style={{ width: 60 }} /></div>
      <div className="field-row"><span>Name of shifted variable:</span><input value={name} onChange={(e) => setName(e.target.value)} placeholder={target} style={{ width: 140 }} /></div>
    </AnalysisFrame>
  )
}

export function RandomSeedDialog({ onClose }: Props): JSX.Element {
  const [seed, setSeed] = useState('2000000')
  const s = () => `SET SEED = ${seed || 0}.`
  return (
    <AnalysisFrame title="Random Number Generators" onOk={() => run(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setSeed('2000000')} onCancel={onClose} okDisabled={!seed.trim()}>
      <div className="field-row"><span>Set Starting Point — Fixed Value:</span><input type="number" value={seed} onChange={(e) => setSeed(e.target.value)} style={{ width: 140 }} /></div>
      <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>Makes RV.* draws and random sampling reproducible.</div>
    </AnalysisFrame>
  )
}

export function RecodeSameDialog({ variables, onClose }: Props): JSX.Element {
  const [src, setSrc] = useState<string[]>([])
  const [rules, setRules] = useState('(1 THRU 5=1)(6 THRU 10=2)(ELSE=SYSMIS)')
  const [editing, setEditing] = useState(false)
  // RECODE without INTO rewrites the same variables.
  const s = () => `RECODE ${src.join(' ')} ${rules}.`
  return (
    <>
      <AnalysisFrame title="Recode into Same Variables" onOk={() => run(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setSrc([])} onCancel={onClose} okDisabled={!src.length || !rules}
        subButtons={[{ label: 'Old and New Values…', onClick: () => setEditing(true) }]}>
        <VarMover variables={variables} value={src} onChange={setSrc} label="Numeric Variables:" accept={(v) => !v.isString} />
        <div style={{ marginTop: 6, fontSize: 12, color: '#333' }}>Old → New: <span style={{ fontFamily: 'Menlo, monospace' }}>{rules || '(none — click Old and New Values…)'}</span></div>
      </AnalysisFrame>
      {editing && <OldNewValuesDialog initial={rules} onOk={(r) => { setRules(r); setEditing(false) }} onCancel={() => setEditing(false)} />}
    </>
  )
}

export function RecodeDifferentDialog({ variables, onClose }: Props): JSX.Element {
  const [src, setSrc] = useState<string[]>([])
  const [target, setTarget] = useState('')
  const [rules, setRules] = useState('(1 THRU 5=1)(6 THRU 10=2)(ELSE=SYSMIS)')
  const [editing, setEditing] = useState(false)
  const s = () => `RECODE ${src[0]} ${rules} INTO ${target}.`
  return (
    <>
      <AnalysisFrame title="Recode into Different Variables" onOk={() => run(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setSrc([]); setTarget('') }} onCancel={onClose} okDisabled={!src.length || !target.trim() || !rules}
        subButtons={[{ label: 'Old and New Values…', onClick: () => setEditing(true) }]}>
        <VarMover variables={variables} value={src} onChange={(v) => setSrc(v.slice(-1))} label="Input Variable:" accept={(v) => !v.isString} />
        <div className="field-row" style={{ marginTop: 6 }}><span>Output Name:</span><input value={target} onChange={(e) => setTarget(e.target.value)} style={{ width: 140 }} /></div>
        <div style={{ marginTop: 6, fontSize: 12, color: '#333' }}>Old → New: <span style={{ fontFamily: 'Menlo, monospace' }}>{rules || '(none — click Old and New Values…)'}</span></div>
      </AnalysisFrame>
      {editing && <OldNewValuesDialog initial={rules} onOk={(r) => { setRules(r); setEditing(false) }} onCancel={() => setEditing(false)} />}
    </>
  )
}

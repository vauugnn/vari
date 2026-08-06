import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

type Props = { variables: VariableMetaJson[]; onClose: () => void }

function go(syntax: string, onClose: () => void) {
  void window.spss.execute(syntax)
  onClose()
}

export function TransposeDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const s = () => `FLIP VARIABLES=${vars.join(' ')}.`
  return (
    <AnalysisFrame title="Transpose" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={!vars.length}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Variable(s):" accept={(v) => !v.isString} />
    </AnalysisFrame>
  )
}

export function AggregateDialog({ variables, onClose }: Props): JSX.Element {
  const [breaks, setBreaks] = useState<string[]>([])
  const [aggs, setAggs] = useState<string[]>([])
  const s = () => {
    const summaries = aggs.map((v) => `  /${v}_mean=MEAN(${v})`).join('\n')
    return `AGGREGATE\n  /OUTFILE=*\n  /BREAK=${breaks.join(' ')}\n${summaries}\n  /N_BREAK=N.`
  }
  return (
    <AnalysisFrame title="Aggregate Data" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setBreaks([]); setAggs([]) }} onCancel={onClose} okDisabled={!breaks.length}>
      <VarMover variables={variables} value={breaks} onChange={setBreaks} label="Break Variable(s):" />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={aggs} onChange={setAggs} label="Summaries (mean):" accept={(v) => !v.isString} />
    </AnalysisFrame>
  )
}

export function AddCasesDialog({ onClose }: Props): JSX.Element {
  const [path, setPath] = useState('')
  const s = () => `ADD FILES /FILE=* /FILE='${path}'.`
  return (
    <AnalysisFrame title="Add Cases (Merge)" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setPath('')} onCancel={onClose} okDisabled={!path.trim()}>
      <div className="field-row"><span>File to append (.sav):</span><input value={path} onChange={(e) => setPath(e.target.value)} style={{ width: 300 }} placeholder="/path/to/other.sav" /></div>
    </AnalysisFrame>
  )
}

export function AddVariablesDialog({ variables, onClose }: Props): JSX.Element {
  const [path, setPath] = useState('')
  const [key, setKey] = useState<string[]>([])
  const s = () => `MATCH FILES /FILE=* /FILE='${path}' /BY ${key.join(' ')}.`
  return (
    <AnalysisFrame title="Add Variables (Merge)" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setPath(''); setKey([]) }} onCancel={onClose} okDisabled={!path.trim() || !key.length}>
      <div className="field-row"><span>Lookup file (.sav):</span><input value={path} onChange={(e) => setPath(e.target.value)} style={{ width: 300 }} placeholder="/path/to/lookup.sav" /></div>
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={key} onChange={setKey} label="Key Variable(s):" />
    </AnalysisFrame>
  )
}

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

export function VarsToCasesDialog({ variables, onClose }: Props): JSX.Element {
  const [srcs, setSrcs] = useState<string[]>([])
  const [make, setMake] = useState('trans')
  const [index, setIndex] = useState('Index')
  const s = () => `VARSTOCASES\n  /MAKE ${make} FROM ${srcs.join(' ')}\n  /INDEX=${index}.`
  return (
    <AnalysisFrame title="Restructure — Variables to Cases" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setSrcs([])} onCancel={onClose} okDisabled={srcs.length < 2 || !make.trim()}>
      <VarMover variables={variables} value={srcs} onChange={setSrcs} label="Variables to Transpose:" accept={num} />
      <div className="field-row" style={{ marginTop: 6 }}><span>Target (long) variable:</span><input value={make} onChange={(e) => setMake(e.target.value)} style={{ width: 120 }} /></div>
      <div className="field-row"><span>Index variable:</span><input value={index} onChange={(e) => setIndex(e.target.value)} style={{ width: 120 }} /></div>
    </AnalysisFrame>
  )
}

export function CasesToVarsDialog({ variables, onClose }: Props): JSX.Element {
  const [id, setId] = useState<string[]>([])
  const [index, setIndex] = useState<string[]>([])
  const s = () => `CASESTOVARS\n  /ID=${id[0]}\n  /INDEX=${index[0]}.`
  return (
    <AnalysisFrame title="Restructure — Cases to Variables" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setId([]); setIndex([]) }} onCancel={onClose} okDisabled={!id.length || !index.length}>
      <VarMover variables={variables} value={id} onChange={(v) => setId(v.slice(-1))} label="Identifier (ID):" />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={index} onChange={(v) => setIndex(v.slice(-1))} label="Index:" />
    </AnalysisFrame>
  )
}

export function SortVariablesDialog({ onClose }: Props): JSX.Element {
  const [key, setKey] = useState('NAME')
  const [dir, setDir] = useState<'A' | 'D'>('A')
  const s = () => `SORT VARIABLES BY ${key} (${dir}).`
  return (
    <AnalysisFrame title="Sort Variables" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setKey('NAME'); setDir('A') }} onCancel={onClose} okDisabled={false}>
      <div className="field-row"><span>Sort by:</span>
        <select value={key} onChange={(e) => setKey(e.target.value)}>
          <option value="NAME">Name</option><option value="TYPE">Type</option><option value="MEASURE">Measurement Level</option>
        </select>
      </div>
      <div className="field-row"><span>Order:</span>
        <label><input type="radio" checked={dir === 'A'} onChange={() => setDir('A')} /> Ascending</label>
        <label><input type="radio" checked={dir === 'D'} onChange={() => setDir('D')} /> Descending</label>
      </div>
    </AnalysisFrame>
  )
}

export function VisualBinDialog({ variables, onClose }: Props): JSX.Element {
  const [src, setSrc] = useState<string[]>([])
  const [name, setName] = useState('')
  const [bins, setBins] = useState('4')
  const [method, setMethod] = useState<'EQUAL' | 'RANK'>('EQUAL')
  const target = name.trim() || (src[0] ? `${src[0]}_bin` : '')
  const s = () => `VBIN ${src[0]} INTO ${target}\n  /BINS ${bins}\n  /METHOD ${method}.`
  return (
    <AnalysisFrame title="Visual Binning" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setSrc([]); setName('') }} onCancel={onClose} okDisabled={!src.length || !target}>
      <VarMover variables={variables} value={src} onChange={(v) => setSrc(v.slice(-1))} label="Variable to Bin:" accept={num} />
      <div className="field-row" style={{ marginTop: 6 }}><span>Binned variable:</span><input value={name} onChange={(e) => setName(e.target.value)} placeholder={target} style={{ width: 120 }} /></div>
      <div className="field-row"><span>Number of bins:</span><input value={bins} onChange={(e) => setBins(e.target.value)} style={{ width: 50 }} /></div>
      <div className="field-row"><span>Method:</span>
        <label><input type="radio" checked={method === 'EQUAL'} onChange={() => setMethod('EQUAL')} /> Equal Width</label>
        <label><input type="radio" checked={method === 'RANK'} onChange={() => setMethod('RANK')} /> Equal Count</label>
      </div>
    </AnalysisFrame>
  )
}

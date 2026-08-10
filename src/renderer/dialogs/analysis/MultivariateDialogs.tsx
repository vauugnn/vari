import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

type Props = { variables: VariableMetaJson[]; onClose: () => void }

function go(syntax: string, onClose: () => void) {
  void window.spss.execute(syntax)
  onClose()
}

export function MultivariateDialog({ variables, onClose }: Props): JSX.Element {
  const [deps, setDeps] = useState<string[]>([])
  const [factors, setFactors] = useState<string[]>([])
  const s = () => `GLM ${deps.join(' ')} BY ${factors.join(' ')}.`
  return (
    <AnalysisFrame title="Multivariate" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setDeps([]); setFactors([]) }} onCancel={onClose} okDisabled={deps.length < 2 || !factors.length}>
      <VarMover variables={variables} value={deps} onChange={setDeps} label="Dependent Variables (2+):" accept={(v) => !v.isString} />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={factors} onChange={setFactors} label="Fixed Factor(s):" />
    </AnalysisFrame>
  )
}

const MEASURES = ['EUCLID', 'SEUCLID', 'BLOCK', 'CHEBYCHEV', 'COSINE']

export function DistancesDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [measure, setMeasure] = useState('EUCLID')
  const [view, setView] = useState<'CASE' | 'VARIABLE'>('VARIABLE')
  const s = () => `PROXIMITIES ${vars.join(' ')}\n  /MEASURE=${measure}\n  /VIEW=${view}.`
  return (
    <AnalysisFrame title="Distances" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={!vars.length}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Variables:" accept={(v) => !v.isString} />
      <div className="field-row" style={{ marginTop: 6 }}>
        <span>Compute Distances:</span>
        <label><input type="radio" checked={view === 'VARIABLE'} onChange={() => setView('VARIABLE')} /> Between variables</label>
        <label><input type="radio" checked={view === 'CASE'} onChange={() => setView('CASE')} /> Between cases</label>
      </div>
      <div className="field-row"><span>Measure:</span>
        <select value={measure} onChange={(e) => setMeasure(e.target.value)}>
          {MEASURES.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
      </div>
    </AnalysisFrame>
  )
}

export function CanonicalDialog({ variables, onClose }: Props): JSX.Element {
  const [set1, setSet1] = useState<string[]>([])
  const [set2, setSet2] = useState<string[]>([])
  const s = () => `CANCORR ${set1.join(' ')} WITH ${set2.join(' ')}.`
  return (
    <AnalysisFrame title="Canonical Correlation" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setSet1([]); setSet2([]) }} onCancel={onClose} okDisabled={!set1.length || !set2.length}>
      <VarMover variables={variables} value={set1} onChange={setSet1} label="Set 1:" accept={(v) => !v.isString} />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={set2} onChange={setSet2} label="Set 2:" accept={(v) => !v.isString} />
    </AnalysisFrame>
  )
}

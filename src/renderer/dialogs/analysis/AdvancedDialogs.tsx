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

export function PowerDialog({ onClose }: Props): JSX.Element {
  const [test, setTest] = useState('TTEST')
  const [effect, setEffect] = useState('0.5')
  const [alpha, setAlpha] = useState('0.05')
  const [solveFor, setSolveFor] = useState<'power' | 'n'>('n')
  const [known, setKnown] = useState('0.8')
  const [groups, setGroups] = useState('3')
  const s = () => `POWER /TEST=${test} /EFFECT=${effect} /ALPHA=${alpha}` +
    (solveFor === 'n' ? ` /POWER=${known}` : ` /N=${known}`) +
    (test === 'ANOVA' ? ` /GROUPS=${groups}` : '') + '.'
  return (
    <AnalysisFrame title="Power Analysis" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setEffect('0.5'); setKnown('0.8') }} onCancel={onClose} okDisabled={false}>
      <div className="field-row"><span>Test:</span>
        <select value={test} onChange={(e) => setTest(e.target.value)}><option value="TTEST">Independent-Samples t</option><option value="ANOVA">One-Way ANOVA</option></select>
      </div>
      <div className="field-row"><span>Effect size:</span><input value={effect} onChange={(e) => setEffect(e.target.value)} style={{ width: 60 }} /></div>
      <div className="field-row"><span>Alpha:</span><input value={alpha} onChange={(e) => setAlpha(e.target.value)} style={{ width: 60 }} /></div>
      {test === 'ANOVA' && <div className="field-row"><span>Groups:</span><input value={groups} onChange={(e) => setGroups(e.target.value)} style={{ width: 60 }} /></div>}
      <div className="field-row"><span>Solve for:</span>
        <label><input type="radio" checked={solveFor === 'n'} onChange={() => { setSolveFor('n'); setKnown('0.8') }} /> Sample size (given power)</label>
        <label><input type="radio" checked={solveFor === 'power'} onChange={() => { setSolveFor('power'); setKnown('30') }} /> Power (given N)</label>
      </div>
      <div className="field-row"><span>{solveFor === 'n' ? 'Target power:' : 'N per group:'}</span><input value={known} onChange={(e) => setKnown(e.target.value)} style={{ width: 60 }} /></div>
    </AnalysisFrame>
  )
}

function varListDialog(title: string, cmd: string) {
  return function Dialog({ variables, onClose }: Props): JSX.Element {
    const [vars, setVars] = useState<string[]>([])
    const s = () => `${cmd} VARIABLES=${vars.join(' ')}.`
    return (
      <AnalysisFrame title={title} onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={!vars.length}>
        <VarMover variables={variables} value={vars} onChange={setVars} label="Variables:" />
      </AnalysisFrame>
    )
  }
}

export const MvaDialog = varListDialog('Missing Value Analysis', 'MVA')
export const MiDialog = varListDialog('Multiple Imputation', 'MI')

export function MediationDialog({ variables, onClose }: Props): JSX.Element {
  const [y, setY] = useState<string[]>([])
  const [x, setX] = useState<string[]>([])
  const [med, setMed] = useState<string[]>([])
  const s = () => `MEDIATION ${y[0]} WITH ${x[0]} /MED ${med[0]}.`
  return (
    <AnalysisFrame title="Mediation Analysis" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setY([]); setX([]); setMed([]) }} onCancel={onClose} okDisabled={!y.length || !x.length || !med.length}>
      <VarMover variables={variables} value={y} onChange={(v) => setY(v.slice(-1))} label="Outcome (Y):" accept={num} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={x} onChange={(v) => setX(v.slice(-1))} label="Predictor (X):" accept={num} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={med} onChange={(v) => setMed(v.slice(-1))} label="Mediator (M):" accept={num} />
    </AnalysisFrame>
  )
}

export function MetaDialog({ variables, onClose }: Props): JSX.Element {
  const [es, setEs] = useState<string[]>([])
  const [se, setSe] = useState<string[]>([])
  const [model, setModel] = useState<'RANDOM' | 'FIXED'>('RANDOM')
  const s = () => `META EFFECT=${es[0]} SE=${se[0]} /MODEL=${model}.`
  return (
    <AnalysisFrame title="Meta-Analysis" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setEs([]); setSe([]) }} onCancel={onClose} okDisabled={!es.length || !se.length}>
      <VarMover variables={variables} value={es} onChange={(v) => setEs(v.slice(-1))} label="Effect Size:" accept={num} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={se} onChange={(v) => setSe(v.slice(-1))} label="Standard Error:" accept={num} />
      <div className="field-row" style={{ marginTop: 6 }}><span>Model:</span>
        <label><input type="radio" checked={model === 'RANDOM'} onChange={() => setModel('RANDOM')} /> Random effects</label>
        <label><input type="radio" checked={model === 'FIXED'} onChange={() => setModel('FIXED')} /> Fixed effect</label>
      </div>
    </AnalysisFrame>
  )
}

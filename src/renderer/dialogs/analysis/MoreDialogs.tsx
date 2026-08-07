import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

type Props = { variables: VariableMetaJson[]; onClose: () => void }

function go(s: string, onClose: () => void) {
  void window.spss.execute(s)
  onClose()
}
function frame(title: string, s: () => string, disabled: boolean, onClose: () => void, body: JSX.Element, reset: () => void) {
  return (
    <AnalysisFrame title={title} onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={reset} onCancel={onClose} okDisabled={disabled}>
      {body}
    </AnalysisFrame>
  )
}

export function CaseSummariesDialog({ variables, onClose }: Props): JSX.Element {
  const [deps, setDeps] = useState<string[]>([])
  const [fac, setFac] = useState<string[]>([])
  const s = () => `SUMMARIZE /TABLES=${deps.join(' ')}${fac.length ? ` BY ${fac[0]}` : ''}.`
  return frame('Case Summaries', s, !deps.length, onClose, (
    <>
      <VarMover variables={variables} value={deps} onChange={setDeps} label="Variables:" accept={(v) => !v.isString} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={fac} onChange={(v) => setFac(v.slice(-1))} label="Grouping Variable:" />
    </>
  ), () => { setDeps([]); setFac([]) })
}

export function CodebookDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const s = () => `CODEBOOK ${vars.join(' ')}.`
  return frame('Codebook', s, !vars.length, onClose, (
    <VarMover variables={variables} value={vars} onChange={setVars} label="Variables:" />
  ), () => setVars([]))
}

export function CurveEstimationDialog({ variables, onClose }: Props): JSX.Element {
  const [dep, setDep] = useState<string[]>([])
  const [indep, setIndep] = useState<string[]>([])
  const [models, setModels] = useState<Set<string>>(new Set(['LINEAR']))
  const s = () => `CURVEFIT VARIABLES=${dep[0]} WITH ${indep[0]}\n  /MODEL=${[...models].join(' ')}.`
  const toggle = (k: string) => {
    const n = new Set(models)
    if (n.has(k)) n.delete(k)
    else n.add(k)
    setModels(n)
  }
  return frame('Curve Estimation', s, !dep.length || !indep.length || !models.size, onClose, (
    <>
      <VarMover variables={variables} value={dep} onChange={(v) => setDep(v.slice(-1))} label="Dependent:" accept={(v) => !v.isString} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={indep} onChange={(v) => setIndep(v.slice(-1))} label="Independent:" accept={(v) => !v.isString} />
      <fieldset className="opts"><legend>Models</legend>
        <div className="stat-grid">
          {[['LINEAR', 'Linear'], ['QUADRATIC', 'Quadratic'], ['CUBIC', 'Cubic'], ['LOGARITHMIC', 'Logarithmic'], ['EXPONENTIAL', 'Exponential']].map(([k, lab]) => (
            <label key={k}><input type="checkbox" checked={models.has(k)} onChange={() => toggle(k)} />{lab}</label>
          ))}
        </div>
      </fieldset>
    </>
  ), () => { setDep([]); setIndep([]); setModels(new Set(['LINEAR'])) })
}

export function RocDialog({ variables, onClose }: Props): JSX.Element {
  const [test, setTest] = useState<string[]>([])
  const [state, setState] = useState<string[]>([])
  const [val, setVal] = useState('1')
  const s = () => `ROC ${test.join(' ')} BY ${state[0]}(${val})\n  /PLOT=CURVE.`
  return frame('ROC Curve', s, !test.length || !state.length, onClose, (
    <>
      <VarMover variables={variables} value={test} onChange={setTest} label="Test Variable(s):" accept={(v) => !v.isString} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={state} onChange={(v) => setState(v.slice(-1))} label="State Variable:" />
      <div className="field-row"><span>Value of State Variable:</span><input value={val} onChange={(e) => setVal(e.target.value)} style={{ width: 60 }} /></div>
    </>
  ), () => { setTest([]); setState([]) })
}

function meanByDialog(title: string, kind: 'LINE' | 'AREA' | 'ERRORBAR') {
  return function Dialog({ variables, onClose }: Props): JSX.Element {
    const [dep, setDep] = useState<string[]>([])
    const [cat, setCat] = useState<string[]>([])
    const s = () => `GRAPH\n  /${kind}(SIMPLE)=MEAN(${dep[0]}) BY ${cat[0]}.`
    return frame(title, s, !dep.length || !cat.length, onClose, (
      <>
        <VarMover variables={variables} value={dep} onChange={(v) => setDep(v.slice(-1))} label="Variable (mean):" accept={(v) => !v.isString} />
        <div style={{ height: 6 }} />
        <VarMover variables={variables} value={cat} onChange={(v) => setCat(v.slice(-1))} label="Category Axis:" />
      </>
    ), () => { setDep([]); setCat([]) })
  }
}

export const LineDialog = meanByDialog('Line Charts', 'LINE')
export const AreaDialog = meanByDialog('Area Charts', 'AREA')
export const ErrorBarDialog = meanByDialog('Error Bar', 'ERRORBAR')

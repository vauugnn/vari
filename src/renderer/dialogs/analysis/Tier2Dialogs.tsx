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

export function UnivariateDialog({ variables, onClose }: Props): JSX.Element {
  const [dep, setDep] = useState<string[]>([])
  const [fac, setFac] = useState<string[]>([])
  const [cov, setCov] = useState<string[]>([])
  const s = () => `UNIANOVA ${dep[0]} BY ${fac.join(' ')}${cov.length ? ` WITH ${cov.join(' ')}` : ''}.`
  return frame('Univariate', s, !dep.length || !fac.length, onClose, (
    <>
      <VarMover variables={variables} value={dep} onChange={(v) => setDep(v.slice(-1))} label="Dependent Variable:" accept={(v) => !v.isString} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={fac} onChange={setFac} label="Fixed Factor(s):" />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={cov} onChange={setCov} label="Covariate(s):" accept={(v) => !v.isString} />
    </>
  ), () => { setDep([]); setFac([]); setCov([]) })
}

export function FactorDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [extract, setExtract] = useState<'eigen' | 'fixed'>('eigen')
  const [nfac, setNfac] = useState('2')
  const [rotation, setRotation] = useState<'VARIMAX' | 'NOROTATE'>('VARIMAX')
  const s = () => {
    const crit = extract === 'fixed' ? `\n  /CRITERIA FACTORS(${nfac})` : ''
    return `FACTOR\n  /VARIABLES=${vars.join(' ')}\n  /EXTRACTION PC${crit}\n  /ROTATION ${rotation}.`
  }
  return frame('Factor Analysis', s, vars.length < 2, onClose, (
    <>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Variables:" accept={(v) => !v.isString} />
      <fieldset style={{ marginTop: 8, border: '1px solid #c0c0c0', padding: '4px 8px' }}>
        <legend>Extract</legend>
        <label><input type="radio" checked={extract === 'eigen'} onChange={() => setExtract('eigen')} /> Eigenvalue &gt; 1</label>
        <label><input type="radio" checked={extract === 'fixed'} onChange={() => setExtract('fixed')} /> Fixed number:</label>
        <input value={nfac} onChange={(e) => setNfac(e.target.value)} disabled={extract !== 'fixed'} style={{ width: 44 }} />
      </fieldset>
      <fieldset style={{ marginTop: 6, border: '1px solid #c0c0c0', padding: '4px 8px' }}>
        <legend>Rotation</legend>
        <label><input type="radio" checked={rotation === 'NOROTATE'} onChange={() => setRotation('NOROTATE')} /> None</label>
        <label><input type="radio" checked={rotation === 'VARIMAX'} onChange={() => setRotation('VARIMAX')} /> Varimax</label>
      </fieldset>
    </>
  ), () => setVars([]))
}

function depCovDialog(title: string, cmd: (dep: string, cov: string[]) => string) {
  return function Dialog({ variables, onClose }: Props): JSX.Element {
    const [dep, setDep] = useState<string[]>([])
    const [cov, setCov] = useState<string[]>([])
    const s = () => cmd(dep[0], cov)
    return frame(title, s, !dep.length || !cov.length, onClose, (
      <>
        <VarMover variables={variables} value={dep} onChange={(v) => setDep(v.slice(-1))} label="Dependent:" />
        <div style={{ height: 6 }} />
        <VarMover variables={variables} value={cov} onChange={setCov} label="Covariates:" accept={(v) => !v.isString} />
      </>
    ), () => { setDep([]); setCov([]) })
  }
}

export function BinaryLogisticDialog({ variables, onClose }: Props): JSX.Element {
  const [dep, setDep] = useState<string[]>([])
  const [cov, setCov] = useState<string[]>([])
  const [ci, setCi] = useState(false)
  const s = () => `LOGISTIC REGRESSION VARIABLES ${dep[0]}\n  /METHOD=ENTER ${cov.join(' ')}${ci ? '\n  /PRINT=CI(95)' : ''}.`
  return frame('Logistic Regression', s, !dep.length || !cov.length, onClose, (
    <>
      <VarMover variables={variables} value={dep} onChange={(v) => setDep(v.slice(-1))} label="Dependent:" />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={cov} onChange={setCov} label="Covariates:" accept={(v) => !v.isString} />
      <label style={{ marginTop: 6, display: 'block' }}>
        <input type="checkbox" checked={ci} onChange={(e) => setCi(e.target.checked)} /> CI for Exp(B): 95%
      </label>
    </>
  ), () => { setDep([]); setCov([]) })
}
export const MultinomialDialog = depCovDialog('Multinomial Logistic Regression', (dep, cov) => `NOMREG ${dep} WITH ${cov.join(' ')}.`)
export const OrdinalDialog = depCovDialog('Ordinal Regression', (dep, cov) => `PLUM ${dep} WITH ${cov.join(' ')}.`)

export function KMeansDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [k, setK] = useState('2')
  const s = () => `QUICK CLUSTER ${vars.join(' ')}\n  /CRITERIA CLUSTERS(${k}).`
  return frame('K-Means Cluster Analysis', s, !vars.length, onClose, (
    <>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Variables:" accept={(v) => !v.isString} />
      <div className="field-row" style={{ marginTop: 6 }}><span>Number of Clusters:</span><input value={k} onChange={(e) => setK(e.target.value)} style={{ width: 50 }} /></div>
    </>
  ), () => setVars([]))
}

export function HierarchicalDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [method, setMethod] = useState('WARD')
  const s = () => `CLUSTER ${vars.join(' ')}\n  /METHOD ${method}.`
  return frame('Hierarchical Cluster Analysis', s, !vars.length, onClose, (
    <>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Variables:" accept={(v) => !v.isString} />
      <div className="field-row" style={{ marginTop: 6 }}><span>Method:</span>
        <select value={method} onChange={(e) => setMethod(e.target.value)}>
          <option value="WARD">Ward linkage</option>
          <option value="BAVERAGE">Between-groups average</option>
          <option value="COMPLETE">Complete linkage</option>
          <option value="SINGLE">Nearest neighbor</option>
        </select>
      </div>
    </>
  ), () => setVars([]))
}

export function DiscriminantDialog({ variables, onClose }: Props): JSX.Element {
  const [grp, setGrp] = useState<string[]>([])
  const [lo, setLo] = useState('1')
  const [hi, setHi] = useState('2')
  const [indep, setIndep] = useState<string[]>([])
  const s = () => `DISCRIMINANT\n  /GROUPS=${grp[0]}(${lo} ${hi})\n  /VARIABLES=${indep.join(' ')}.`
  return frame('Discriminant Analysis', s, !grp.length || !indep.length, onClose, (
    <>
      <VarMover variables={variables} value={grp} onChange={(v) => setGrp(v.slice(-1))} label="Grouping Variable:" />
      <div className="field-row"><span>Range Min:</span><input value={lo} onChange={(e) => setLo(e.target.value)} style={{ width: 50 }} /><span>Max:</span><input value={hi} onChange={(e) => setHi(e.target.value)} style={{ width: 50 }} /></div>
      <VarMover variables={variables} value={indep} onChange={setIndep} label="Independents:" accept={(v) => !v.isString} />
    </>
  ), () => { setGrp([]); setIndep([]) })
}

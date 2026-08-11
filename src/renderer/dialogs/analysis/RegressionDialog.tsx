import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'
import { Modal } from '../Modal'

export function LinearRegressionDialog({
  variables,
  onClose
}: {
  variables: VariableMetaJson[]
  onClose: () => void
}): JSX.Element {
  const [dep, setDep] = useState<string[]>([])
  const [indep, setIndep] = useState<string[]>([])
  const [stats, setStats] = useState<Set<string>>(new Set(['ESTIMATES', 'MODELFIT']))
  const [dlg, setDlg] = useState(false)

  const syntax = (): string => {
    const kw: string[] = []
    if (stats.has('ESTIMATES')) kw.push('COEFF', 'OUTS')
    if (stats.has('MODELFIT')) kw.push('R', 'ANOVA')
    if (stats.has('CI')) kw.push('CI')
    if (stats.has('DESCRIPTIVES')) kw.push('DESCRIPTIVES')
    return `REGRESSION\n  /MISSING=LISTWISE\n  /STATISTICS=${kw.join(' ') || 'COEFF OUTS R ANOVA'}\n  /DEPENDENT=${dep[0]}\n  /METHOD=ENTER ${indep.join(' ')}.`
  }
  const ok = () => {
    void window.spss.execute(syntax())
    onClose()
  }
  const flip = (k: string, on: boolean) => {
    const n = new Set(stats)
    if (on) n.add(k)
    else n.delete(k)
    setStats(n)
  }
  return (
    <>
      <AnalysisFrame
        title="Linear Regression"
        onOk={ok}
        onPaste={() => {
          window.spss.paste(syntax())
          onClose()
        }}
        onReset={() => {
          setDep([])
          setIndep([])
        }}
        onCancel={onClose}
        okDisabled={dep.length === 0 || indep.length === 0}
        subButtons={[{ label: 'Statistics…', onClick: () => setDlg(true) }]}
      >
        <VarMover variables={variables} value={dep} onChange={(v) => setDep(v.slice(-1))} label="Dependent:" accept={(v) => !v.isString} />
        <div style={{ height: 8 }} />
        <VarMover variables={variables} value={indep} onChange={setIndep} label="Independent(s):" accept={(v) => !v.isString} />
      </AnalysisFrame>
      {dlg && (
        <Modal title="Linear Regression: Statistics" onOk={() => setDlg(false)} onCancel={() => setDlg(false)}>
          <div className="stat-grid">
            {[
              ['ESTIMATES', 'Estimates'],
              ['CI', 'Confidence intervals (95%)'],
              ['MODELFIT', 'Model fit (R², ANOVA)'],
              ['DESCRIPTIVES', 'Descriptives']
            ].map(([k, lab]) => (
              <label key={k}>
                <input type="checkbox" checked={stats.has(k)} onChange={(e) => flip(k, e.target.checked)} /> {lab}
              </label>
            ))}
          </div>
        </Modal>
      )}
    </>
  )
}

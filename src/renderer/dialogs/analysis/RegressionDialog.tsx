import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

export function LinearRegressionDialog({
  variables,
  onClose
}: {
  variables: VariableMetaJson[]
  onClose: () => void
}): JSX.Element {
  const [dep, setDep] = useState<string[]>([])
  const [indep, setIndep] = useState<string[]>([])

  const syntax = (): string =>
    `REGRESSION\n  /MISSING=LISTWISE\n  /STATISTICS=COEFF OUTS R ANOVA\n  /DEPENDENT=${dep[0]}\n  /METHOD=ENTER ${indep.join(' ')}.`
  const ok = () => {
    void window.spss.execute(syntax())
    onClose()
  }
  return (
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
    >
      <VarMover variables={variables} value={dep} onChange={(v) => setDep(v.slice(-1))} label="Dependent:" accept={(v) => !v.isString} />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={indep} onChange={setIndep} label="Independent(s):" accept={(v) => !v.isString} />
    </AnalysisFrame>
  )
}

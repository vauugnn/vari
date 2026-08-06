import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

export function BivariateCorrelationsDialog({
  variables,
  onClose
}: {
  variables: VariableMetaJson[]
  onClose: () => void
}): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [pearson, setPearson] = useState(true)
  const [spearman, setSpearman] = useState(false)
  const [kendall, setKendall] = useState(false)

  const syntax = (): string => {
    const cmds: string[] = []
    if (pearson) cmds.push(`CORRELATIONS\n  /VARIABLES=${vars.join(' ')}.`)
    const np: string[] = []
    if (spearman) np.push('SPEARMAN')
    if (kendall) np.push('KENDALL')
    if (np.length) cmds.push(`NONPAR CORR\n  /VARIABLES=${vars.join(' ')}\n  /PRINT=${np.join(' ')}.`)
    return cmds.join('\n')
  }
  const ok = () => {
    void window.spss.execute(syntax())
    onClose()
  }
  return (
    <AnalysisFrame
      title="Bivariate Correlations"
      onOk={ok}
      onPaste={() => {
        window.spss.paste(syntax())
        onClose()
      }}
      onReset={() => {
        setVars([])
        setPearson(true)
        setSpearman(false)
        setKendall(false)
      }}
      onCancel={onClose}
      okDisabled={vars.length < 2 || (!pearson && !spearman && !kendall)}
    >
      <VarMover variables={variables} value={vars} onChange={setVars} label="Variables:" accept={(v) => !v.isString} />
      <fieldset className="opts" style={{ marginTop: 8, border: '1px solid #c0c0c0', padding: '4px 8px' }}>
        <legend>Correlation Coefficients</legend>
        <label>
          <input type="checkbox" checked={pearson} onChange={(e) => setPearson(e.target.checked)} /> Pearson
        </label>
        <label>
          <input type="checkbox" checked={kendall} onChange={(e) => setKendall(e.target.checked)} /> Kendall&apos;s tau-b
        </label>
        <label>
          <input type="checkbox" checked={spearman} onChange={(e) => setSpearman(e.target.checked)} /> Spearman
        </label>
      </fieldset>
    </AnalysisFrame>
  )
}

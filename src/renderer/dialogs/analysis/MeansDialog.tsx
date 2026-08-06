import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'
import { Modal } from '../Modal'

export function MeansDialog({
  variables,
  onClose
}: {
  variables: VariableMetaJson[]
  onClose: () => void
}): JSX.Element {
  const [deps, setDeps] = useState<string[]>([])
  const [factor, setFactor] = useState<string[]>([])
  const [anova, setAnova] = useState(false)
  const [dlg, setDlg] = useState(false)

  const syntax = (): string => {
    let s = `MEANS TABLES=${deps.join(' ')} BY ${factor[0]}\n  /CELLS=MEAN COUNT STDDEV`
    if (anova) s += `\n  /STATISTICS=ANOVA`
    return s + '.'
  }
  const ok = () => {
    void window.spss.execute(syntax())
    onClose()
  }
  return (
    <>
      <AnalysisFrame
        title="Means"
        onOk={ok}
        onPaste={() => {
          window.spss.paste(syntax())
          onClose()
        }}
        onReset={() => {
          setDeps([])
          setFactor([])
          setAnova(false)
        }}
        onCancel={onClose}
        okDisabled={deps.length === 0 || factor.length === 0}
        subButtons={[{ label: 'Options…', onClick: () => setDlg(true) }]}
      >
        <VarMover variables={variables} value={deps} onChange={setDeps} label="Dependent List:" accept={(v) => !v.isString} />
        <div style={{ height: 8 }} />
        <VarMover variables={variables} value={factor} onChange={(v) => setFactor(v.slice(-1))} label="Independent List:" />
      </AnalysisFrame>
      {dlg && (
        <Modal title="Means: Options" onOk={() => setDlg(false)} onCancel={() => setDlg(false)}>
          <label>
            <input type="checkbox" checked={anova} onChange={(e) => setAnova(e.target.checked)} /> ANOVA table and eta
          </label>
        </Modal>
      )}
    </>
  )
}

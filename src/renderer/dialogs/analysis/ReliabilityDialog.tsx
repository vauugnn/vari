import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'
import { Modal } from '../Modal'

export function ReliabilityDialog({
  variables,
  onClose
}: {
  variables: VariableMetaJson[]
  onClose: () => void
}): JSX.Element {
  const [items, setItems] = useState<string[]>([])
  const [itemTotal, setItemTotal] = useState(false)
  const [dlg, setDlg] = useState(false)

  const syntax = (): string => {
    let s = `RELIABILITY\n  /VARIABLES=${items.join(' ')}\n  /SCALE('ALL VARIABLES')=ALL\n  /MODEL=ALPHA`
    if (itemTotal) s += `\n  /SUMMARY=TOTAL`
    return s + '.'
  }
  const ok = () => {
    void window.spss.execute(syntax())
    onClose()
  }

  return (
    <>
      <AnalysisFrame
        title="Reliability Analysis"
        onOk={ok}
        onPaste={() => {
          window.spss.paste(syntax())
          onClose()
        }}
        onReset={() => {
          setItems([])
          setItemTotal(false)
        }}
        onCancel={onClose}
        okDisabled={items.length < 2}
        subButtons={[{ label: 'Statistics…', onClick: () => setDlg(true) }]}
      >
        <VarMover variables={variables} value={items} onChange={setItems} label="Items:" accept={(v) => !v.isString} />
      </AnalysisFrame>
      {dlg && (
        <Modal title="Reliability Analysis: Statistics" onOk={() => setDlg(false)} onCancel={() => setDlg(false)}>
          <label>
            <input type="checkbox" checked={itemTotal} onChange={(e) => setItemTotal(e.target.checked)} /> Scale if item
            deleted (item-total statistics)
          </label>
        </Modal>
      )}
    </>
  )
}

import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'
import { Modal } from '../Modal'

export function CrosstabsDialog({
  variables,
  onClose
}: {
  variables: VariableMetaJson[]
  onClose: () => void
}): JSX.Element {
  const [rows, setRows] = useState<string[]>([])
  const [cols, setCols] = useState<string[]>([])
  const [chisq, setChisq] = useState(false)
  const [cells, setCells] = useState<Set<string>>(new Set(['COUNT']))
  const [dlg, setDlg] = useState<'stats' | 'cells' | null>(null)

  const toSyntax = (): string => {
    let s = `CROSSTABS\n  /TABLES=${rows.join(' ')} BY ${cols.join(' ')}`
    if (chisq) s += `\n  /STATISTICS=CHISQ`
    const c = ['COUNT', 'EXPECTED', 'ROW', 'COLUMN', 'TOTAL'].filter((k) => cells.has(k))
    s += `\n  /CELLS=${c.join(' ')}`
    return s + '.'
  }
  const ok = () => {
    void window.spss.execute(toSyntax())
    onClose()
  }

  return (
    <>
      <AnalysisFrame
        title="Crosstabs"
        onOk={ok}
        onPaste={() => {
          window.spss.paste(toSyntax())
          onClose()
        }}
        onReset={() => {
          setRows([])
          setCols([])
          setChisq(false)
          setCells(new Set(['COUNT']))
        }}
        onCancel={onClose}
        okDisabled={rows.length === 0 || cols.length === 0}
        subButtons={[
          { label: 'Statistics…', onClick: () => setDlg('stats') },
          { label: 'Cells…', onClick: () => setDlg('cells') }
        ]}
      >
        <VarMover variables={variables} value={rows} onChange={setRows} label="Row(s):" />
        <div style={{ height: 8 }} />
        <VarMover variables={variables} value={cols} onChange={setCols} label="Column(s):" />
      </AnalysisFrame>

      {dlg === 'stats' && (
        <Modal title="Crosstabs: Statistics" onOk={() => setDlg(null)} onCancel={() => setDlg(null)}>
          <label>
            <input type="checkbox" checked={chisq} onChange={(e) => setChisq(e.target.checked)} /> Chi-square
          </label>
        </Modal>
      )}
      {dlg === 'cells' && (
        <Modal title="Crosstabs: Cell Display" onOk={() => setDlg(null)} onCancel={() => setDlg(null)}>
          <div className="stat-grid">
            {[
              ['COUNT', 'Observed'],
              ['EXPECTED', 'Expected'],
              ['ROW', 'Row %'],
              ['COLUMN', 'Column %'],
              ['TOTAL', 'Total %']
            ].map(([k, lab]) => (
              <label key={k}>
                <input
                  type="checkbox"
                  checked={cells.has(k)}
                  onChange={(e) => {
                    const n = new Set(cells)
                    if (e.target.checked) n.add(k)
                    else n.delete(k)
                    setCells(n)
                  }}
                />
                {lab}
              </label>
            ))}
          </div>
        </Modal>
      )}
    </>
  )
}

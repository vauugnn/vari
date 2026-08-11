import { useState } from 'react'
import type { DatasetSummary } from '../../shared/types'
import { Modal } from './Modal'

// Text/CSV Import wizard — the delimiter/type config SPSS shows before loading.
export function ImportWizard({
  path,
  onClose,
  onDone
}: {
  path: string
  onClose: () => void
  onDone: (s: DatasetSummary) => void
}): JSX.Element {
  const [delimiter, setDelimiter] = useState('comma')
  const [firstRowNames, setFirstRowNames] = useState(true)
  const [decimal, setDecimal] = useState('.')
  const [error, setError] = useState('')

  const ok = async (): Promise<void> => {
    try {
      const s = await window.spss.ds.importText(path, { delimiter, firstRowNames, decimal })
      onDone(s)
      onClose()
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e))
    }
  }
  const base = path.split('/').pop()

  return (
    <Modal title="Import Text Data" onOk={() => void ok()} onCancel={onClose}>
      <div style={{ marginBottom: 8, color: '#333' }}>File: {base}</div>
      <div className="field-row">
        <span style={{ width: 110 }}>Delimiter:</span>
        <select value={delimiter} onChange={(e) => setDelimiter(e.target.value)}>
          <option value="comma">Comma ,</option>
          <option value="tab">Tab</option>
          <option value="semicolon">Semicolon ;</option>
          <option value="space">Space</option>
          <option value="pipe">Pipe |</option>
        </select>
      </div>
      <div className="field-row">
        <span style={{ width: 110 }}>Decimal symbol:</span>
        <select value={decimal} onChange={(e) => setDecimal(e.target.value)}>
          <option value=".">Period .</option>
          <option value=",">Comma ,</option>
        </select>
      </div>
      <label style={{ marginTop: 6 }}>
        <input type="checkbox" checked={firstRowNames} onChange={(e) => setFirstRowNames(e.target.checked)} />
        First row contains variable names
      </label>
      {error && <div style={{ marginTop: 6, fontSize: 11, color: '#a33' }}>{error}</div>}
    </Modal>
  )
}

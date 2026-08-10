import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { Modal } from '../Modal'
import { useStore } from '../../state/store'

type Props = { variables: VariableMetaJson[]; onClose: () => void }

export function GoToCaseDialog({ onClose }: Props): JSX.Element {
  const gotoCell = useStore((s) => s.gotoCell)
  const setActiveTab = useStore((s) => s.setActiveTab)
  const [n, setN] = useState('1')
  const submit = () => {
    const row = Math.max(1, parseInt(n, 10) || 1) - 1
    setActiveTab('data')
    gotoCell(row, null)
    onClose()
  }
  return (
    <Modal title="Go to Case" onOk={submit} onCancel={onClose}>
      <div className="field-row"><span>Go to case number:</span>
        <input autoFocus type="number" min={1} value={n} onChange={(e) => setN(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submit()} style={{ width: 100 }} />
      </div>
    </Modal>
  )
}

export function GoToVariableDialog({ variables, onClose }: Props): JSX.Element {
  const gotoCell = useStore((s) => s.gotoCell)
  const setActiveTab = useStore((s) => s.setActiveTab)
  const [idx, setIdx] = useState(0)
  const submit = () => {
    setActiveTab('data')
    gotoCell(null, idx)
    onClose()
  }
  return (
    <Modal title="Go to Variable" onOk={submit} onCancel={onClose}>
      <div className="field-row"><span>Variable:</span>
        <select autoFocus value={idx} onChange={(e) => setIdx(Number(e.target.value))} style={{ width: 200 }}>
          {variables.map((v, i) => <option key={i} value={i}>{v.name}</option>)}
        </select>
      </div>
    </Modal>
  )
}

export function FindDialog({ variables, onClose }: Props): JSX.Element {
  const gotoCell = useStore((s) => s.gotoCell)
  const setActiveTab = useStore((s) => s.setActiveTab)
  const goto = useStore((s) => s.goto)
  const [query, setQuery] = useState('')
  const [scope, setScope] = useState(-1) // -1 = all columns
  const [status, setStatus] = useState('')

  const findNext = async () => {
    if (!query) return
    const startRow = (goto.row ?? -1) + 1
    const res = await window.spss.ds.find(query, Math.max(0, startRow), 0, scope < 0 ? null : scope)
    if (res.found) {
      setActiveTab('data')
      gotoCell(res.row ?? 0, res.col ?? 0)
      setStatus('')
    } else {
      // wrap to the top
      const again = await window.spss.ds.find(query, 0, 0, scope < 0 ? null : scope)
      if (again.found) {
        setActiveTab('data')
        gotoCell(again.row ?? 0, again.col ?? 0)
        setStatus('Search wrapped to the top.')
      } else {
        setStatus('No match found.')
      }
    }
  }

  return (
    <Modal title="Find" onOk={() => void findNext()} okLabel="Find Next" onCancel={onClose}>
      <div className="field-row"><span>Find what:</span>
        <input autoFocus value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && void findNext()} style={{ width: 200 }} />
      </div>
      <div className="field-row"><span>In column:</span>
        <select value={scope} onChange={(e) => setScope(Number(e.target.value))} style={{ width: 200 }}>
          <option value={-1}>All variables</option>
          {variables.map((v, i) => <option key={i} value={i}>{v.name}</option>)}
        </select>
      </div>
      {status && <div style={{ fontSize: 11, color: '#a33', marginTop: 4 }}>{status}</div>}
    </Modal>
  )
}

import { useState } from 'react'
import type { DatasetSummary } from '../../shared/types'
import { Modal } from './Modal'

// Open a dataset from a SQL query. Connection is a SQLAlchemy URL
// (sqlite:///file.db, postgresql://user:pw@host/db) or a plain SQLite file path.
export function OpenDatabaseDialog({ onClose, onDone }: { onClose: () => void; onDone: (s: DatasetSummary) => void }): JSX.Element {
  const [conn, setConn] = useState('sqlite:///')
  const [query, setQuery] = useState('SELECT * FROM ')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const run = async () => {
    setBusy(true)
    setError('')
    try {
      const s = await window.spss.ds.openDatabase(conn.trim(), query.trim())
      onDone(s)
      onClose()
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title="Open Database" onOk={() => void run()} okLabel={busy ? 'Loading…' : 'Read'} okDisabled={busy} onCancel={onClose}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: 460 }}>
        <div className="field-row"><span style={{ width: 90 }}>Connection:</span>
          <input value={conn} onChange={(e) => setConn(e.target.value)} style={{ flex: 1 }} placeholder="sqlite:///path/to/file.db" />
        </div>
        <div>SQL:</div>
        <textarea value={query} onChange={(e) => setQuery(e.target.value)} spellCheck={false}
          style={{ width: '100%', height: 100, fontFamily: 'Menlo, monospace', fontSize: 12, border: '1px solid #7f9db9' }} />
        {error && <div style={{ fontSize: 11, color: '#a33' }}>{error}</div>}
        <div style={{ fontSize: 11, color: '#666' }}>
          Examples: sqlite:///data.db · postgresql://user:pw@host:5432/db · mysql+pymysql://user:pw@host/db
        </div>
      </div>
    </Modal>
  )
}

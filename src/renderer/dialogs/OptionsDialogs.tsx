import { useState } from 'react'
import { Modal } from './Modal'
import { useStore } from '../state/store'

export function RenameDatasetDialog({ onClose }: { onClose: () => void }): JSX.Element {
  const summary = useStore((s) => s.summary)
  const [name, setName] = useState(summary?.name ?? 'DataSet1')
  const submit = () => {
    if (name.trim()) void window.spss.execute(`DATASET NAME ${name.trim()}.`)
    onClose()
  }
  return (
    <Modal title="Rename Dataset" onOk={submit} onCancel={onClose} okDisabled={!name.trim()}>
      <div className="field-row"><span>Name:</span>
        <input autoFocus value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && submit()} style={{ width: 200 }} />
      </div>
    </Modal>
  )
}

// A real (if small) Options dialog wired to the view/display preferences.
export function OptionsDialog({ onClose }: { onClose: () => void }): JSX.Element {
  const s = useStore()
  return (
    <Modal title="Options" onOk={onClose} onCancel={onClose}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, width: 340 }}>
        <div style={{ fontWeight: 600, fontSize: 12, color: '#333' }}>Data Editor Display</div>
        <label><input type="checkbox" checked={s.showGridLines} onChange={s.toggleGridLines} /> Show grid lines</label>
        <label><input type="checkbox" checked={s.showStatusBar} onChange={s.toggleStatusBar} /> Show status bar</label>
        <label><input type="checkbox" checked={s.showValueLabels} onChange={s.toggleValueLabels} /> Display value labels in Data View</label>
        <div style={{ fontSize: 11, color: '#666', marginTop: 6 }}>
          More options (output formatting, default variable type, syntax) are on the roadmap.
        </div>
      </div>
    </Modal>
  )
}

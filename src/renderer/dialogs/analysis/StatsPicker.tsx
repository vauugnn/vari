import { useState } from 'react'
import { Modal } from '../Modal'

export interface StatOption {
  key: string
  label: string
}

export function StatsPicker({
  title,
  options,
  initial,
  onOk,
  onCancel
}: {
  title: string
  options: StatOption[]
  initial: Set<string>
  onOk: (selected: Set<string>) => void
  onCancel: () => void
}): JSX.Element {
  const [sel, setSel] = useState<Set<string>>(new Set(initial))
  const toggle = (k: string) => {
    const next = new Set(sel)
    if (next.has(k)) next.delete(k)
    else next.add(k)
    setSel(next)
  }
  return (
    <Modal title={title} onOk={() => onOk(sel)} onCancel={onCancel}>
      <div className="stat-grid">
        {options.map((o) => (
          <label key={o.key}>
            <input type="checkbox" checked={sel.has(o.key)} onChange={() => toggle(o.key)} />
            {o.label}
          </label>
        ))}
      </div>
    </Modal>
  )
}

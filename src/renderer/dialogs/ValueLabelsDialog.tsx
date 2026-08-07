import { useState } from 'react'
import type { ValueLabel, VariableMetaJson } from '../../shared/types'
import { Modal } from './Modal'

// Value Labels dialog (PHASE-1 section 7): value/label pairs, Add/Change/Remove.
export function ValueLabelsDialog({
  meta,
  onOk,
  onCancel
}: {
  meta: VariableMetaJson
  onOk: (labels: ValueLabel[]) => void
  onCancel: () => void
}): JSX.Element {
  const isString = meta.isString
  const [labels, setLabels] = useState<ValueLabel[]>(meta.valueLabels.map((v) => ({ ...v })))
  const [value, setValue] = useState('')
  const [label, setLabel] = useState('')
  const [selected, setSelected] = useState<number | null>(null)

  const parseVal = (s: string): number | string => (isString ? s : Number(s))

  const add = () => {
    if (value === '') return
    const v = parseVal(value)
    const next = labels.filter((l) => String(l.value) !== String(v))
    next.push({ value: v, label })
    setLabels(next)
    setValue('')
    setLabel('')
  }
  const change = () => {
    if (selected === null) return
    const next = labels.slice()
    next[selected] = { value: parseVal(value), label }
    setLabels(next)
  }
  const remove = () => {
    if (selected === null) return
    setLabels(labels.filter((_, i) => i !== selected))
    setSelected(null)
    setValue('')
    setLabel('')
  }

  return (
    <Modal title="Value Labels" onOk={() => onOk(labels)} onCancel={onCancel}>
      <div className="field-row">
        <span style={{ width: 50 }}>Value:</span>
        <input type="text" value={value} onChange={(e) => setValue(e.target.value)} style={{ width: 120 }} />
      </div>
      <div className="field-row">
        <span style={{ width: 50 }}>Label:</span>
        <input type="text" value={label} onChange={(e) => setLabel(e.target.value)} style={{ width: 200 }} />
      </div>
      <div className="field-row">
        <button className="vl-btn" onClick={add} title="Add">
          +
        </button>
        <button className="vl-btn" onClick={remove} disabled={selected === null} title="Remove">
          −
        </button>
        <button onClick={change} disabled={selected === null} title="Change">
          Change
        </button>
      </div>
      <div className="vl-list">
        {labels.map((l, i) => (
          <div
            key={i}
            className={'vl-item' + (selected === i ? ' vl-item--sel' : '')}
            onMouseDown={() => {
              setSelected(i)
              setValue(String(l.value))
              setLabel(l.label)
            }}
          >
            {String(l.value)} = &quot;{l.label}&quot;
          </div>
        ))}
      </div>
    </Modal>
  )
}

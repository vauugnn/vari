import { useState } from 'react'
import type { MissingJson, VariableMetaJson } from '../../shared/types'
import { Modal } from './Modal'

type Mode = 'none' | 'discrete' | 'range'

// Missing Values dialog (PHASE-1 section 7): three radio options.
export function MissingValuesDialog({
  meta,
  onOk,
  onCancel
}: {
  meta: VariableMetaJson
  onOk: (missing: MissingJson) => void
  onCancel: () => void
}): JSX.Element {
  const isString = meta.isString
  const m = meta.missing
  const [mode, setMode] = useState<Mode>(m.kind)
  const [d, setD] = useState<string[]>(() => {
    const vals = m.kind === 'discrete' ? m.values.map(String) : []
    return [vals[0] ?? '', vals[1] ?? '', vals[2] ?? '']
  })
  const [lo, setLo] = useState(m.kind === 'range' && m.lo != null ? String(m.lo) : '')
  const [hi, setHi] = useState(m.kind === 'range' && m.hi != null ? String(m.hi) : '')
  const [rangeDiscrete, setRangeDiscrete] = useState(
    m.kind === 'range' && m.values.length ? String(m.values[0]) : ''
  )

  const conv = (s: string): number | string => (isString ? s : Number(s))

  const build = (): MissingJson => {
    if (mode === 'none') return { kind: 'none', values: [], lo: null, hi: null }
    if (mode === 'discrete') {
      const values = d.filter((x) => x.trim() !== '').map(conv)
      return { kind: 'discrete', values, lo: null, hi: null }
    }
    const values = rangeDiscrete.trim() !== '' ? [conv(rangeDiscrete)] : []
    return { kind: 'range', values, lo: lo === '' ? null : Number(lo), hi: hi === '' ? null : Number(hi) }
  }

  return (
    <Modal title="Missing Values" onOk={() => onOk(build())} onCancel={onCancel}>
      <div className="radio-block">
        <label>
          <input type="radio" checked={mode === 'none'} onChange={() => setMode('none')} />
          No missing values
        </label>

        <label>
          <input type="radio" checked={mode === 'discrete'} onChange={() => setMode('discrete')} />
          Discrete missing values
        </label>
        <div className="field-row" style={{ marginLeft: 22 }}>
          {[0, 1, 2].map((i) => (
            <input
              key={i}
              type="text"
              disabled={mode !== 'discrete'}
              value={d[i]}
              onChange={(e) => setD(d.map((x, j) => (j === i ? e.target.value : x)))}
              style={{ width: 70 }}
            />
          ))}
        </div>

        <label>
          <input type="radio" disabled={isString} checked={mode === 'range'} onChange={() => setMode('range')} />
          Range plus one optional discrete missing value
        </label>
        <div className="field-row" style={{ marginLeft: 22 }}>
          <span>Low:</span>
          <input type="text" disabled={mode !== 'range'} value={lo} onChange={(e) => setLo(e.target.value)} style={{ width: 70 }} />
          <span>High:</span>
          <input type="text" disabled={mode !== 'range'} value={hi} onChange={(e) => setHi(e.target.value)} style={{ width: 70 }} />
        </div>
        <div className="field-row" style={{ marginLeft: 22 }}>
          <span>Discrete value:</span>
          <input
            type="text"
            disabled={mode !== 'range'}
            value={rangeDiscrete}
            onChange={(e) => setRangeDiscrete(e.target.value)}
            style={{ width: 70 }}
          />
        </div>
      </div>
    </Modal>
  )
}

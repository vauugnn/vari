import { useState } from 'react'
import type { VariableMetaJson } from '../../shared/types'
import { Modal } from './Modal'

// Variable View "Type" column dialog (PHASE-1 section 7).
const TYPES: { label: string; code: string; hasDecimals: boolean }[] = [
  { label: 'Numeric', code: 'F', hasDecimals: true },
  { label: 'Comma', code: 'COMMA', hasDecimals: true },
  { label: 'Dot', code: 'DOT', hasDecimals: true },
  { label: 'Scientific notation', code: 'E', hasDecimals: true },
  { label: 'Date', code: 'DATE', hasDecimals: false },
  { label: 'Dollar', code: 'DOLLAR', hasDecimals: true },
  { label: 'Custom currency', code: 'CCA', hasDecimals: true },
  { label: 'String', code: 'A', hasDecimals: false },
  { label: 'Restricted Numeric (integer with leading zeros)', code: 'N', hasDecimals: false }
]

function codeOf(fmt: string): string {
  const m = /^[A-Za-z]+/.exec(fmt)
  return (m ? m[0] : 'F').toUpperCase()
}

export function VariableTypeDialog({
  meta,
  onOk,
  onCancel
}: {
  meta: VariableMetaJson
  onOk: (format: string) => void
  onCancel: () => void
}): JSX.Element {
  const initialCode = codeOf(meta.format)
  const [code, setCode] = useState(TYPES.some((t) => t.code === initialCode) ? initialCode : 'F')
  const [width, setWidth] = useState(meta.width || 8)
  const [decimals, setDecimals] = useState(meta.decimals || 0)

  const current = TYPES.find((t) => t.code === code)!

  const build = (): string => {
    if (code === 'A') return `A${width}`
    if (code === 'DATE') return `DATE${width || 11}`
    if (code === 'CCA') return `DOLLAR${width}.${decimals}` // custom currency stub -> dollar
    if (current.hasDecimals) return `${code}${width}.${decimals}`
    return `${code}${width}`
  }

  return (
    <Modal title="Variable Type" onOk={() => onOk(build())} onCancel={onCancel}>
      <div style={{ display: 'flex', gap: 14 }}>
        <div className="type-list">
          {TYPES.map((t) => (
            <label key={t.code}>
              <input type="radio" name="vtype" checked={code === t.code} onChange={() => setCode(t.code)} />
              {t.label}
            </label>
          ))}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, paddingTop: 4 }}>
          <div className="field-row">
            <span style={{ width: 80 }}>{code === 'A' ? 'Characters:' : 'Width:'}</span>
            <input type="number" min={1} value={width} onChange={(e) => setWidth(Number(e.target.value))} style={{ width: 60 }} />
          </div>
          <div className="field-row">
            <span style={{ width: 80 }}>Decimal Places:</span>
            <input
              type="number"
              min={0}
              value={decimals}
              disabled={!current.hasDecimals}
              onChange={(e) => setDecimals(Number(e.target.value))}
              style={{ width: 60 }}
            />
          </div>
        </div>
      </div>
    </Modal>
  )
}

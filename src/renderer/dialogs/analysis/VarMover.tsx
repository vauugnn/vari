import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { MeasureIcon } from '../../common/icons'
import './analysis.css'

// The universal source-list / target-box mover (HLD 5.3): variables move via
// the arrow button or double-click, and return to their file-order position
// when removed. `accept` greys out the arrow for invalid types.
export function VarMover({
  variables,
  value,
  onChange,
  label,
  accept
}: {
  variables: VariableMetaJson[]
  value: string[]
  onChange: (names: string[]) => void
  label: string
  accept?: (v: VariableMetaJson) => boolean
}): JSX.Element {
  const [srcSel, setSrcSel] = useState<string[]>([])
  const [tgtSel, setTgtSel] = useState<string[]>([])
  const chosen = new Set(value)
  const source = variables.filter((v) => !chosen.has(v.name))
  const byName = new Map(variables.map((v) => [v.name, v]))

  const canAdd = srcSel.length > 0 && srcSel.every((n) => !accept || accept(byName.get(n)!))

  const add = () => {
    if (!canAdd) return
    onChange([...value, ...srcSel])
    setSrcSel([])
  }
  const remove = () => {
    onChange(value.filter((n) => !tgtSel.includes(n)))
    setTgtSel([])
  }
  const toggle = (list: string[], set: (x: string[]) => void, name: string) =>
    set(list.includes(name) ? list.filter((n) => n !== name) : [...list, name])

  const item = (v: VariableMetaJson, selected: boolean, onClick: () => void, onDbl: () => void) => (
    <div key={v.name} className={'vm-item' + (selected ? ' vm-item--sel' : '')} onClick={onClick} onDoubleClick={onDbl} title={v.label ? `${v.label} [${v.name}]` : v.name}>
      <MeasureIcon measure={v.measure} isString={v.isString} isDate={v.type === 'Date'} size={14} />
      <span className="vm-name">
        {v.label ? v.label : v.name}
        {v.label ? <span className="vm-varname"> [{v.name}]</span> : null}
      </span>
    </div>
  )

  return (
    <div className="vm">
      <div className="vm-col">
        <div className="vm-list">
          {source.map((v) =>
            item(
              v,
              srcSel.includes(v.name),
              () => toggle(srcSel, setSrcSel, v.name),
              () => (!accept || accept(v)) && onChange([...value, v.name])
            )
          )}
        </div>
      </div>
      <div className="vm-arrows">
        <button className="vm-arrow" onClick={value.length && tgtSel.length ? remove : add} disabled={!canAdd && tgtSel.length === 0}>
          {tgtSel.length ? '◀' : '▶'}
        </button>
      </div>
      <div className="vm-col">
        <div className="vm-label">{label}</div>
        <div className="vm-list">
          {value.map((n) => {
            const v = byName.get(n)
            if (!v) return null
            return item(v, tgtSel.includes(n), () => toggle(tgtSel, setTgtSel, n), () => onChange(value.filter((x) => x !== n)))
          })}
        </div>
      </div>
    </div>
  )
}

import { useState } from 'react'
import { Modal } from '../Modal'

// One old→new mapping. `disp` is the human-readable summary shown in the list;
// `rule` is the syntax fragment, e.g. "(1 THRU 5=1)".
interface Mapping {
  disp: string
  rule: string
}

type OldKind = 'value' | 'range' | 'sysmis' | 'else'
type NewKind = 'value' | 'sysmis' | 'copy'

function buildRule(oldKind: OldKind, oldA: string, oldB: string, newKind: NewKind, newVal: string): Mapping | null {
  let oldPart = ''
  let oldDisp = ''
  if (oldKind === 'value') {
    if (oldA.trim() === '') return null
    oldPart = oldA.trim()
    oldDisp = oldA.trim()
  } else if (oldKind === 'range') {
    if (oldA.trim() === '' || oldB.trim() === '') return null
    oldPart = `${oldA.trim()} THRU ${oldB.trim()}`
    oldDisp = `${oldA.trim()} thru ${oldB.trim()}`
  } else if (oldKind === 'sysmis') {
    oldPart = 'SYSMIS'
    oldDisp = 'SYSMIS'
  } else {
    oldPart = 'ELSE'
    oldDisp = 'ELSE'
  }
  let newPart = ''
  let newDisp = ''
  if (newKind === 'value') {
    if (newVal.trim() === '') return null
    newPart = newVal.trim()
    newDisp = newVal.trim()
  } else if (newKind === 'sysmis') {
    newPart = 'SYSMIS'
    newDisp = 'SYSMIS'
  } else {
    newPart = 'COPY'
    newDisp = 'Copy'
  }
  return { disp: `${oldDisp}  →  ${newDisp}`, rule: `(${oldPart}=${newPart})` }
}

// Parse an existing rules string like "(1 THRU 5=1)(ELSE=SYSMIS)" back into a list.
function parseRules(s: string): Mapping[] {
  const out: Mapping[] = []
  const re = /\(([^)=]+)=([^)]+)\)/g
  let m: RegExpExecArray | null
  while ((m = re.exec(s))) {
    const oldp = m[1].trim()
    const newp = m[2].trim()
    const oldDisp = /THRU/i.test(oldp) ? oldp.replace(/THRU/i, 'thru') : oldp
    const newDisp = /COPY/i.test(newp) ? 'Copy' : newp
    out.push({ disp: `${oldDisp}  →  ${newDisp}`, rule: `(${oldp}=${newp})` })
  }
  return out
}

export function OldNewValuesDialog({
  initial,
  onOk,
  onCancel
}: {
  initial: string
  onOk: (rules: string) => void
  onCancel: () => void
}): JSX.Element {
  const [maps, setMaps] = useState<Mapping[]>(() => parseRules(initial))
  const [oldKind, setOldKind] = useState<OldKind>('value')
  const [oldA, setOldA] = useState('')
  const [oldB, setOldB] = useState('')
  const [newKind, setNewKind] = useState<NewKind>('value')
  const [newVal, setNewVal] = useState('')
  const [sel, setSel] = useState<number | null>(null)

  const add = () => {
    const m = buildRule(oldKind, oldA, oldB, newKind, newVal)
    if (!m) return
    setMaps([...maps, m])
    setOldA('')
    setOldB('')
    setNewVal('')
  }
  const change = () => {
    if (sel === null) return
    const m = buildRule(oldKind, oldA, oldB, newKind, newVal)
    if (!m) return
    setMaps(maps.map((x, i) => (i === sel ? m : x)))
  }
  const remove = () => {
    if (sel === null) return
    setMaps(maps.filter((_, i) => i !== sel))
    setSel(null)
  }

  return (
    <Modal title="Recode: Old and New Values" onOk={() => onOk(maps.map((m) => m.rule).join(''))} onCancel={onCancel}>
      <div style={{ display: 'flex', gap: 14 }}>
        <div style={{ width: 210 }}>
          <fieldset style={{ border: '1px solid #c0c0c0', padding: '4px 8px' }}>
            <legend>Old Value</legend>
            <label><input type="radio" checked={oldKind === 'value'} onChange={() => setOldKind('value')} /> Value:
              <input value={oldA} onChange={(e) => setOldA(e.target.value)} onFocus={() => setOldKind('value')} style={{ width: 70, marginLeft: 4 }} />
            </label>
            <label><input type="radio" checked={oldKind === 'sysmis'} onChange={() => setOldKind('sysmis')} /> System-missing</label>
            <label><input type="radio" checked={oldKind === 'range'} onChange={() => setOldKind('range')} /> Range:
              <input value={oldA} onChange={(e) => setOldA(e.target.value)} onFocus={() => setOldKind('range')} style={{ width: 44, margin: '0 3px' }} /> thru
              <input value={oldB} onChange={(e) => setOldB(e.target.value)} onFocus={() => setOldKind('range')} style={{ width: 44, marginLeft: 3 }} />
            </label>
            <label><input type="radio" checked={oldKind === 'else'} onChange={() => setOldKind('else')} /> All other values</label>
          </fieldset>
          <fieldset style={{ border: '1px solid #c0c0c0', padding: '4px 8px', marginTop: 8 }}>
            <legend>New Value</legend>
            <label><input type="radio" checked={newKind === 'value'} onChange={() => setNewKind('value')} /> Value:
              <input value={newVal} onChange={(e) => setNewVal(e.target.value)} onFocus={() => setNewKind('value')} style={{ width: 70, marginLeft: 4 }} />
            </label>
            <label><input type="radio" checked={newKind === 'sysmis'} onChange={() => setNewKind('sysmis')} /> System-missing</label>
            <label><input type="radio" checked={newKind === 'copy'} onChange={() => setNewKind('copy')} /> Copy old value(s)</label>
          </fieldset>
        </div>
        <div style={{ flex: 1 }}>
          <div className="field-row" style={{ gap: 6 }}>
            <button onClick={add}>Add</button>
            <button onClick={change} disabled={sel === null}>Change</button>
            <button onClick={remove} disabled={sel === null}>Remove</button>
          </div>
          <div style={{ fontSize: 11, color: '#555', margin: '4px 0' }}>Old → New:</div>
          <div className="vl-list" style={{ height: 150 }}>
            {maps.map((m, i) => (
              <div
                key={i}
                className={'vl-item' + (sel === i ? ' vl-item--sel' : '')}
                onMouseDown={() => setSel(i)}
              >
                {m.disp}
              </div>
            ))}
          </div>
        </div>
      </div>
    </Modal>
  )
}

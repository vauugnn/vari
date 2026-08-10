import { useEffect, useState } from 'react'
import type { Align, DatasetSummary, Measure, Role, ValueLabel, MissingJson, VariableMetaJson } from '../../shared/types'
import { useStore } from '../state/store'
import { MeasureIcon } from '../common/icons'
import { ContextMenu, type MenuItem } from './ContextMenu'
import { VariableTypeDialog } from '../dialogs/VariableTypeDialog'
import { ValueLabelsDialog } from '../dialogs/ValueLabelsDialog'
import { MissingValuesDialog } from '../dialogs/MissingValuesDialog'
import './grid.css'

const COLUMNS = ['Name', 'Type', 'Width', 'Decimals', 'Label', 'Values', 'Missing', 'Columns', 'Align', 'Measure', 'Role']
const MEASURES: Measure[] = ['scale', 'ordinal', 'nominal']
const ALIGNS: Align[] = ['left', 'right', 'center']
const ROLES: Role[] = ['input', 'target', 'both', 'none', 'partition', 'split']

const DATE_CODES = new Set(['DATE', 'ADATE', 'EDATE', 'SDATE', 'JDATE', 'DATETIME', 'TIME', 'DTIME'])

function codeOf(fmt: string): string {
  const m = /^[A-Za-z]+/.exec(fmt)
  return (m ? m[0] : 'F').toUpperCase()
}

function rebuildFormat(meta: VariableMetaJson, width: number, decimals: number): string {
  const code = codeOf(meta.format)
  if (code === 'A') return `A${width}`
  if (DATE_CODES.has(code)) return `${code}${width}`
  return `${code}${width}.${decimals}`
}

function valueLabelsSummary(vl: ValueLabel[]): string {
  if (!vl.length) return 'None'
  return `{${vl[0].value}, ${vl[0].label}}` + (vl.length > 1 ? '…' : '')
}

function missingSummary(m: MissingJson): string {
  if (m.kind === 'none') return 'None'
  if (m.kind === 'discrete') return m.values.join(', ') || 'None'
  const lo = m.lo ?? 'LO'
  const hi = m.hi ?? 'HI'
  return `${lo}–${hi}${m.values.length ? ', ' + m.values[0] : ''}`
}

// Variable-definition clipboard, shared across remounts (Copy → Paste/Duplicate).
let varClipboard: VariableMetaJson[] = []

function uniqueName(base: string, existing: Set<string>): string {
  let n = 1
  let name = `${base}_${n}`
  while (existing.has(name.toUpperCase())) {
    n++
    name = `${base}_${n}`
  }
  return name
}

type DialogState =
  | { kind: 'type'; index: number }
  | { kind: 'values'; index: number }
  | { kind: 'missing'; index: number }
  | null

export function VariableViewGrid({ summary }: { summary: DatasetSummary }): JSX.Element {
  const setSummary = useStore((s) => s.setSummary)
  const setError = useStore((s) => s.setError)
  const [dialog, setDialog] = useState<DialogState>(null)
  const [newName, setNewName] = useState('')
  // Row-number selection (a..b inclusive), for delete of one or many variables.
  const [rowSel, setRowSel] = useState<{ a: number; b: number } | null>(null)
  const [menu, setMenu] = useState<{ x: number; y: number; items: MenuItem[] } | null>(null)

  const rowSelected = (i: number): boolean =>
    !!rowSel && i >= Math.min(rowSel.a, rowSel.b) && i <= Math.max(rowSel.a, rowSel.b)

  const deleteRange = async (a: number, b: number): Promise<void> => {
    const lo = Math.max(0, Math.min(a, b))
    const hi = Math.min(summary.variables.length - 1, Math.max(a, b))
    try {
      let s
      for (let i = hi; i >= lo; i--) s = await window.spss.ds.deleteVariable(i)
      if (s) setSummary(s)
      setRowSel(null)
      setError(null)
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err))
    }
  }

  const insertAt = async (index: number): Promise<void> => {
    try {
      setSummary(await window.spss.ds.insertVariable(index, null))
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err))
    }
  }

  const copyRows = (a: number, b: number): void => {
    const lo = Math.min(a, b)
    const hi = Math.max(a, b)
    varClipboard = summary.variables.slice(lo, hi + 1).map((v) => ({ ...v }))
  }

  // Paste copied variable attributes onto the selected rows, keeping each
  // target's own name (SPSS "paste" in Variable View copies the definition).
  const pasteRows = async (a: number, b: number): Promise<void> => {
    if (!varClipboard.length) return
    const lo = Math.min(a, b)
    const hi = Math.min(summary.variables.length - 1, Math.max(a, b))
    try {
      let s
      for (let i = lo; i <= hi; i++) {
        const src = varClipboard[(i - lo) % varClipboard.length]
        const patch = { ...src, name: summary.variables[i].name }
        s = await window.spss.ds.setVariableMeta(i, { ...summary.variables[i], ...patch })
      }
      if (s) setSummary(s)
      setError(null)
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err))
    }
  }

  // Duplicate the selected variables (definition only) right after them.
  const duplicateRows = async (a: number, b: number): Promise<void> => {
    const lo = Math.min(a, b)
    const hi = Math.max(a, b)
    const existing = new Set(summary.variables.map((v) => v.name.toUpperCase()))
    try {
      let s: DatasetSummary | null = null
      let at = hi + 1
      for (let i = lo; i <= hi; i++) {
        const src = summary.variables[i]
        const name = uniqueName(src.name, existing)
        existing.add(name.toUpperCase())
        s = await window.spss.ds.insertVariable(at, { ...src, name })
        at++
      }
      if (s) setSummary(s)
      setError(null)
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err))
    }
  }

  const rowMenu = (i: number, e: React.MouseEvent): void => {
    e.preventDefault()
    const sel = rowSelected(i) ? rowSel! : { a: i, b: i }
    setRowSel(sel)
    const lo = Math.min(sel.a, sel.b)
    const count = Math.abs(sel.a - sel.b) + 1
    setMenu({
      x: e.clientX,
      y: e.clientY,
      items: [
        { label: count > 1 ? `Copy ${count} Variables` : 'Copy', onClick: () => copyRows(sel.a, sel.b) },
        { label: 'Paste', disabled: !varClipboard.length, onClick: () => void pasteRows(sel.a, sel.b) },
        { label: count > 1 ? `Duplicate ${count} Variables` : 'Duplicate', onClick: () => void duplicateRows(sel.a, sel.b) },
        { separator: true },
        { label: 'Insert Variable', onClick: () => void insertAt(lo) },
        { label: count > 1 ? `Clear ${count} Variables` : 'Clear', onClick: () => void deleteRange(sel.a, sel.b) }
      ]
    })
  }

  const commit = async (index: number, patch: Partial<VariableMetaJson>): Promise<void> => {
    const meta = { ...summary.variables[index], ...patch }
    try {
      const s = await window.spss.ds.setVariableMeta(index, meta)
      setSummary(s)
      setError(null)
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err))
    }
  }

  const addVariable = async (name: string): Promise<void> => {
    if (!name.trim()) return
    const meta: VariableMetaJson = {
      name: name.trim(),
      type: 'Numeric',
      format: 'F8.2',
      width: 8,
      decimals: 2,
      label: '',
      valueLabels: [],
      missing: { kind: 'none', values: [], lo: null, hi: null },
      columns: 8,
      align: 'right',
      measure: 'scale',
      role: 'input',
      isString: false
    }
    try {
      const s = await window.spss.ds.insertVariable(null, meta)
      setSummary(s)
      setNewName('')
      setError(null)
    } catch (err) {
      setError(String(err instanceof Error ? err.message : err))
    }
  }

  return (
    <div className="vv">
      <table>
        <thead>
          <tr>
            <th className="rownum" />
            {COLUMNS.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {summary.variables.map((v, i) => (
            <tr key={i}>
              <td
                className={'rownum' + (rowSelected(i) ? ' rownum--sel' : '')}
                onMouseDown={(e) => setRowSel(e.shiftKey && rowSel ? { a: rowSel.a, b: i } : { a: i, b: i })}
                onContextMenu={(e) => rowMenu(i, e)}
              >
                {i + 1}
              </td>
              <td>
                <TextCell value={v.name} onCommit={(val) => commit(i, { name: val })} />
              </td>
              <td className="button-cell">
                <button onClick={() => setDialog({ kind: 'type', index: i })}>{v.type}</button>
              </td>
              <td>
                <NumCell value={v.width} onCommit={(val) => commit(i, { format: rebuildFormat(v, val, v.decimals), width: val })} />
              </td>
              <td>
                <NumCell
                  value={v.decimals}
                  disabled={v.isString}
                  onCommit={(val) => commit(i, { format: rebuildFormat(v, v.width, val), decimals: val })}
                />
              </td>
              <td>
                <TextCell value={v.label} onCommit={(val) => commit(i, { label: val })} />
              </td>
              <td className="button-cell">
                <button onClick={() => setDialog({ kind: 'values', index: i })}>{valueLabelsSummary(v.valueLabels)}</button>
              </td>
              <td className="button-cell">
                <button onClick={() => setDialog({ kind: 'missing', index: i })}>{missingSummary(v.missing)}</button>
              </td>
              <td>
                <NumCell value={v.columns} onCommit={(val) => commit(i, { columns: val })} />
              </td>
              <td>
                <SelectCell value={v.align} options={ALIGNS} onCommit={(val) => commit(i, { align: val as Align })} />
              </td>
              <td>
                <MeasureCell
                  value={v.measure}
                  isString={v.isString}
                  isDate={v.type === 'Date'}
                  onCommit={(val) => commit(i, { measure: val })}
                />
              </td>
              <td>
                <SelectCell value={v.role} options={ROLES} onCommit={(val) => commit(i, { role: val as Role })} />
              </td>
            </tr>
          ))}
          {/* trailing empty row: type a name to create a variable */}
          <tr>
            <td className="rownum">{summary.variables.length + 1}</td>
            <td>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onBlur={() => void addVariable(newName)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') void addVariable(newName)
                }}
              />
            </td>
            {COLUMNS.slice(1).map((c) => (
              <td key={c} />
            ))}
          </tr>
        </tbody>
      </table>

      {dialog?.kind === 'type' && (
        <VariableTypeDialog
          meta={summary.variables[dialog.index]}
          onOk={(format) => {
            void commit(dialog.index, { format })
            setDialog(null)
          }}
          onCancel={() => setDialog(null)}
        />
      )}
      {dialog?.kind === 'values' && (
        <ValueLabelsDialog
          meta={summary.variables[dialog.index]}
          onOk={(valueLabels) => {
            void commit(dialog.index, { valueLabels })
            setDialog(null)
          }}
          onCancel={() => setDialog(null)}
        />
      )}
      {dialog?.kind === 'missing' && (
        <MissingValuesDialog
          meta={summary.variables[dialog.index]}
          onOk={(missing) => {
            void commit(dialog.index, { missing })
            setDialog(null)
          }}
          onCancel={() => setDialog(null)}
        />
      )}
      {menu && <ContextMenu x={menu.x} y={menu.y} items={menu.items} onClose={() => setMenu(null)} />}
    </div>
  )
}

function TextCell({ value, onCommit }: { value: string; onCommit: (v: string) => void }): JSX.Element {
  const [v, setV] = useState(value)
  // Resync when the underlying variable changes (reload, insert/delete, undo);
  // rows are keyed by position, so without this the input keeps stale text.
  useEffect(() => setV(value), [value])
  return (
    <input
      value={v}
      onChange={(e) => setV(e.target.value)}
      onBlur={() => v !== value && onCommit(v)}
      onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
    />
  )
}

function NumCell({
  value,
  disabled,
  onCommit
}: {
  value: number
  disabled?: boolean
  onCommit: (v: number) => void
}): JSX.Element {
  const [v, setV] = useState(String(value))
  useEffect(() => setV(String(value)), [value])
  return (
    <input
      type="number"
      disabled={disabled}
      value={v}
      onChange={(e) => setV(e.target.value)}
      onBlur={() => Number(v) !== value && onCommit(Number(v))}
      onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
    />
  )
}

// SPSS shows the measurement-level icon in the Measure cell, not just a word.
function MeasureCell({
  value,
  isString,
  isDate,
  onCommit
}: {
  value: Measure
  isString: boolean
  isDate: boolean
  onCommit: (v: Measure) => void
}): JSX.Element {
  return (
    <div className="measure-cell">
      <MeasureIcon measure={value} isString={isString} isDate={isDate} size={14} />
      <select value={value} onChange={(e) => onCommit(e.target.value as Measure)}>
        {MEASURES.map((o) => (
          <option key={o} value={o}>
            {o.charAt(0).toUpperCase() + o.slice(1)}
          </option>
        ))}
      </select>
    </div>
  )
}

function SelectCell({
  value,
  options,
  onCommit
}: {
  value: string
  options: string[]
  onCommit: (v: string) => void
}): JSX.Element {
  return (
    <select value={value} onChange={(e) => onCommit(e.target.value)}>
      {options.map((o) => (
        <option key={o} value={o}>
          {o.charAt(0).toUpperCase() + o.slice(1)}
        </option>
      ))}
    </select>
  )
}

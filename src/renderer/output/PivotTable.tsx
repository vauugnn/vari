import { useState } from 'react'
import './pivot.css'

interface DimJson {
  label: string
  categories: string[]
}
interface CellJson {
  r: number[]
  c: number[]
  v: string
  kind: string
}
export interface PivotTableJson {
  type: 'PivotTable'
  title: string
  caption: string | null
  corner: string
  rowDims: DimJson[]
  colDims: DimJson[]
  cells: CellJson[]
  colLeaves?: string[]
  colSpanners?: { label: string; span: number }[][]
  footnotes?: string[]
}

// a, b, c, … for footnote markers (SPSS uses lowercase superscript letters).
const footLetter = (i: number): string => String.fromCharCode(97 + (i % 26))

const sizes = (dims: DimJson[]): number[] => dims.map((d) => d.categories.length)
const prod = (xs: number[]): number => xs.reduce((a, b) => a * b, 1)

function leafTuples(dims: DimJson[]): number[][] {
  let out: number[][] = [[]]
  for (const d of dims) {
    const next: number[][] = []
    for (const pre of out) for (let i = 0; i < d.categories.length; i++) next.push([...pre, i])
    out = next
  }
  return out
}

function spanOfCategory(dims: DimJson[], k: number): number {
  return prod(sizes(dims).slice(k + 1))
}
function repeatOfDim(dims: DimJson[], k: number): number {
  return prod(sizes(dims).slice(0, k))
}

// Transpose a rectangular table: swap row/column dimensions and each cell's
// coordinates. (Ragged tables with colLeaves are left as-is.)
function transposeTable(t: PivotTableJson): PivotTableJson {
  return {
    ...t,
    rowDims: t.colDims,
    colDims: t.rowDims,
    cells: t.cells.map((c) => ({ ...c, r: c.c, c: c.r }))
  }
}

export function PivotTableView({ table: raw }: { table: PivotTableJson }): JSX.Element {
  const canTranspose = raw.colLeaves == null
  const [tposed, setTposed] = useState(false)
  // In-place edits: user-overridden cell text keyed by "r|c", and the cell
  // currently being edited.
  const [edits, setEdits] = useState<Record<string, string>>({})
  const [editing, setEditing] = useState<{ key: string; value: string } | null>(null)
  const table = tposed && canTranspose ? transposeTable(raw) : raw
  const { rowDims, colDims, corner } = table
  const rowHeaderCols = Math.max(1, rowDims.length)
  const grouped = table.colLeaves != null

  const cellMap = new Map<string, CellJson>()
  for (const cell of table.cells) cellMap.set(`${cell.r.join(',')}|${cell.c.join(',')}`, cell)

  const leafCols: number[][] = grouped ? table.colLeaves!.map((_, i) => [i]) : leafTuples(colDims)
  const leafRows = leafTuples(rowDims)

  const headerTr: JSX.Element[] = []
  const cornerTh = (rowSpan: number): JSX.Element => (
    <th key="corner" className="pt-corner" rowSpan={rowSpan} colSpan={rowHeaderCols}>
      {corner || ''}
    </th>
  )

  if (grouped) {
    // Ragged columns: spanner rows (top-to-bottom) then a leaf-label row.
    const spanners = table.colSpanners ?? []
    const totalHeaderRows = spanners.length + 1
    spanners.forEach((row, ri) => {
      const ths: JSX.Element[] = []
      if (ri === 0) ths.push(cornerTh(totalHeaderRows))
      row.forEach((g, gi) => {
        const cls = g.label ? 'pt-colhead pt-dimlabel' : 'pt-colhead pt-blankspan'
        ths.push(
          <th key={`s${ri}-${gi}`} className={cls} colSpan={g.span}>
            {g.label}
          </th>
        )
      })
      headerTr.push(<tr key={`h${ri}`}>{ths}</tr>)
    })
    const leafThs: JSX.Element[] = []
    if (spanners.length === 0) leafThs.push(cornerTh(1))
    table.colLeaves!.forEach((lab, i) => (
      leafThs.push(
        <th key={`lf${i}`} className="pt-colhead">
          {lab}
        </th>
      )
    ))
    headerTr.push(<tr key="hleaf">{leafThs}</tr>)
  } else {
    // Nested cross-product columns: a label row (if labelled) + category row per dim.
    const headerRows: { label: boolean; k: number }[] = []
    colDims.forEach((d, k) => {
      if (d.label) headerRows.push({ label: true, k })
      headerRows.push({ label: false, k })
    })
    if (colDims.length === 0) headerRows.push({ label: false, k: -1 })
    const totalHeaderRows = headerRows.length
    headerRows.forEach((hr, ri) => {
      const ths: JSX.Element[] = []
      if (ri === 0) ths.push(cornerTh(totalHeaderRows))
      if (hr.k >= 0) {
        const d = colDims[hr.k]
        const span = hr.label ? d.categories.length * spanOfCategory(colDims, hr.k) : spanOfCategory(colDims, hr.k)
        const groups = repeatOfDim(colDims, hr.k)
        for (let g = 0; g < groups; g++) {
          if (hr.label) {
            ths.push(
              <th key={`l${g}`} className="pt-colhead pt-dimlabel" colSpan={span}>
                {d.label}
              </th>
            )
          } else {
            d.categories.forEach((cat, ci) => {
              ths.push(
                <th key={`c${g}-${ci}`} className="pt-colhead" colSpan={span}>
                  {cat}
                </th>
              )
            })
          }
        }
      }
      headerTr.push(<tr key={`h${ri}`}>{ths}</tr>)
    })
  }

  // ---- body rows with row-header nesting ----
  const bodyTr: JSX.Element[] = []
  leafRows.forEach((rTuple, rIdx) => {
    const cells: JSX.Element[] = []
    if (rowDims.length === 0) {
      cells.push(<th key="rh" className="pt-rowhead" />)
    } else {
      rowDims.forEach((d, k) => {
        const span = prod(sizes(rowDims).slice(k + 1))
        if (rIdx % span === 0) {
          cells.push(
            <th key={`rh${k}`} className="pt-rowhead" rowSpan={span}>
              {d.categories[rTuple[k]]}
            </th>
          )
        }
      })
    }
    leafCols.forEach((cTuple, cIdx) => {
      const cell = cellMap.get(`${rTuple.join(',')}|${cTuple.join(',')}`)
      const key = `${rTuple.join(',')}|${cTuple.join(',')}`
      const shown = key in edits ? edits[key] : cell ? cell.v : ''
      const isEditing = editing?.key === key
      cells.push(
        <td
          key={cIdx}
          className={'pt-cell' + (cell?.kind === 'text' ? ' pt-cell--text' : ' pt-cell--num')}
          title="Double-click to edit"
          onDoubleClick={() => setEditing({ key, value: shown })}
        >
          {isEditing ? (
            <input
              className="pt-cell-input"
              autoFocus
              value={editing!.value}
              onChange={(e) => setEditing({ key, value: e.target.value })}
              onBlur={() => {
                setEdits((m) => ({ ...m, [key]: editing!.value }))
                setEditing(null)
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
                else if (e.key === 'Escape') setEditing(null)
              }}
            />
          ) : (
            shown
          )}
        </td>
      )
    })
    bodyTr.push(<tr key={rIdx}>{cells}</tr>)
  })

  return (
    <div className="pt-wrap">
      <div
        className="pt-title"
        title={canTranspose ? 'Double-click to transpose rows and columns' : undefined}
        onDoubleClick={() => canTranspose && setTposed((v) => !v)}
      >
        {table.title}
        {canTranspose && (
          <button className="pt-transpose" title="Transpose rows and columns" onClick={() => setTposed((v) => !v)}>
            ⇄
          </button>
        )}
      </div>
      <table className="pt-table">
        <thead>{headerTr}</thead>
        <tbody>{bodyTr}</tbody>
      </table>
      {table.caption && <div className="pt-caption">{table.caption}</div>}
      {table.footnotes && table.footnotes.length > 0 && (
        <div className="pt-footnotes">
          {table.footnotes.map((note, i) => (
            <div key={i} className="pt-footnote">
              <sup>{footLetter(i)}</sup>. {note}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

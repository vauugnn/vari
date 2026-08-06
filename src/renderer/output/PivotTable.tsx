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
}

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

export function PivotTableView({ table }: { table: PivotTableJson }): JSX.Element {
  const { rowDims, colDims, corner } = table
  const rowHeaderCols = Math.max(1, rowDims.length)

  // How many header rows: each column dimension contributes a label row (only
  // if it has a label) plus a category row.
  const headerRows: { label: boolean; k: number }[] = []
  colDims.forEach((d, k) => {
    if (d.label) headerRows.push({ label: true, k })
    headerRows.push({ label: false, k })
  })
  if (colDims.length === 0) headerRows.push({ label: false, k: -1 })
  const totalHeaderRows = headerRows.length

  const cellMap = new Map<string, CellJson>()
  for (const cell of table.cells) cellMap.set(`${cell.r.join(',')}|${cell.c.join(',')}`, cell)

  const leafCols = leafTuples(colDims)
  const leafRows = leafTuples(rowDims)

  // ---- column header rows ----
  const headerTr: JSX.Element[] = []
  headerRows.forEach((hr, ri) => {
    const ths: JSX.Element[] = []
    if (ri === 0) {
      ths.push(
        <th
          key="corner"
          className="pt-corner"
          rowSpan={totalHeaderRows}
          colSpan={rowHeaderCols}
        >
          {corner || ''}
        </th>
      )
    }
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
      cells.push(
        <td key={cIdx} className={'pt-cell' + (cell?.kind === 'text' ? ' pt-cell--text' : ' pt-cell--num')}>
          {cell ? cell.v : ''}
        </td>
      )
    })
    bodyTr.push(<tr key={rIdx}>{cells}</tr>)
  })

  return (
    <div className="pt-wrap">
      <div className="pt-title">{table.title}</div>
      <table className="pt-table">
        <thead>{headerTr}</thead>
        <tbody>{bodyTr}</tbody>
      </table>
      {table.caption && <div className="pt-caption">{table.caption}</div>}
    </div>
  )
}

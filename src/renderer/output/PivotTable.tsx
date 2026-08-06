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

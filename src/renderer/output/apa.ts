import type { PivotTableJson } from './PivotTable'

// A pivot table flattened to rows of text: header rows, then body rows. Header and row
// labels appear once where a group starts (blank under it), as in a published table.
export interface TableText {
  head: string[][]
  body: string[][]
}

const esc = (s: string): string => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

export function pivotToText(t: PivotTableJson): TableText {
  if (t.flat) return flatToText(t)
  const rowTuples = tuples(t.rowDims.map((d) => d.categories.length))
  const cells = new Map(t.cells.map((c) => [`${c.r.join(',')}|${c.c.join(',')}`, c.v]))
  const leftCols = Math.max(1, t.rowDims.length)

  let colTuples: number[][]
  const head: string[][] = []
  if (t.colLeaves) {
    colTuples = t.colLeaves.map((_, i) => [i])
    for (const row of t.colSpanners ?? []) {
      const line: string[] = Array(leftCols).fill('')
      for (const g of row) line.push(g.label, ...Array(Math.max(0, g.span - 1)).fill(''))
      head.push(line)
    }
    head.push([...Array(leftCols).fill(''), ...t.colLeaves])
  } else {
    colTuples = tuples(t.colDims.map((d) => d.categories.length))
    t.colDims.forEach((d, k) => {
      const line: string[] = Array(leftCols).fill('')
      colTuples.forEach((tu, i) => {
        const startsGroup = i === 0 || colTuples[i - 1].slice(0, k + 1).join() !== tu.slice(0, k + 1).join()
        line.push(startsGroup ? d.categories[tu[k]] : '')
      })
      head.push(line)
    })
    if (head.length === 0) head.push(Array(leftCols + colTuples.length).fill(''))
  }
  if (t.corner) head[0][0] = t.corner

  const body = rowTuples.map((tu, i) => {
    const labels = t.rowDims.map((d, k) => {
      const startsGroup = i === 0 || rowTuples[i - 1].slice(0, k + 1).join() !== tu.slice(0, k + 1).join()
      return startsGroup ? d.categories[tu[k]] : ''
    })
    while (labels.length < leftCols) labels.push('')
    return [...labels, ...colTuples.map((ct) => cells.get(`${tu.join(',')}|${ct.join(',')}`) ?? '')]
  })
  return { head, body }
}

function flatToText(t: PivotTableJson): TableText {
  const f = t.flat!
  const ncols = f.grid[0]?.length ?? 0
  const width = f.rowHeaderCols
  // Header rows: place each cell at the next free position, honouring spans from rows above.
  const busy: boolean[][] = f.colHeaders.map(() => Array(ncols).fill(false))
  const head = f.colHeaders.map((row, k) => {
    const line: string[] = Array(ncols).fill('')
    let pos = 0
    for (const c of row) {
      while (pos < ncols && busy[k][pos]) pos++
      line[pos] = c.t
      for (let kk = k; kk < Math.min(k + c.rs, busy.length); kk++)
        for (let j = pos; j < Math.min(pos + c.cs, ncols); j++) busy[kk][j] = true
      pos += c.cs
    }
    return [...Array(width).fill(''), ...line]
  })
  if (t.corner && head[0]) head[0][0] = t.corner
  // Body rows: header cells land in the first free header column; spanned rows stay blank.
  const left: number[] = Array(width).fill(0)
  const body = f.grid.map((cells, r) => {
    const labels: string[] = Array(width).fill('')
    let col = 0
    for (const h of f.rowHeaders[r] ?? []) {
      while (col < width && left[col] > 0) col++
      if (col >= width) break
      labels[col] = h.t
      for (let j = col; j < Math.min(col + h.cs, width); j++) left[j] = h.rs // decremented once at the end of this row
      col += h.cs
    }
    for (let j = 0; j < width; j++) if (left[j] > 0) left[j]--
    return [...labels, ...cells]
  })
  return { head, body }
}

function tuples(sizes: number[]): number[][] {
  let out: number[][] = [[]]
  for (const n of sizes) out = out.flatMap((pre) => Array.from({ length: n }, (_, i) => [...pre, i]))
  return out
}

// Tab-separated text (pastes into a spreadsheet) and APA-style HTML (pastes into Word):
// the title in italics, rules above and below the column headings and under the table,
// no vertical lines.
export function toApa(t: PivotTableJson): { html: string; text: string } {
  const { head, body } = pivotToText(t)
  const text = [...head, ...body].map((r) => r.join('\t')).join('\n')
  const cell = (tag: 'th' | 'td', s: string, first: boolean, num: boolean, border: string): string =>
    `<${tag} style="padding:2px 10px;${border}text-align:${first || !num ? 'left' : 'right'};font-weight:normal">${esc(s)}</${tag}>`
  const isNum = (s: string): boolean => /^[-.\d,]+%?$/.test(s.trim())
  const lastHead = head.length - 1
  const headHtml = head
    .map((row, k) => {
      const border = (k === 0 ? 'border-top:1px solid #000;' : '') + (k === lastHead ? 'border-bottom:1px solid #000;' : '')
      return `<tr>${row.map((c, j) => cell('th', c, j === 0, false, border)).join('')}</tr>`
    })
    .join('')
  const bodyHtml = body
    .map((row, i) => {
      const border = i === body.length - 1 ? 'border-bottom:1px solid #000;' : ''
      return `<tr>${row.map((c, j) => cell('td', c, j === 0, isNum(c), border)).join('')}</tr>`
    })
    .join('')
  const notes = (t.footnotes ?? []).map((n, i) => `<p style="margin:2px 0"><i>Note.</i> ${String.fromCharCode(97 + i)}. ${esc(n)}</p>`).join('')
  const html =
    `<p style="margin:0 0 4px"><i>${esc(t.title)}</i></p>` +
    `<table style="border-collapse:collapse;font-family:'Times New Roman',serif;font-size:12pt">` +
    `<thead>${headHtml}</thead><tbody>${bodyHtml}</tbody></table>${notes}`
  return { html, text }
}

export async function copyApa(t: PivotTableJson): Promise<void> {
  const { html, text } = toApa(t)
  await navigator.clipboard.write([
    new ClipboardItem({
      'text/html': new Blob([html], { type: 'text/html' }),
      'text/plain': new Blob([text], { type: 'text/plain' })
    })
  ])
}

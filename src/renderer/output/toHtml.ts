import type { OutputObject } from '../../shared/types'
import type { PivotTableJson } from './PivotTable'

const esc = (s: string): string =>
  s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c] as string)

const prod = (xs: number[]): number => xs.reduce((a, b) => a * b, 1)
const sizes = (dims: { categories: string[] }[]): number[] => dims.map((d) => d.categories.length)

function leafTuples(dims: { categories: string[] }[]): number[][] {
  let out: number[][] = [[]]
  for (const d of dims) {
    const next: number[][] = []
    for (const pre of out) for (let i = 0; i < d.categories.length; i++) next.push([...pre, i])
    out = next
  }
  return out
}

function pivotHtml(t: PivotTableJson): string {
  const rowHeaderCols = Math.max(1, t.rowDims.length)
  const grouped = t.colLeaves != null
  const cornerCell = (rs: number): string =>
    `<th class="pt-corner" rowspan="${rs}" colspan="${rowHeaderCols}">${esc(t.corner || '')}</th>`

  const cellMap = new Map<string, string>()
  for (const c of t.cells) cellMap.set(`${c.r.join(',')}|${c.c.join(',')}`, c.v)

  const leafCols: number[][] = grouped ? t.colLeaves!.map((_, i) => [i]) : leafTuples(t.colDims)
  const leafRows = leafTuples(t.rowDims)

  let html = `<div class="pt-title">${esc(t.title)}</div><table class="pt-table"><thead>`
  if (grouped) {
    const spanners = t.colSpanners ?? []
    const totalHeaderRows = spanners.length + 1
    spanners.forEach((row, ri) => {
      html += '<tr>'
      if (ri === 0) html += cornerCell(totalHeaderRows)
      for (const g of row) html += `<th class="pt-colhead pt-dimlabel" colspan="${g.span}">${esc(g.label)}</th>`
      html += '</tr>'
    })
    html += '<tr>'
    if (spanners.length === 0) html += cornerCell(1)
    for (const lab of t.colLeaves!) html += `<th class="pt-colhead">${esc(lab)}</th>`
    html += '</tr>'
  } else {
    const headerRows: { label: boolean; k: number }[] = []
    t.colDims.forEach((d, k) => {
      if (d.label) headerRows.push({ label: true, k })
      headerRows.push({ label: false, k })
    })
    if (t.colDims.length === 0) headerRows.push({ label: false, k: -1 })
    const totalHeaderRows = headerRows.length
    headerRows.forEach((hr, ri) => {
      html += '<tr>'
      if (ri === 0) html += cornerCell(totalHeaderRows)
      if (hr.k >= 0) {
        const d = t.colDims[hr.k]
        const spanCat = prod(sizes(t.colDims).slice(hr.k + 1))
        const span = hr.label ? d.categories.length * spanCat : spanCat
        const groups = prod(sizes(t.colDims).slice(0, hr.k))
        for (let g = 0; g < groups; g++) {
          if (hr.label) html += `<th class="pt-colhead pt-dimlabel" colspan="${span}">${esc(d.label)}</th>`
          else for (const cat of d.categories) html += `<th class="pt-colhead" colspan="${span}">${esc(cat)}</th>`
        }
      }
      html += '</tr>'
    })
  }
  html += '</thead><tbody>'
  leafRows.forEach((rTuple, rIdx) => {
    html += '<tr>'
    if (t.rowDims.length === 0) html += '<th class="pt-rowhead"></th>'
    else
      t.rowDims.forEach((d, k) => {
        const span = prod(sizes(t.rowDims).slice(k + 1))
        if (rIdx % span === 0) html += `<th class="pt-rowhead" rowspan="${span}">${esc(d.categories[rTuple[k]])}</th>`
      })
    leafCols.forEach((cTuple) => {
      const v = cellMap.get(`${rTuple.join(',')}|${cTuple.join(',')}`) ?? ''
      html += `<td class="pt-cell pt-cell--num">${esc(v)}</td>`
    })
    html += '</tr>'
  })
  html += '</tbody></table>'
  if (t.caption) html += `<div class="pt-caption">${esc(t.caption)}</div>`
  if (t.footnotes && t.footnotes.length) {
    html += '<div class="pt-footnotes">'
    t.footnotes.forEach((note, i) => {
      html += `<div class="pt-footnote"><sup>${String.fromCharCode(97 + (i % 26))}</sup>. ${esc(note)}</div>`
    })
    html += '</div>'
  }
  return `<div class="pt-wrap">${html}</div>`
}

function itemHtml(o: OutputObject): string {
  switch (o.type) {
    case 'Title':
      return `<div class="out-title">${esc((o as { text: string }).text)}</div>`
    case 'TextBlock':
      return `<div class="out-text">${esc((o as { text: string }).text)}</div>`
    case 'Warning':
      return `<div class="out-warning">${esc((o as { text: string }).text)}</div>`
    case 'Error':
      return `<div class="out-error">${esc((o as { text: string }).text)}</div>`
    case 'PivotTable':
      return pivotHtml(o as unknown as PivotTableJson)
    case 'Chart':
      return `<div class="out-chart">${(o as unknown as { svg: string }).svg}</div>`
    default:
      return `<div>${esc(JSON.stringify(o))}</div>`
  }
}

const STYLE = `
body{font-family:Tahoma,'Segoe UI',sans-serif;font-size:12px;color:#000;background:#fff;margin:16px;}
.out-title{font-weight:bold;font-size:13px;margin:8px 0 4px;}
.out-text{white-space:pre-wrap;margin:4px 0;}
.out-warning{color:#8a6d00;white-space:pre-wrap;margin:4px 0;}
.out-error{color:#a00000;white-space:pre-wrap;margin:4px 0;}
.pt-wrap{margin:10px 0;display:inline-block;}
.pt-title{font-weight:bold;margin:6px 0 4px;}
.pt-table{border-collapse:collapse;border:1px solid #000;font-size:12px;}
.pt-table th,.pt-table td{padding:1px 8px;line-height:17px;vertical-align:top;white-space:nowrap;}
.pt-colhead{text-align:center;font-weight:normal;border-bottom:1px solid #000;border-left:1px solid #d9d9d9;background:#fbfbfb;}
.pt-dimlabel{text-align:center;font-weight:normal;border-bottom:1px solid #d9d9d9;}
.pt-corner{text-align:left;font-weight:normal;border-right:1px solid #000;border-bottom:1px solid #000;background:#fbfbfb;}
.pt-rowhead{text-align:left;font-weight:normal;border-right:1px solid #000;background:#fbfbfb;}
.pt-cell{border-left:1px solid #eee;}
.pt-cell--num{text-align:right;}
.pt-caption{font-size:11px;color:#333;margin-top:3px;}
`

export function documentHtml(items: OutputObject[]): string {
  const body = items.map(itemHtml).join('\n')
  return `<!doctype html>
<html><head><meta charset="utf-8"><title>SPSS Output</title><style>${STYLE}</style></head>
<body>${body}</body></html>`
}

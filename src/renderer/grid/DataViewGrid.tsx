import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import type { DatasetSummary, VariableMetaJson } from '../../shared/types'
import { useStore } from '../state/store'
import { MeasureIcon } from '../common/icons'
import { ContextMenu, type MenuItem } from './ContextMenu'
import './grid.css'

const ROW_H = 20
const BLOCK = 250
const OVERSCAN = 6
const MIN_COL = 56
const MAX_COL = 320

interface Sel {
  r0: number
  c0: number
  r1: number
  c1: number
}

function colWidthPx(chars: number): number {
  return Math.max(MIN_COL, Math.min(MAX_COL, chars * 7 + 18))
}

export function DataViewGrid({ summary }: { summary: DatasetSummary }): JSX.Element {
  const showValueLabels = useStore((s) => s.showValueLabels)
  const storeRev = useStore((s) => s.revision)
  const goto = useStore((s) => s.goto)

  const nVars = summary.nVars
  const [nRows, setNRows] = useState(summary.nRows)
  useEffect(() => setNRows(summary.nRows), [summary])

  const EMPTY_COL_W = colWidthPx(8)

  const baseWidths = useMemo(
    () => summary.variables.map((v) => colWidthPx(v.columns || v.width || 8)),
    [summary]
  )
  const [wOverride, setWOverride] = useState<Record<number, number>>({})
  useEffect(() => setWOverride({}), [summary])
  const colWidths = baseWidths.map((w, i) => wOverride[i] ?? w)
  const realWidth = colWidths.reduce((a, b) => a + b, 0)
  const gutterW = Math.max(40, String(Math.max(nRows + 1, 1)).length * 9 + 20)

  // ---- windowed row cache ------------------------------------------
  const cacheRef = useRef<Map<number, string[][]>>(new Map())
  const loadingRef = useRef<Set<number>>(new Set())
  const [, forceRender] = useReducer((x) => x + 1, 0)
  const [dataRev, bumpData] = useReducer((x) => x + 1, 0)

  const scrollRef = useRef<HTMLDivElement>(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [viewportH, setViewportH] = useState(400)
  const [viewportW, setViewportW] = useState(800)

  useEffect(() => {
    cacheRef.current.clear()
    loadingRef.current.clear()
    forceRender()
  }, [showValueLabels, storeRev, dataRev])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const ro = new ResizeObserver(() => {
      setViewportH(el.clientHeight)
      setViewportW(el.clientWidth)
    })
    ro.observe(el)
    setViewportH(el.clientHeight)
    setViewportW(el.clientWidth)
    return () => ro.disconnect()
  }, [])

  // Fill the viewport with empty rows/columns so it always looks like a
  // spreadsheet (SPSS shows an empty grid even with no data), plus one trailing
  // slot for creating the next case / variable.
  const fillCols = Math.max(1, Math.ceil((viewportW - gutterW - realWidth) / EMPTY_COL_W))
  const displayCols = nVars + fillCols
  const fillRows = Math.max(1, Math.ceil(viewportH / ROW_H) - nRows + 2)
  const displayRows = nRows + fillRows

  const start = Math.max(0, Math.floor(scrollTop / ROW_H) - OVERSCAN)
  const end = Math.min(displayRows, Math.ceil((scrollTop + viewportH) / ROW_H) + OVERSCAN)

  useEffect(() => {
    const b0 = Math.floor(start / BLOCK)
    const b1 = Math.floor((Math.max(end, 1) - 1) / BLOCK)
    for (let b = b0; b <= b1; b++) {
      if (cacheRef.current.has(b) || loadingRef.current.has(b)) continue
      const offset = b * BLOCK
      if (offset >= nRows) continue
      loadingRef.current.add(b)
      void window.spss.ds.getRows(offset, BLOCK, showValueLabels).then((w) => {
        cacheRef.current.set(b, w.rows)
        loadingRef.current.delete(b)
        if (w.nRows !== nRows) setNRows(w.nRows)
        forceRender()
      })
    }
  }, [start, end, showValueLabels, storeRev, dataRev, nRows])

  const cellText = useCallback(
    (r: number, c: number): string => {
      if (r >= nRows || c >= nVars) return ''
      const rows = cacheRef.current.get(Math.floor(r / BLOCK))
      if (!rows) return ''
      return rows[r - Math.floor(r / BLOCK) * BLOCK]?.[c] ?? ''
    },
    [nRows, nVars]
  )

  // ---- selection + editing -----------------------------------------
  const [sel, setSel] = useState<Sel | null>(null)
  const draggingRef = useRef(false)

  // React to a Go-to / Find navigation target: select the cell and scroll it
  // into view.
  useEffect(() => {
    if (goto.nonce === 0) return
    const r = goto.row ?? (sel?.r1 ?? 0)
    const c = goto.col ?? (sel?.c1 ?? 0)
    setSel({ r0: r, c0: c, r1: r, c1: c })
    const el = scrollRef.current
    if (el) el.scrollTop = Math.max(0, r * ROW_H - el.clientHeight / 2)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [goto.nonce])
  const [edit, setEdit] = useState<{ r: number; c: number; value: string } | null>(null)

  const inSel = (r: number, c: number): boolean => {
    if (!sel) return false
    return (
      r >= Math.min(sel.r0, sel.r1) &&
      r <= Math.max(sel.r0, sel.r1) &&
      c >= Math.min(sel.c0, sel.c1) &&
      c <= Math.max(sel.c0, sel.c1)
    )
  }

  const startEdit = (r: number, c: number, initial?: string) => {
    if (c >= nVars && c !== nVars) return
    setEdit({ r, c, value: initial ?? cellText(r, c) })
  }

  const commitEdit = useCallback(
    async (move: 'down' | 'right' | null) => {
      if (!edit) return
      const { r, c, value } = edit
      setEdit(null)
      try {
        let col = c
        if (c >= nVars) {
          // Typing into the trailing blank column creates VAR0000n / F8.2.
          const s = await window.spss.ds.insertVariable(null, null)
          useStore.getState().setSummary(s)
          col = s.nVars - 1
        }
        if (value !== '') {
          await window.spss.ds.setCell(r, col, value)
          if (r >= nRows) setNRows(r + 1)
        }
        bumpData()
      } catch (err) {
        useStore.getState().setError(String(err instanceof Error ? err.message : err))
      }
      if (move === 'down') setSel({ r0: r + 1, c0: c, r1: r + 1, c1: c })
      if (move === 'right') setSel({ r0: r, c0: c + 1, r1: r, c1: c + 1 })
    },
    [edit, nVars, nRows]
  )

  const onCellMouseDown = (r: number, c: number, e: React.MouseEvent) => {
    if (edit) void commitEdit(null)
    draggingRef.current = true
    if (e.shiftKey && sel) setSel({ ...sel, r1: r, c1: c })
    else setSel({ r0: r, c0: c, r1: r, c1: c })
  }
  const onCellMouseEnter = (r: number, c: number) => {
    if (draggingRef.current && sel) setSel({ ...sel, r1: r, c1: c })
  }
  useEffect(() => {
    const up = () => (draggingRef.current = false)
    window.addEventListener('mouseup', up)
    return () => window.removeEventListener('mouseup', up)
  }, [])

  // ---- context menu, column resize, clipboard ----------------------
  const [menu, setMenu] = useState<{ x: number; y: number; items: MenuItem[] } | null>(null)
  const resizeRef = useRef<{ c: number; startX: number; startW: number; w: number } | null>(null)

  const existingNames = (): Set<string> => new Set(summary.variables.map((v) => v.name.toUpperCase()))

  const insertVarAt = async (index: number): Promise<void> => {
    const s = await window.spss.ds.insertVariable(index, defaultVarMeta(existingNames()))
    useStore.getState().setSummary(s)
  }
  // Delete an inclusive column range, highest index first so earlier indices
  // stay valid as the dataset reindexes.
  const deleteVarRange = async (c0: number, c1: number): Promise<void> => {
    const lo = Math.max(0, Math.min(c0, c1))
    const hi = Math.min(nVars - 1, Math.max(c0, c1))
    let summary: DatasetSummary | null = null
    for (let c = hi; c >= lo; c--) summary = await window.spss.ds.deleteVariable(c)
    if (summary) {
      useStore.getState().setSummary(summary)
      setSel(null)
    }
  }
  const deleteCaseRange = async (r0: number, r1: number): Promise<void> => {
    const lo = Math.max(0, Math.min(r0, r1))
    const hi = Math.min(nRows - 1, Math.max(r0, r1))
    let last: { nRows: number } | null = null
    for (let r = hi; r >= lo; r--) last = await window.spss.ds.deleteCase(r)
    if (last) {
      setNRows(last.nRows)
      bumpData()
      setSel(null)
    }
  }
  const insertCaseAt = async (index: number): Promise<void> => {
    const res = await window.spss.ds.insertCase(index)
    setNRows(res.nRows)
    bumpData()
  }
  const runDescriptives = (c: number): void => {
    if (c < nVars) void window.spss.execute(`DESCRIPTIVES VARIABLES=${summary.variables[c].name}.`)
  }

  const copySelection = async (): Promise<void> => {
    if (!sel) return
    const [r0, r1] = [Math.min(sel.r0, sel.r1), Math.max(sel.r0, sel.r1)]
    const [c0, c1] = [Math.min(sel.c0, sel.c1), Math.max(sel.c0, sel.c1)]
    const lines: string[] = []
    for (let r = r0; r <= r1; r++) {
      const cols: string[] = []
      for (let c = c0; c <= c1; c++) cols.push(cellText(r, c))
      lines.push(cols.join('\t'))
    }
    try {
      await navigator.clipboard.writeText(lines.join('\n'))
    } catch {
      /* clipboard unavailable */
    }
  }
  const pasteSelection = async (): Promise<void> => {
    if (!sel) return
    let text = ''
    try {
      text = await navigator.clipboard.readText()
    } catch {
      return
    }
    if (!text) return
    const r0 = Math.min(sel.r0, sel.r1)
    const c0 = Math.min(sel.c0, sel.c1)
    const grid = text.replace(/\r/g, '').replace(/\n$/, '').split('\n').map((l) => l.split('\t'))
    const need = c0 + Math.max(...grid.map((g) => g.length))
    let cur = nVars
    while (cur < need) {
      const s = await window.spss.ds.insertVariable(null, null)
      useStore.getState().setSummary(s)
      cur = s.nVars
    }
    for (let i = 0; i < grid.length; i++)
      for (let j = 0; j < grid[i].length; j++) {
        if (grid[i][j] === '') continue
        try {
          await window.spss.ds.setCell(r0 + i, c0 + j, grid[i][j])
        } catch {
          /* skip bad cell */
        }
      }
    setNRows(Math.max(nRows, r0 + grid.length))
    bumpData()
  }

  const startResize = (c: number, e: React.MouseEvent): void => {
    e.stopPropagation()
    e.preventDefault()
    resizeRef.current = { c, startX: e.clientX, startW: colWidths[c], w: colWidths[c] }
  }
  useEffect(() => {
    const mm = (e: MouseEvent): void => {
      const r = resizeRef.current
      if (!r) return
      r.w = Math.max(MIN_COL, r.startW + (e.clientX - r.startX))
      setWOverride((o) => ({ ...o, [r.c]: r.w }))
    }
    const mu = async (): Promise<void> => {
      const r = resizeRef.current
      if (!r) return
      resizeRef.current = null
      const chars = Math.max(1, Math.round((r.w - 18) / 7))
      const v = summary.variables[r.c]
      if (v) {
        try {
          useStore.getState().setSummary(await window.spss.ds.setVariableMeta(r.c, { ...v, columns: chars }))
        } catch {
          /* ignore */
        }
      }
    }
    window.addEventListener('mousemove', mm)
    window.addEventListener('mouseup', mu)
    return () => {
      window.removeEventListener('mousemove', mm)
      window.removeEventListener('mouseup', mu)
    }
  }, [summary])

  const headerMenu = (c: number, e: React.MouseEvent): void => {
    e.preventDefault()
    // Keep an existing multi-column selection if the click landed inside it;
    // otherwise select just this column.
    const inCols = sel && c >= Math.min(sel.c0, sel.c1) && c <= Math.max(sel.c0, sel.c1)
    const c0 = inCols ? Math.min(sel!.c0, sel!.c1) : c
    const c1 = inCols ? Math.max(sel!.c0, sel!.c1) : c
    setSel({ r0: 0, c0, r1: displayRows - 1, c1 })
    const count = Math.min(c1, nVars - 1) - c0 + 1
    setMenu({
      x: e.clientX,
      y: e.clientY,
      items: [
        { label: 'Insert Variable', onClick: () => void insertVarAt(c0) },
        { label: count > 1 ? `Clear ${count} Variables` : 'Clear', disabled: c0 >= nVars, onClick: () => void deleteVarRange(c0, c1) },
        { separator: true },
        { label: 'Descriptive Statistics', disabled: c0 >= nVars, onClick: () => runDescriptives(c0) }
      ]
    })
  }
  const gutterMenu = (r: number, e: React.MouseEvent): void => {
    e.preventDefault()
    const inRows = sel && r >= Math.min(sel.r0, sel.r1) && r <= Math.max(sel.r0, sel.r1)
    const r0 = inRows ? Math.min(sel!.r0, sel!.r1) : r
    const r1 = inRows ? Math.max(sel!.r0, sel!.r1) : r
    setSel({ r0, c0: 0, r1, c1: displayCols - 1 })
    const count = Math.min(r1, nRows - 1) - r0 + 1
    setMenu({
      x: e.clientX,
      y: e.clientY,
      items: [
        { label: 'Insert Case', onClick: () => void insertCaseAt(r0) },
        { label: count > 1 ? `Clear ${count} Cases` : 'Clear', disabled: r0 >= nRows, onClick: () => void deleteCaseRange(r0, r1) }
      ]
    })
  }
  const cellMenu = (r: number, c: number, e: React.MouseEvent): void => {
    e.preventDefault()
    if (!inSel(r, c)) setSel({ r0: r, c0: c, r1: r, c1: c })
    setMenu({
      x: e.clientX,
      y: e.clientY,
      items: [
        { label: 'Copy', onClick: () => void copySelection() },
        { label: 'Paste', onClick: () => void pasteSelection() }
      ]
    })
  }

  const onGridKeyDown = (e: React.KeyboardEvent) => {
    if (edit) return
    if ((e.metaKey || e.ctrlKey) && (e.key === 'c' || e.key === 'C')) {
      void copySelection()
      return
    }
    if ((e.metaKey || e.ctrlKey) && (e.key === 'v' || e.key === 'V')) {
      void pasteSelection()
      return
    }
    if (!sel) return
    const { r1, c1 } = sel
    if (e.key === 'Enter' || e.key === 'F2') {
      startEdit(r1, c1)
      e.preventDefault()
    } else if (e.key === 'ArrowDown') setSel({ r0: Math.min(r1 + 1, displayRows - 1), c0: c1, r1: Math.min(r1 + 1, displayRows - 1), c1 })
    else if (e.key === 'ArrowUp') setSel({ r0: Math.max(r1 - 1, 0), c0: c1, r1: Math.max(r1 - 1, 0), c1 })
    else if (e.key === 'ArrowRight') setSel({ r0: r1, c0: Math.min(c1 + 1, displayCols - 1), r1, c1: Math.min(c1 + 1, displayCols - 1) })
    else if (e.key === 'ArrowLeft') setSel({ r0: r1, c0: Math.max(c1 - 1, 0), r1, c1: Math.max(c1 - 1, 0) })
    else if (e.key.length === 1 && !e.metaKey && !e.ctrlKey) startEdit(r1, c1, e.key)
  }

  const totalWidth = gutterW + realWidth + fillCols * EMPTY_COL_W

  const rows: JSX.Element[] = []
  for (let r = start; r < end; r++) {
    const cells: JSX.Element[] = []
    for (let c = 0; c < displayCols; c++) {
      const w = c < nVars ? colWidths[c] : colWidthPx(8)
      const v = c < nVars ? summary.variables[c] : null
      const rightAlign = v ? !v.isString : true
      const isEditing = edit && edit.r === r && edit.c === c
      const text = cellText(r, c)
      cells.push(
        <div
          key={c}
          className={'cell' + (inSel(r, c) ? ' cell--sel' : '') + (rightAlign ? ' cell--num' : '')}
          style={{ width: w }}
          onMouseDown={(e) => onCellMouseDown(r, c, e)}
          onMouseEnter={() => onCellMouseEnter(r, c)}
          onDoubleClick={() => startEdit(r, c)}
          onContextMenu={(e) => cellMenu(r, c, e)}
        >
          {isEditing ? (
            <input
              className="cell-input"
              autoFocus
              value={edit.value}
              onChange={(e) => setEdit({ ...edit, value: e.target.value })}
              onBlur={() => void commitEdit(null)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') void commitEdit('down')
                else if (e.key === 'Tab') {
                  e.preventDefault()
                  void commitEdit('right')
                } else if (e.key === 'Escape') setEdit(null)
              }}
            />
          ) : (
            text
          )}
        </div>
      )
    }
    rows.push(
      <div key={r} className="row" style={{ height: ROW_H }}>
        <div
          className={'gutter-cell' + (sel && r >= Math.min(sel.r0, sel.r1) && r <= Math.max(sel.r0, sel.r1) ? ' gutter-cell--sel' : '')}
          style={{ width: gutterW }}
          onMouseDown={(e) => {
            draggingRef.current = true
            if (e.shiftKey && sel) setSel({ r0: sel.r0, c0: 0, r1: r, c1: displayCols - 1 })
            else setSel({ r0: r, c0: 0, r1: r, c1: displayCols - 1 })
          }}
          onMouseEnter={() => {
            if (draggingRef.current && sel && sel.c0 === 0 && sel.c1 === displayCols - 1)
              setSel({ ...sel, r1: r })
          }}
          onContextMenu={(e) => gutterMenu(r, e)}
        >
          {r + 1}
        </div>
        {cells}
      </div>
    )
  }

  return (
    <div
      className="grid"
      ref={scrollRef}
      tabIndex={0}
      onKeyDown={onGridKeyDown}
      onScroll={(e) => setScrollTop((e.target as HTMLDivElement).scrollTop)}
    >
      <div className="grid-inner" style={{ width: totalWidth }}>
        <div className="header-row" style={{ height: ROW_H }}>
          <div className="corner" style={{ width: gutterW }} />
          {summary.variables.map((v, c) => (
            <div
              key={c}
              className={'col-head' + (sel && c >= Math.min(sel.c0, sel.c1) && c <= Math.max(sel.c0, sel.c1) ? ' col-head--sel' : '')}
              style={{ width: colWidths[c] }}
              title={v.label || v.name}
              onMouseDown={(e) => {
                draggingRef.current = true
                if (e.shiftKey && sel) setSel({ r0: 0, c0: sel.c0, r1: displayRows - 1, c1: c })
                else setSel({ r0: 0, c0: c, r1: displayRows - 1, c1: c })
              }}
              onMouseEnter={() => {
                if (draggingRef.current && sel && sel.r0 === 0 && sel.r1 === displayRows - 1)
                  setSel({ ...sel, c1: c })
              }}
              onContextMenu={(e) => headerMenu(c, e)}
            >
              <span className="col-head-inner">
                <MeasureIcon measure={v.measure} isString={v.isString} isDate={v.type === 'Date'} size={14} />
                <span className="col-head-name">{v.name}</span>
              </span>
              <div className="col-resize" onMouseDown={(e) => startResize(c, e)} />
            </div>
          ))}
          {Array.from({ length: fillCols }, (_, k) => (
            <div key={'e' + k} className="col-head col-head--empty" style={{ width: EMPTY_COL_W }} />
          ))}
        </div>
        <div style={{ height: start * ROW_H }} />
        {rows}
        <div style={{ height: Math.max(0, (displayRows - end) * ROW_H) }} />
      </div>
      {menu && <ContextMenu x={menu.x} y={menu.y} items={menu.items} onClose={() => setMenu(null)} />}
    </div>
  )
}

function defaultVarMeta(existing: Set<string>): VariableMetaJson {
  let n = existing.size + 1
  let name = 'VAR' + String(n).padStart(5, '0')
  while (existing.has(name.toUpperCase())) {
    n++
    name = 'VAR' + String(n).padStart(5, '0')
  }
  return {
    name,
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
}

import { useState, useRef, useEffect } from 'react'
import type { OutputObject } from '../../shared/types'
import { PivotTableView, type PivotTableJson } from '../output/PivotTable'
import './output.css'

// The default bar/fill and edge colours the sidecar draws with; the editor
// retints these in the SVG so the user can recolour bars/fills live.
const DEFAULT_FILL = '#4e79c4'
const DEFAULT_EDGE = '#2f4f8a'

const SWATCHES = ['#4e79c4', '#5aa552', '#d9a441', '#d9433f', '#8c66b5', '#41b2c2', '#6d6e71', '#1192e8']

function retint(svg: string, fill: string, edge: string): string {
  const rx = (hex: string): RegExp => new RegExp(hex.replace('#', '#?'), 'gi')
  return svg.replace(rx(DEFAULT_FILL), fill).replace(rx(DEFAULT_EDGE), edge)
}

// The fill colour of an SVG element, from either its inline style or `fill`
// attribute, normalised to lowercase.
function fillOf(el: Element): string {
  const style = el.getAttribute('style') || ''
  const m = /fill:\s*([^;]+)/i.exec(style)
  if (m) return m[1].trim().toLowerCase()
  return (el.getAttribute('fill') || '').trim().toLowerCase()
}

// Set a path's fill in whichever way it was originally specified.
function setFillOf(el: SVGElement, color: string): void {
  const style = el.getAttribute('style') || ''
  if (/fill:/i.test(style)) el.setAttribute('style', style.replace(/fill:\s*[^;]+/i, `fill: ${color}`))
  else el.setAttribute('fill', color)
}

// A chart: click to enlarge (lightbox), double-click to open the Chart Editor.
// In the editor you can click an individual bar/wedge to select it and recolour
// just that element (SPSS Chart Editor behaviour), or recolour every bar at once.
function ChartView({ svg }: { svg: string }): JSX.Element {
  const [big, setBig] = useState(false)
  const [editing, setEditing] = useState(false)
  const [fill, setFill] = useState(DEFAULT_FILL)
  const [edge, setEdge] = useState(DEFAULT_EDGE)
  const [sel, setSel] = useState<SVGElement | null>(null)
  const editRef = useRef<HTMLDivElement>(null)
  const shown = fill === DEFAULT_FILL && edge === DEFAULT_EDGE ? svg : retint(svg, fill, edge)

  // In edit mode, wire click handlers onto the data bars/wedges. The bars are
  // the filled paths whose colour matches the current fill (the sidecar draws
  // every bar in that one colour); gridlines and the frame are drawn in grey/
  // white and stay untouched. Clicking a bar selects it (outline) so the
  // controls can recolour that single element.
  useEffect(() => {
    if (!editing) return
    const svgEl = editRef.current?.querySelector('svg')
    if (!svgEl) return
    setSel(null)
    const target = fill.toLowerCase()
    const bars = Array.from(svgEl.querySelectorAll<SVGElement>('path')).filter(
      (p) => fillOf(p) === target,
    )
    const handlers: Array<[SVGElement, (e: Event) => void]> = []
    let current: SVGElement | null = null
    for (const bar of bars) {
      bar.style.cursor = 'pointer'
      const onClick = (e: Event): void => {
        e.stopPropagation()
        if (current) current.style.outline = ''
        current = e.currentTarget as SVGElement
        current.style.outline = '2px dashed #222'
        setSel(current)
      }
      bar.addEventListener('click', onClick)
      handlers.push([bar, onClick])
    }
    return () => handlers.forEach(([b, h]) => b.removeEventListener('click', h))
  }, [editing, shown, fill])

  // Apply a colour: to the selected bar only if one is selected, else to all bars.
  const paint = (color: string): void => {
    if (sel) { setFillOf(sel, color); return }
    setFill(color)
  }

  return (
    <>
      <div
        className="out-chart"
        title="Click to enlarge · double-click to edit"
        onClick={() => setBig(true)}
        onDoubleClick={(e) => { e.stopPropagation(); setBig(false); setEditing(true) }}
        dangerouslySetInnerHTML={{ __html: shown }}
      />
      {big && !editing && (
        <div className="out-chart-lightbox" onClick={() => setBig(false)}>
          <div className="out-chart-lightbox-inner" dangerouslySetInnerHTML={{ __html: shown }} />
        </div>
      )}
      {editing && (
        <div className="out-chart-lightbox" onClick={() => setEditing(false)}>
          <div className="chart-editor" onClick={(e) => e.stopPropagation()}>
            <div className="chart-editor-head">Chart Editor</div>
            <div className="chart-editor-body">
              <div className="chart-editor-svg" ref={editRef} dangerouslySetInnerHTML={{ __html: shown }} />
              <div className="chart-editor-controls">
                <div className="chart-editor-hint">
                  {sel ? 'Editing selected bar' : 'Click a bar to edit just it'}
                </div>
                <label>{sel ? 'Selected bar colour' : 'Bar / fill colour'}
                  <input type="color" value={fill}
                    onChange={(e) => paint(e.target.value)} />
                </label>
                <div className="chart-editor-swatches">
                  {SWATCHES.map((c) => (
                    <button key={c} className="chart-editor-swatch" style={{ background: c }} title={c}
                      onClick={() => paint(c)} />
                  ))}
                </div>
                {sel && (
                  <button onClick={() => { sel.style.outline = ''; setSel(null) }}>Deselect</button>
                )}
                <label>Border colour (all bars)
                  <input type="color" value={edge} onChange={(e) => setEdge(e.target.value)} />
                </label>
                <button onClick={() => { setFill(DEFAULT_FILL); setEdge(DEFAULT_EDGE); setSel(null) }}>Reset colours</button>
                <button onClick={() => setEditing(false)}>Close</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

/**
 * Renders one output object. Switches on `type` with a fallback for unknown
 * types, so new object types slot in without touching plumbing (PHASE-0 §5).
 */
export function OutputItem({ obj }: { obj: OutputObject }): JSX.Element {
  switch (obj.type) {
    case 'Title':
      return <div className="out-title">{(obj as { text: string }).text}</div>
    case 'TextBlock':
      return <div className="out-text">{(obj as { text: string }).text}</div>
    case 'Warning':
      return <div className="out-warning">{(obj as { text: string }).text}</div>
    case 'Error':
      return <div className="out-error">{(obj as { text: string }).text}</div>
    case 'PivotTable':
      return <PivotTableView table={obj as unknown as PivotTableJson} />
    case 'Chart':
      return <ChartView svg={(obj as unknown as { svg: string }).svg} />
    default:
      return (
        <div className="out-unknown">
          [{obj.type}]
          {typeof (obj as { text?: string }).text === 'string' ? ` ${(obj as { text: string }).text}` : ''}
        </div>
      )
  }
}

export function OutputList({ items }: { items: OutputObject[] }): JSX.Element {
  return (
    <div className="out-list">
      {items.map((obj, i) => (
        <OutputItem key={i} obj={obj} />
      ))}
    </div>
  )
}

import { useState } from 'react'
import type { OutputObject } from '../../shared/types'
import { PivotTableView, type PivotTableJson } from '../output/PivotTable'
import './output.css'

// The default bar/fill and edge colours the sidecar draws with; the editor
// retints these in the SVG so the user can recolour bars/fills live.
const DEFAULT_FILL = '#4e79c4'
const DEFAULT_EDGE = '#2f4f8a'

function retint(svg: string, fill: string, edge: string): string {
  const rx = (hex: string): RegExp => new RegExp(hex.replace('#', '#?'), 'gi')
  return svg.replace(rx(DEFAULT_FILL), fill).replace(rx(DEFAULT_EDGE), edge)
}

// A chart: click to enlarge (lightbox), double-click to open the Chart Editor
// (recolour bars/fill).
function ChartView({ svg }: { svg: string }): JSX.Element {
  const [big, setBig] = useState(false)
  const [editing, setEditing] = useState(false)
  const [fill, setFill] = useState(DEFAULT_FILL)
  const [edge, setEdge] = useState(DEFAULT_EDGE)
  const shown = fill === DEFAULT_FILL && edge === DEFAULT_EDGE ? svg : retint(svg, fill, edge)
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
              <div className="chart-editor-svg" dangerouslySetInnerHTML={{ __html: shown }} />
              <div className="chart-editor-controls">
                <label>Bar / fill colour
                  <input type="color" value={fill} onChange={(e) => setFill(e.target.value)} />
                </label>
                <label>Border colour
                  <input type="color" value={edge} onChange={(e) => setEdge(e.target.value)} />
                </label>
                <button onClick={() => { setFill(DEFAULT_FILL); setEdge(DEFAULT_EDGE) }}>Reset colours</button>
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

import { useState } from 'react'
import type { OutputObject } from '../../shared/types'
import { PivotTableView, type PivotTableJson } from '../output/PivotTable'
import { ChartEditor } from './ChartEditor'
import { svgToPng } from './chartExport'
import './output.css'

// A chart: double-click to open the Chart Editor, where any bar or text can be
// selected and edited (as in SPSS).
function ChartView({ obj, onChange }: { obj: OutputObject; onChange?: (o: OutputObject) => void }): JSX.Element {
  const svg = (obj as unknown as { svg: string }).svg
  const [editing, setEditing] = useState(false)
  const apply = async (next: string): Promise<void> => {
    setEditing(false)
    const png = await svgToPng(next)
    // The original SPSS chart members no longer describe the edited chart.
    const edited: Record<string, unknown> = { ...(obj as unknown as Record<string, unknown>), svg: next }
    delete edited.spv
    if (png) edited.png = png
    onChange?.(edited as unknown as OutputObject)
  }
  return (
    <>
      <div
        className="out-chart"
        title="Double-click to edit"
        onDoubleClick={() => setEditing(true)}
        dangerouslySetInnerHTML={{ __html: svg }}
      />
      {editing && <ChartEditor svg={svg} onApply={(n) => void apply(n)} onCancel={() => setEditing(false)} />}
    </>
  )
}

/**
 * Renders one output object. Switches on `type` with a fallback for unknown
 * types, so new object types slot in without touching plumbing (PHASE-0 §5).
 */
export function OutputItem({ obj, onChange }: { obj: OutputObject; onChange?: (o: OutputObject) => void }): JSX.Element {
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
      return <ChartView obj={obj} onChange={onChange} />
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

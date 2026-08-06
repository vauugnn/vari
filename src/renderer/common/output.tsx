import type { OutputObject } from '../../shared/types'
import { PivotTableView, type PivotTableJson } from '../output/PivotTable'
import './output.css'

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
      return (
        <div
          className="out-chart"
          dangerouslySetInnerHTML={{ __html: (obj as unknown as { svg: string }).svg }}
        />
      )
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

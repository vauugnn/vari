import type { OutputObject } from '../../shared/types'
import './output.css'

/**
 * Renders one output object. Switches on `type` with a fallback for unknown
 * types, so later phases add PivotTable/Chart/Notes without touching plumbing
 * (PHASE-0 section 5).
 */
function OutputItem({ obj }: { obj: OutputObject }): JSX.Element {
  switch (obj.type) {
    case 'Title':
      return <div className="out-title">{obj.text}</div>
    case 'Error':
      return <div className="out-error">{obj.text}</div>
    default:
      return (
        <div className="out-unknown">
          [{obj.type}]{typeof obj.text === 'string' ? ` ${obj.text}` : ''}
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

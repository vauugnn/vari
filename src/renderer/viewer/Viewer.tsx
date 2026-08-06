import { useEffect, useState } from 'react'
import type { OutputObject } from '../../shared/types'
import { OutputList } from '../common/output'
import './viewer.css'

// Split pane: outline tree on the left (Phase 0 lists Title nodes), content on
// the right. Appends output objects streamed from main via output.append.
export function Viewer(): JSX.Element {
  const [items, setItems] = useState<OutputObject[]>([])

  useEffect(() => {
    return window.spss.onOutput((objects) => {
      setItems((prev) => [...prev, ...objects])
    })
  }, [])

  const outline = items
    .map((o, i) => ({ o, i }))
    .filter(({ o }) => o.type === 'Title')

  return (
    <div className="vw-root">
      <div className="vw-outline">
        <div className="vw-outline-head">Output</div>
        {outline.map(({ o, i }) => (
          <div key={i} className="vw-outline-item">
            {o.type === 'Title' ? o.text : ''}
          </div>
        ))}
      </div>
      <div className="vw-content">
        {items.length === 0 ? (
          <div className="vw-empty" />
        ) : (
          <OutputList items={items} />
        )}
      </div>
    </div>
  )
}

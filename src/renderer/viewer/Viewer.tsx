import { useEffect, useRef, useState } from 'react'
import type { OutputObject } from '../../shared/types'
import { OutputItem } from '../common/output'
import { documentHtml } from '../output/toHtml'
import './viewer.css'

interface OutlineEntry {
  index: number
  label: string
  kind: 'title' | 'table' | 'other'
}

function outlineOf(items: OutputObject[]): OutlineEntry[] {
  const out: OutlineEntry[] = []
  items.forEach((o, index) => {
    if (o.type === 'Title') out.push({ index, label: (o as { text: string }).text, kind: 'title' })
    else if (o.type === 'PivotTable') out.push({ index, label: (o as unknown as { title: string }).title, kind: 'table' })
  })
  return out
}

export function Viewer(): JSX.Element {
  const [items, setItems] = useState<OutputObject[]>([])
  const itemRefs = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    return window.spss.onOutput((objects) => setItems((prev) => [...prev, ...objects]))
  }, [])

  const outline = outlineOf(items)

  const exportHtml = async (): Promise<void> => {
    await window.spss.exportHtml(documentHtml(items))
  }

  return (
    <div className="vw-shell">
      <div className="vw-toolbar">
        <button onClick={exportHtml} disabled={items.length === 0}>
          Export HTML…
        </button>
        <button onClick={() => void window.spss.exportExcel(items)} disabled={items.length === 0}>
          Export Excel…
        </button>
        <button onClick={() => setItems([])} disabled={items.length === 0}>
          Clear
        </button>
      </div>
      <div className="vw-root">
        <div className="vw-outline">
          <div className="vw-outline-head">Output</div>
          {outline.map((e) => (
            <div
              key={e.index}
              className={'vw-outline-item vw-outline-item--' + e.kind}
              onClick={() => itemRefs.current[e.index]?.scrollIntoView({ block: 'start', behavior: 'smooth' })}
            >
              {e.label}
            </div>
          ))}
        </div>
        <div className="vw-content">
          {items.length === 0 ? (
            <div className="vw-empty" />
          ) : (
            items.map((obj, i) => (
              <div key={i} ref={(el) => (itemRefs.current[i] = el)}>
                <OutputItem obj={obj} />
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

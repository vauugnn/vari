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
  const [selected, setSelected] = useState<number | null>(null)
  // Titles whose following block is collapsed (folded), keyed by item index.
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set())
  const itemRefs = useRef<(HTMLDivElement | null)[]>([])

  useEffect(() => {
    return window.spss.onOutput((objects) => setItems((prev) => [...prev, ...objects]))
  }, [])

  const outline = outlineOf(items)

  const exportHtml = async (): Promise<void> => {
    await window.spss.exportHtml(documentHtml(items))
  }

  const deleteItem = (i: number): void => {
    setItems((prev) => prev.filter((_, idx) => idx !== i))
    setSelected(null)
  }

  const toggleCollapse = (i: number): void => {
    setCollapsed((prev) => {
      const n = new Set(prev)
      if (n.has(i)) n.delete(i)
      else n.add(i)
      return n
    })
  }

  // An item is hidden when it falls under a collapsed Title (up to the next Title).
  const hidden = (i: number): boolean => {
    for (let j = i - 1; j >= 0; j--) {
      if (items[j].type === 'Title') return collapsed.has(j)
    }
    return false
  }

  const select = (i: number): void => {
    setSelected(i)
    itemRefs.current[i]?.scrollIntoView({ block: 'start', behavior: 'smooth' })
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
        <button onClick={() => void window.spss.exportSpv(items)} disabled={items.length === 0}>
          Save Output…
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
              className={
                'vw-outline-item vw-outline-item--' + e.kind + (selected === e.index ? ' vw-outline-item--sel' : '')
              }
              onClick={() => select(e.index)}
            >
              {e.kind === 'title' && (
                <span
                  className="vw-caret"
                  onClick={(ev) => {
                    ev.stopPropagation()
                    toggleCollapse(e.index)
                  }}
                >
                  {collapsed.has(e.index) ? '▸' : '▾'}
                </span>
              )}
              {e.label}
            </div>
          ))}
        </div>
        <div className="vw-content">
          {items.length === 0 ? (
            <div className="vw-empty" />
          ) : (
            items.map((obj, i) =>
              hidden(i) ? null : (
                <div
                  key={i}
                  ref={(el) => (itemRefs.current[i] = el)}
                  className={'vw-item' + (selected === i ? ' vw-item--sel' : '')}
                  onClick={() => setSelected(i)}
                >
                  <button className="vw-item-del" title="Delete" onClick={(ev) => { ev.stopPropagation(); deleteItem(i) }}>
                    ×
                  </button>
                  {obj.type === 'Title' && (
                    <button className="vw-item-fold" title="Collapse/expand" onClick={(ev) => { ev.stopPropagation(); toggleCollapse(i) }}>
                      {collapsed.has(i) ? '▸' : '▾'}
                    </button>
                  )}
                  <OutputItem obj={obj} />
                </div>
              )
            )
          )}
        </div>
      </div>
    </div>
  )
}

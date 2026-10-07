import { useEffect, useRef, useState } from 'react'
import type { MenuHit } from '../../shared/types'
import './appsearch.css'

// The toolbar's "Search application" box: type part of a menu command's name, pick a result.
export function AppSearch(): JSX.Element {
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<MenuHit[]>([])
  const [active, setActive] = useState(0)
  const [open, setOpen] = useState(false)
  const box = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let alive = true
    void window.spss.searchMenu(query).then((h) => {
      if (alive) {
        setHits(h)
        setActive(0)
      }
    })
    return () => {
      alive = false
    }
  }, [query])

  useEffect(() => {
    const close = (e: MouseEvent): void => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const choose = (h: MenuHit): void => {
    setOpen(false)
    setQuery('')
    void window.spss.invokeMenu(h.indexPath)
  }

  return (
    <div className="as" ref={box}>
      <svg className="as-icon" width="14" height="14" viewBox="0 0 16 16" aria-hidden>
        <circle cx="6.5" cy="6.5" r="4.5" fill="none" stroke="#2f6fd0" strokeWidth="1.8" />
        <line x1="10" y1="10" x2="14.5" y2="14.5" stroke="#2f6fd0" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
      <input
        type="text"
        value={query}
        placeholder="Search application"
        onFocus={() => setOpen(true)}
        onChange={(e) => {
          setQuery(e.target.value)
          setOpen(true)
        }}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown') setActive((a) => Math.min(a + 1, hits.length - 1))
          else if (e.key === 'ArrowUp') setActive((a) => Math.max(a - 1, 0))
          else if (e.key === 'Enter' && hits[active]) choose(hits[active])
          else if (e.key === 'Escape') setOpen(false)
        }}
      />
      {open && query.trim() !== '' && (
        <div className="as-results">
          {hits.length === 0 ? (
            <div className="as-none">No matching commands</div>
          ) : (
            hits.map((h, i) => (
              <div key={h.indexPath.join('.')} className={'as-hit' + (i === active ? ' as-hit--on' : '')} onMouseEnter={() => setActive(i)} onClick={() => choose(h)}>
                <span className="as-label">{h.label}</span>
                <span className="as-path">{h.path}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}

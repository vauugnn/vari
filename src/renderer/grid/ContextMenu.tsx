import { useEffect } from 'react'
import './contextmenu.css'

export interface MenuItem {
  label?: string
  onClick?: () => void
  disabled?: boolean
  separator?: boolean
}

export function ContextMenu({
  x,
  y,
  items,
  onClose
}: {
  x: number
  y: number
  items: MenuItem[]
  onClose: () => void
}): JSX.Element {
  useEffect(() => {
    const close = () => onClose()
    window.addEventListener('mousedown', close)
    window.addEventListener('blur', close)
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', esc)
    return () => {
      window.removeEventListener('mousedown', close)
      window.removeEventListener('blur', close)
      window.removeEventListener('keydown', esc)
    }
  }, [onClose])

  return (
    <div className="ctx-menu" style={{ left: x, top: y }} onMouseDown={(e) => e.stopPropagation()}>
      {items.map((it, i) =>
        it.separator ? (
          <div key={i} className="ctx-sep" />
        ) : (
          <div
            key={i}
            className={'ctx-item' + (it.disabled ? ' ctx-item--disabled' : '')}
            onMouseDown={(e) => {
              e.stopPropagation()
              if (!it.disabled) {
                it.onClick?.()
                onClose()
              }
            }}
          >
            {it.label}
          </div>
        )
      )}
    </div>
  )
}

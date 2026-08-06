import type { ReactNode } from 'react'
import './modal.css'

export function Modal({
  title,
  children,
  onOk,
  onCancel,
  okDisabled
}: {
  title: string
  children: ReactNode
  onOk: () => void
  onCancel: () => void
  okDisabled?: boolean
}): JSX.Element {
  return (
    <div className="modal-overlay" onMouseDown={onCancel}>
      <div className="modal" onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-title">{title}</div>
        <div className="modal-body">{children}</div>
        <div className="modal-footer">
          <button onClick={onOk} disabled={okDisabled}>
            OK
          </button>
          <button onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </div>
  )
}

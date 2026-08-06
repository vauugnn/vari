import type { ReactNode } from 'react'
import './analysis.css'

// The dialog frame shared by Analyze dialogs (HLD 5.3): body on the left, a
// column of sub-dialog buttons on the right, and the OK/Paste/Reset/Cancel row.
export function AnalysisFrame({
  title,
  children,
  subButtons,
  onOk,
  onPaste,
  onReset,
  onCancel,
  okDisabled
}: {
  title: string
  children: ReactNode
  subButtons?: { label: string; onClick: () => void }[]
  onOk: () => void
  onPaste: () => void
  onReset: () => void
  onCancel: () => void
  okDisabled?: boolean
}): JSX.Element {
  return (
    <div className="modal-overlay" onMouseDown={onCancel}>
      <div className="af" onMouseDown={(e) => e.stopPropagation()}>
        <div className="af-title">{title}</div>
        <div className="af-main">
          <div className="af-body">{children}</div>
          {subButtons && subButtons.length > 0 && (
            <div className="af-subs">
              {subButtons.map((b) => (
                <button key={b.label} onClick={b.onClick}>
                  {b.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="af-footer">
          <button onClick={onOk} disabled={okDisabled}>
            OK
          </button>
          <button onClick={onPaste} disabled={okDisabled}>
            Paste
          </button>
          <button onClick={onReset}>Reset</button>
          <button onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </div>
  )
}

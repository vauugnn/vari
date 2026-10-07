import type { ReactNode } from 'react'
import './toolbar.css'

// One icon button on a toolbar, with a hover tooltip (works over disabled buttons too).
export function TB({
  title,
  onClick,
  active,
  disabled,
  children
}: {
  title: string
  onClick?: () => void
  active?: boolean
  disabled?: boolean
  children: ReactNode
}): JSX.Element {
  return (
    <span className="tt" data-tip={title}>
      <button className={'icon-btn' + (active ? ' icon-btn--on' : '')} disabled={disabled} onClick={onClick}>
        {children}
      </button>
    </span>
  )
}

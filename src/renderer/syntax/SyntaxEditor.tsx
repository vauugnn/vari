import { useEffect, useState } from 'react'
import type { SidecarStatus } from '../../shared/types'
import './syntax.css'

// Plain textarea + Run button. Run disabled until the sidecar answers ping().
// Executed text routes renderer -> main -> sidecar; output lands in the Viewer.
export function SyntaxEditor(): JSX.Element {
  const [text, setText] = useState("TITLE 'hello'.")
  const [status, setStatus] = useState<SidecarStatus>({ state: 'starting' })
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    void window.spss.getSidecarStatus().then(setStatus)
    return window.spss.onSidecarStatus(setStatus)
  }, [])

  const ready = status.state === 'ready'

  async function run(): Promise<void> {
    if (!ready || busy) return
    setBusy(true)
    try {
      await window.spss.execute(text)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="sx-root">
      <div className="sx-toolbar">
        <button onClick={run} disabled={!ready || busy} title="Run all">
          ▶ Run
        </button>
        <span className="sx-status">
          {status.state === 'ready'
            ? 'Processor ready'
            : status.state === 'down'
              ? `Processor unavailable${status.detail ? ` — ${status.detail}` : ''}`
              : 'Starting processor…'}
        </span>
      </div>
      <textarea
        className="sx-editor"
        spellCheck={false}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
    </div>
  )
}

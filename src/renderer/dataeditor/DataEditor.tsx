import { useEffect, useState } from 'react'
import type { SidecarStatus } from '../../shared/types'
import './dataeditor.css'

// Phase 0: no grid, no data model. Empty body with correctly positioned and
// styled Data View / Variable View tabs at bottom left, plus a status bar.
type Tab = 'data' | 'variable'

export function DataEditor(): JSX.Element {
  const [tab, setTab] = useState<Tab>('data')
  const [status, setStatus] = useState<SidecarStatus>({ state: 'starting' })

  useEffect(() => {
    void window.spss.getSidecarStatus().then(setStatus)
    return window.spss.onSidecarStatus(setStatus)
  }, [])

  return (
    <div className="de-root">
      <div className="de-toolbar" />
      <div className="de-body">
        {/* empty grid area (Phase 1) */}
      </div>
      <div className="de-tabs">
        <button
          className={tab === 'data' ? 'de-tab de-tab--active' : 'de-tab'}
          onClick={() => setTab('data')}
        >
          Data View
        </button>
        <button
          className={tab === 'variable' ? 'de-tab de-tab--active' : 'de-tab'}
          onClick={() => setTab('variable')}
        >
          Variable View
        </button>
      </div>
      <div className="statusbar">
        IBM SPSS Statistics Processor is {status.state === 'ready' ? 'ready' : status.state === 'down' ? 'unavailable' : 'starting'}
      </div>
    </div>
  )
}

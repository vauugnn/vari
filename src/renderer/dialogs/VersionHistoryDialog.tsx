import { useCallback, useEffect, useMemo, useState } from 'react'
import type { HistoryDiff, HistoryVersion } from '../../shared/types'
import './history.css'

const KIND_LABEL: Record<HistoryVersion['kind'], string> = {
  auto: 'Autosave',
  save: 'Saved',
  manual: 'Saved version',
  'pre-op': 'Before a change',
  restore: 'Before a restore',
  open: 'Opened'
}

const fmtTime = (t: number): string => new Date(t * 1000).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })

function dayLabel(t: number): string {
  const d = new Date(t * 1000)
  const today = new Date()
  const diffDays = Math.round((new Date(today.toDateString()).getTime() - new Date(d.toDateString()).getTime()) / 86400000)
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  return d.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric', year: d.getFullYear() === today.getFullYear() ? undefined : 'numeric' })
}

const show = (v: unknown): string => (v === null || v === undefined || v === '' ? 'blank' : String(v))
const plural = (n: number, one: string, many = one + 's'): string => `${n.toLocaleString()} ${n === 1 ? one : many}`

// A diff in sentences, most important first.
export function describeDiff(d: HistoryDiff): string[] {
  if (d.identical) return ['No differences.']
  const out: string[] = []
  if (d.rows.from !== d.rows.to) out.push(`Cases: ${d.rows.from.toLocaleString()} → ${d.rows.to.toLocaleString()}`)
  if (d.variables.added.length) out.push(`Added ${plural(d.variables.added.length, 'variable')}: ${d.variables.added.join(', ')}`)
  if (d.variables.removed.length) out.push(`Removed ${plural(d.variables.removed.length, 'variable')}: ${d.variables.removed.join(', ')}`)
  for (const c of d.variables.changed.slice(0, 12)) {
    const detail = typeof c.from === 'number' && typeof c.to === 'number' ? '' : `: ${show(c.from)} → ${show(c.to)}`
    out.push(`${c.variable}: ${c.field} changed${detail}`)
  }
  if (d.variables.changed.length > 12) out.push(`…and ${d.variables.changed.length - 12} more variable changes`)
  if (d.cells.changed) {
    out.push(`${plural(d.cells.changed, 'cell')} changed`)
    for (const e of d.cells.examples) out.push(`   Case ${e.case}, ${e.variable}: ${show(e.from)} → ${show(e.to)}`)
  }
  if (d.outputItems.from !== d.outputItems.to) out.push(`Output items: ${d.outputItems.from} → ${d.outputItems.to}`)
  if (d.syntaxDiff.length) out.push('Syntax changed (see below)')
  return out
}

export function VersionHistoryDialog({ onClose }: { onClose: () => void }): JSX.Element {
  const [versions, setVersions] = useState<HistoryVersion[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [against, setAgainst] = useState<'previous' | 'now'>('previous')
  const [diff, setDiff] = useState<HistoryDiff | null>(null)
  const [naming, setNaming] = useState<string | null>(null)
  const [confirmRestore, setConfirmRestore] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const reload = useCallback(async (keep?: string) => {
    try {
      const out = await window.spss.history.list()
      setVersions(out.versions)
      setSelected((cur) => keep ?? (cur && out.versions.some((v) => v.id === cur) ? cur : out.versions[0]?.id ?? null))
      setError('')
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  const index = versions.findIndex((v) => v.id === selected)
  const current = index >= 0 ? versions[index] : null
  const previous = index >= 0 ? versions[index + 1] : undefined // the list is newest first

  // Changes for the selected version, either since the version before it or against now.
  useEffect(() => {
    setDiff(null)
    setConfirmRestore(false)
    setNaming(null)
    if (!current) return
    let alive = true
    const run = async (): Promise<void> => {
      try {
        if (against === 'now') setDiff(await window.spss.history.diff(current.id))
        else if (previous) setDiff(await window.spss.history.diff(previous.id, current.id))
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : String(e))
      }
    }
    void run()
    return () => {
      alive = false
    }
  }, [current?.id, previous?.id, against]) // eslint-disable-line react-hooks/exhaustive-deps

  const groups = useMemo(() => {
    const out: { label: string; items: HistoryVersion[] }[] = []
    for (const v of versions) {
      const label = dayLabel(v.time)
      const last = out[out.length - 1]
      if (last && last.label === label) last.items.push(v)
      else out.push({ label, items: [v] })
    }
    return out
  }, [versions])

  const act = async (fn: () => Promise<unknown>, keep?: string): Promise<void> => {
    setBusy(true)
    try {
      await fn()
      await reload(keep)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-overlay" onMouseDown={onClose}>
      <div className="vh" onMouseDown={(e) => e.stopPropagation()}>
        <div className="vh-title">
          Version History
          <button className="vh-close" title="Close" onClick={onClose}>×</button>
        </div>
        <div className="vh-body">
          <div className="vh-list">
            <div className="vh-listhead">
              <button
                disabled={busy}
                onClick={() => void act(async () => {
                  const v = await window.spss.history.create()
                  if (v) setSelected(v.id)
                }, undefined)}
              >
                Save version now
              </button>
            </div>
            {versions.length === 0 && <div className="vh-empty">No versions yet. Vari saves one automatically every few minutes when something changes.</div>}
            {groups.map((g) => (
              <div key={g.label}>
                <div className="vh-day">{g.label}</div>
                {g.items.map((v) => (
                  <div key={v.id} className={'vh-item' + (v.id === selected ? ' vh-item--sel' : '')} onClick={() => setSelected(v.id)}>
                    <div className="vh-item-top">
                      <span className={'vh-name' + (v.name ? ' vh-name--named' : '')}>{v.name || KIND_LABEL[v.kind]}</span>
                      <span className="vh-time">{fmtTime(v.time)}</span>
                    </div>
                    <div className="vh-item-sub">
                      {v.name ? `${KIND_LABEL[v.kind]} · ` : ''}
                      {v.rows.toLocaleString()} cases · {plural(v.vars, 'variable')}
                    </div>
                  </div>
                ))}
              </div>
            ))}
          </div>
          <div className="vh-detail">
            {error && <div className="vh-error">{error}</div>}
            {current ? (
              <>
                <div className="vh-dhead">
                  {naming === null ? (
                    <>
                      <div className="vh-dtitle">{current.name || KIND_LABEL[current.kind]}</div>
                      <button onClick={() => setNaming(current.name)} disabled={busy}>Name this version…</button>
                    </>
                  ) : (
                    <>
                      <input
                        autoFocus
                        type="text"
                        value={naming}
                        placeholder="e.g. Before cleaning"
                        onChange={(e) => setNaming(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') void act(() => window.spss.history.rename(current.id, naming), current.id)
                          if (e.key === 'Escape') setNaming(null)
                        }}
                      />
                      <button disabled={busy} onClick={() => void act(() => window.spss.history.rename(current.id, naming), current.id)}>Save name</button>
                      <button onClick={() => setNaming(null)}>Cancel</button>
                    </>
                  )}
                </div>
                <div className="vh-dmeta">
                  {new Date(current.time * 1000).toLocaleString()} · {KIND_LABEL[current.kind]} · {current.rows.toLocaleString()} cases,{' '}
                  {plural(current.vars, 'variable')}, {plural(current.outputItems, 'output item')} · {(current.bytes / 1024).toFixed(0)} KB
                </div>
                <div className="vh-compare">
                  Changes
                  <label>
                    <input type="radio" checked={against === 'previous'} onChange={() => setAgainst('previous')} /> since the version before
                  </label>
                  <label>
                    <input type="radio" checked={against === 'now'} onChange={() => setAgainst('now')} /> compared with now
                  </label>
                </div>
                <div className="vh-changes">
                  {against === 'previous' && !previous ? (
                    <div className="vh-muted">This is the oldest version.</div>
                  ) : diff ? (
                    <>
                      {describeDiff(diff).map((line, i) => (
                        <div key={i} className="vh-line">{line}</div>
                      ))}
                      {diff.syntaxDiff.length > 0 && (
                        <pre className="vh-syntax">
                          {diff.syntaxDiff.map((l, i) => (
                            <div key={i} className={l.startsWith('+') && !l.startsWith('+++') ? 'vh-add' : l.startsWith('-') && !l.startsWith('---') ? 'vh-del' : ''}>
                              {l}
                            </div>
                          ))}
                        </pre>
                      )}
                    </>
                  ) : (
                    <div className="vh-muted">Comparing…</div>
                  )}
                </div>
                <div className="vh-actions">
                  {confirmRestore ? (
                    <>
                      <span className="vh-warn">Restore this version? Your current work is saved as a version first, so nothing is lost.</span>
                      <button
                        disabled={busy}
                        onClick={() => void act(async () => {
                          await window.spss.history.restore(current.id)
                          onClose()
                        })}
                      >
                        Restore
                      </button>
                      <button onClick={() => setConfirmRestore(false)}>Cancel</button>
                    </>
                  ) : (
                    <>
                      <button disabled={busy} onClick={() => setConfirmRestore(true)}>Restore this version</button>
                      <button
                        disabled={busy || current.kind === 'open'}
                        title={current.kind === 'open' ? 'The original is kept' : 'Delete this version'}
                        onClick={() => void act(() => window.spss.history.remove(current.id))}
                      >
                        Delete
                      </button>
                    </>
                  )}
                </div>
              </>
            ) : (
              <div className="vh-muted">Select a version to see what changed.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

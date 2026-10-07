import { useState } from 'react'
import { NODES, ROOT, type Result } from './testChooser'
import './chooser.css'

interface Step {
  node: string
  answer?: string
}

export function TestChooserDialog({ onClose, onOpen }: { onClose: () => void; onOpen: (dialogId: string) => void }): JSX.Element {
  // The path of answers so far; the last step is the node being shown.
  const [path, setPath] = useState<Step[]>([{ node: ROOT }])
  const here = path[path.length - 1]
  const node = NODES[here.node]

  const choose = (label: string, next: string): void =>
    setPath((p) => [...p.slice(0, -1), { ...p[p.length - 1], answer: label }, { node: next }])
  const back = (): void => setPath((p) => (p.length > 1 ? p.slice(0, -1).map((s, i, a) => (i === a.length - 1 ? { node: s.node } : s)) : p))

  const result = node.kind === 'result' ? (node as Result) : null

  return (
    <div className="modal-overlay" onMouseDown={onClose}>
      <div className="tc" onMouseDown={(e) => e.stopPropagation()}>
        <div className="tc-title">Which test should I use?</div>
        <div className="tc-body">
          {path.length > 1 && (
            <div className="tc-trail">
              {path.slice(0, -1).map((s, i, a) => (
                <span key={i} className="tc-crumb">
                  {s.answer}
                  {i < a.length - 1 && <span className="tc-sep"> › </span>}
                </span>
              ))}
            </div>
          )}
          {node.kind === 'question' ? (
            <>
              <div className="tc-q">{node.text}</div>
              {node.options.map((o) => (
                <button key={o.label} className="tc-opt" onClick={() => choose(o.label, o.next)}>
                  <span className="tc-opt-label">{o.label}</span>
                  {o.hint && <span className="tc-opt-hint">{o.hint}</span>}
                </button>
              ))}
            </>
          ) : (
            result && (
              <div className="tc-result">
                <div className="tc-rtitle">{result.title}</div>
                <p className="tc-why">{result.why}</p>
                <div className="tc-h">Check before you run it</div>
                <ul>
                  {result.check.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
                <div className="tc-h">In your write-up</div>
                <p>{result.report}</p>
                {result.fallback && (
                  <button className="tc-fallback" onClick={() => choose(result.fallback!.label, result.fallback!.next)}>
                    If this applies: “{result.fallback.label}” → see {NODES[result.fallback.next].kind === 'result' ? (NODES[result.fallback.next] as Result).title : 'next step'}
                  </button>
                )}
              </div>
            )
          )}
        </div>
        <div className="tc-footer">
          <button onClick={back} disabled={path.length === 1}>Back</button>
          <button onClick={() => setPath([{ node: ROOT }])} disabled={path.length === 1}>Start over</button>
          <span style={{ flex: 1 }} />
          <button onClick={onClose}>Close</button>
          {result && (
            <button
              onClick={() => {
                onClose()
                onOpen(result.dialog)
              }}
            >
              Open {result.dialogLabel}…
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

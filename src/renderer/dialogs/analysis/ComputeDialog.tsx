import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { MeasureIcon } from '../../common/icons'

// Transform ▸ Compute Variable. Emits `COMPUTE target = expression.`
export function ComputeDialog({
  variables,
  onClose
}: {
  variables: VariableMetaJson[]
  onClose: () => void
}): JSX.Element {
  const [target, setTarget] = useState('')
  const [expr, setExpr] = useState('')

  const syntax = (): string => `COMPUTE ${target} = ${expr}.`
  const ok = () => {
    void window.spss.execute(syntax())
    onClose()
  }
  const insert = (name: string) => setExpr((e) => (e ? e + ' ' + name : name))

  return (
    <AnalysisFrame
      title="Compute Variable"
      onOk={ok}
      onPaste={() => {
        window.spss.paste(syntax())
        onClose()
      }}
      onReset={() => {
        setTarget('')
        setExpr('')
      }}
      onCancel={onClose}
      okDisabled={!target.trim() || !expr.trim()}
    >
      <div style={{ display: 'flex', gap: 12 }}>
        <div style={{ flex: 1 }}>
          <div className="field-row">
            <span>Target Variable:</span>
            <input type="text" value={target} onChange={(e) => setTarget(e.target.value)} style={{ width: 140 }} />
          </div>
          <div style={{ marginTop: 4 }}>Numeric Expression:</div>
          <textarea
            value={expr}
            onChange={(e) => setExpr(e.target.value)}
            spellCheck={false}
            style={{ width: '100%', height: 90, fontFamily: 'Menlo, monospace', fontSize: 12, resize: 'none' }}
          />
          <div style={{ marginTop: 4, display: 'flex', flexWrap: 'wrap', gap: 3 }}>
            {['+', '-', '*', '/', '**', '(', ')', '>', '<', '>=', '<=', '=', '~=', 'AND', 'OR', 'NOT'].map((op) => (
              <button key={op} style={{ minWidth: 30, padding: '1px 6px' }} onClick={() => insert(op)}>
                {op}
              </button>
            ))}
          </div>
        </div>
        <div style={{ width: 150 }}>
          <div>Variables:</div>
          <div className="vm-list" style={{ height: 150 }}>
            {variables.map((v) => (
              <div key={v.name} className="vm-item" onDoubleClick={() => insert(v.name)}>
                <MeasureIcon measure={v.measure} isString={v.isString} isDate={v.type === 'Date'} size={14} />
                <span className="vm-name">{v.name}</span>
              </div>
            ))}
          </div>
          <div style={{ fontSize: 11, color: '#666', marginTop: 3 }}>Double-click to insert. Functions: MEAN.n, SUM, SQRT, LN, ABS, RND…</div>
        </div>
      </div>
    </AnalysisFrame>
  )
}

import { useEffect, useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

type Props = { variables: VariableMetaJson[]; onClose: () => void }
const num = (v: VariableMetaJson) => !v.isString

// A single builder covering the legacy chart gallery. Each type declares which
// roles it needs; the dialog shows those slots and emits GRAPH syntax that the
// sidecar renders (matplotlib -> SVG). Not a drag canvas, but the same result.
type Role = 'x' | 'y' | 'group' | 'series'
type ChartType = {
  key: string
  label: string
  roles: Role[]
  syntax: (r: Record<Role, string[]>) => string
}

const TYPES: ChartType[] = [
  { key: 'bar', label: 'Bar', roles: ['x'], syntax: (r) => `GRAPH\n  /BAR(SIMPLE)=COUNT BY ${r.x[0]}.` },
  { key: 'bar3d', label: '3-D Bar', roles: ['x', 'group'], syntax: (r) => `GRAPH\n  /BAR3D=${r.x[0]} BY ${r.group[0]}.` },
  { key: 'line', label: 'Line', roles: ['y', 'x'], syntax: (r) => `GRAPH\n  /LINE(SIMPLE)=MEAN(${r.y[0]}) BY ${r.x[0]}.` },
  { key: 'area', label: 'Area', roles: ['y', 'x'], syntax: (r) => `GRAPH\n  /AREA(SIMPLE)=MEAN(${r.y[0]}) BY ${r.x[0]}.` },
  { key: 'pie', label: 'Pie', roles: ['x'], syntax: (r) => `GRAPH\n  /PIE=COUNT BY ${r.x[0]}.` },
  { key: 'hist', label: 'Histogram', roles: ['x'], syntax: (r) => `GRAPH\n  /HISTOGRAM=${r.x[0]}.` },
  { key: 'scatter', label: 'Scatter', roles: ['y', 'x'], syntax: (r) => `GRAPH\n  /SCATTERPLOT(BIVAR)=${r.x[0]} WITH ${r.y[0]}.` },
  { key: 'box', label: 'Boxplot', roles: ['y', 'group'], syntax: (r) => `GRAPH\n  /BOXPLOT=${r.y[0]}${r.group[0] ? ' BY ' + r.group[0] : ''}.` },
  { key: 'errorbar', label: 'Error Bar', roles: ['y', 'x'], syntax: (r) => `GRAPH\n  /ERRORBAR(CI 95)=MEAN(${r.y[0]}) BY ${r.x[0]}.` },
  { key: 'hilo', label: 'High-Low', roles: ['series'], syntax: (r) => `GRAPH\n  /HILO=${r.series.join(' ')}.` },
  { key: 'pyramid', label: 'Population Pyramid', roles: ['x', 'group'], syntax: (r) => `GRAPH\n  /PYRAMID=${r.x[0]} BY ${r.group[0]}.` }
]

const ROLE_LABEL: Record<Role, string> = { x: 'X-Axis / Category', y: 'Y-Axis / Measure', group: 'Grouping', series: 'Series (High Low [Close])' }

export function ChartBuilderDialog({ variables, onClose }: Props): JSX.Element {
  const [typeKey, setTypeKey] = useState('bar')
  const [roles, setRoles] = useState<Record<Role, string[]>>({ x: [], y: [], group: [], series: [] })
  const [preview, setPreview] = useState<string>('')
  const [previewing, setPreviewing] = useState(false)
  const type = TYPES.find((t) => t.key === typeKey)!

  const setRole = (role: Role, v: string[]) => setRoles((r) => ({ ...r, [role]: v }))
  const ready = type.roles.every((role) => (role === 'group' ? true : roles[role].length > 0))
  const s = () => type.syntax(roles)

  // Live canvas: whenever the chart spec is complete, render a preview off to
  // the side without committing it to the Viewer (debounced).
  useEffect(() => {
    if (!ready) {
      setPreview('')
      return
    }
    let alive = true
    setPreviewing(true)
    const handle = setTimeout(() => {
      void window.spss.preview(s()).then((objs) => {
        if (!alive) return
        const chart = objs.find((o) => o.type === 'Chart') as unknown as { svg?: string } | undefined
        setPreview(chart?.svg ?? '')
        setPreviewing(false)
      })
    }, 250)
    return () => {
      alive = false
      clearTimeout(handle)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [typeKey, JSON.stringify(roles)])

  return (
    <AnalysisFrame
      title="Chart Builder"
      onOk={() => { void window.spss.execute(s()); onClose() }}
      onPaste={() => { window.spss.paste(s()); onClose() }}
      onReset={() => setRoles({ x: [], y: [], group: [], series: [] })}
      onCancel={onClose}
      okDisabled={!ready}
    >
      <div style={{ display: 'flex', gap: 12 }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, width: 150, alignContent: 'flex-start' }}>
          {TYPES.map((t) => (
            <button
              key={t.key}
              onClick={() => { setTypeKey(t.key); setRoles({ x: [], y: [], group: [], series: [] }) }}
              style={{
                width: 68, height: 34, fontSize: 11,
                background: t.key === typeKey ? '#cbdcf0' : '#f0f0f0',
                border: '1px solid ' + (t.key === typeKey ? '#5b9bd5' : '#bbb')
              }}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div style={{ flex: 1, minWidth: 240 }}>
          {type.roles.map((role) => (
            <div key={role} style={{ marginBottom: 8 }}>
              <VarMover
                variables={variables}
                value={roles[role]}
                onChange={(v) => setRole(role, role === 'series' ? v : v.slice(-1))}
                label={ROLE_LABEL[role] + (role === 'group' ? ' (optional):' : ':')}
                accept={role === 'y' || role === 'series' ? num : undefined}
              />
            </div>
          ))}
        </div>
        <div className="cb-canvas">
          <div className="cb-canvas-head">Preview</div>
          {preview ? (
            <div className="cb-canvas-svg" dangerouslySetInnerHTML={{ __html: preview }} />
          ) : (
            <div className="cb-canvas-empty">{previewing ? 'Rendering…' : 'Assign variables to preview the chart.'}</div>
          )}
        </div>
      </div>
    </AnalysisFrame>
  )
}

import { useEffect, useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import './chartbuilder.css'

type Props = { variables: VariableMetaJson[]; onClose: () => void }
type Role = 'x' | 'y' | 'group' | 'series'

// A gallery entry: which roles it needs, whether a Statistic/error-bars apply,
// and how it turns roles + options into GRAPH syntax.
type Spec = {
  key: string
  group: string
  label: string
  roles: Role[]
  stat: boolean
  errbar: boolean
  syntax: (r: Record<Role, string[]>, stat: string, err: boolean) => string
}

const measure = (stat: string, y: string): string =>
  stat === 'COUNT' ? 'COUNT' : `${stat}(${y})`

const SPECS: Spec[] = [
  { key: 'bar', group: 'Bar', label: 'Simple Bar', roles: ['x', 'y'], stat: true, errbar: true,
    syntax: (r, s, e) => e
      ? `GRAPH\n  /ERRORBAR(CI 95)=MEAN(${r.y[0]}) BY ${r.x[0]}.`
      : `GRAPH\n  /BAR(SIMPLE)=${measure(s, r.y[0])} BY ${r.x[0]}.` },
  { key: 'bar3d', group: 'Bar', label: '3-D Bar', roles: ['x', 'group'], stat: false, errbar: false,
    syntax: (r) => `GRAPH\n  /BAR3D=${r.x[0]} BY ${r.group[0]}.` },
  { key: 'line', group: 'Line', label: 'Simple Line', roles: ['x', 'y'], stat: true, errbar: false,
    syntax: (r, s) => `GRAPH\n  /LINE(SIMPLE)=${measure(s, r.y[0])} BY ${r.x[0]}.` },
  { key: 'area', group: 'Area', label: 'Simple Area', roles: ['x', 'y'], stat: true, errbar: false,
    syntax: (r, s) => `GRAPH\n  /AREA(SIMPLE)=${measure(s, r.y[0])} BY ${r.x[0]}.` },
  { key: 'pie', group: 'Pie/Polar', label: 'Pie', roles: ['x'], stat: false, errbar: false,
    syntax: (r) => `GRAPH\n  /PIE=COUNT BY ${r.x[0]}.` },
  { key: 'scatter', group: 'Scatter/Dot', label: 'Simple Scatter', roles: ['y', 'x'], stat: false, errbar: false,
    syntax: (r) => `GRAPH\n  /SCATTERPLOT(BIVAR)=${r.x[0]} WITH ${r.y[0]}.` },
  { key: 'hist', group: 'Histogram', label: 'Histogram', roles: ['x'], stat: false, errbar: false,
    syntax: (r) => `GRAPH\n  /HISTOGRAM=${r.x[0]}.` },
  { key: 'hilo', group: 'High-Low', label: 'High-Low', roles: ['series'], stat: false, errbar: false,
    syntax: (r) => `GRAPH\n  /HILO=${r.series.join(' ')}.` },
  { key: 'box', group: 'Boxplot', label: 'Simple Boxplot', roles: ['y', 'group'], stat: false, errbar: false,
    syntax: (r) => `GRAPH\n  /BOXPLOT=${r.y[0]}${r.group[0] ? ' BY ' + r.group[0] : ''}.` },
  { key: 'errorbar', group: 'Bar', label: 'Simple Error Bar', roles: ['x', 'y'], stat: false, errbar: false,
    syntax: (r) => `GRAPH\n  /ERRORBAR(CI 95)=MEAN(${r.y[0]}) BY ${r.x[0]}.` },
  { key: 'pyramid', group: 'Bar', label: 'Population Pyramid', roles: ['x', 'group'], stat: false, errbar: false,
    syntax: (r) => `GRAPH\n  /PYRAMID=${r.x[0]} BY ${r.group[0]}.` }
]

const GROUPS = ['Bar', 'Line', 'Area', 'Pie/Polar', 'Scatter/Dot', 'Histogram', 'High-Low', 'Boxplot']
const ROLE_LABEL: Record<Role, string> = { x: 'X-Axis', y: 'Y-Axis', group: 'Cluster / Group', series: 'Series' }

export function ChartBuilderDialog({ variables, onClose }: Props): JSX.Element {
  const [group, setGroup] = useState('Bar')
  const [specKey, setSpecKey] = useState('bar')
  const [roles, setRoles] = useState<Record<Role, string[]>>({ x: [], y: [], group: [], series: [] })
  const [stat, setStat] = useState('COUNT')
  const [errbar, setErrbar] = useState(false)
  const [preview, setPreview] = useState('')
  const [previewing, setPreviewing] = useState(false)

  const spec = SPECS.find((s) => s.key === specKey)!
  const galleryItems = SPECS.filter((s) => s.group === group)
  const setRole = (role: Role, v: string[]) => setRoles((r) => ({ ...r, [role]: v }))
  const ready = spec.roles.every((role) => (role === 'group' ? true : roles[role].length > 0)) &&
    (!stat || stat === 'COUNT' || roles.y.length > 0)
  const s = () => spec.syntax(roles, stat, errbar)

  useEffect(() => {
    if (!ready) { setPreview(''); return }
    let alive = true
    setPreviewing(true)
    const h = setTimeout(() => {
      void window.spss.preview(s()).then((objs) => {
        if (!alive) return
        const chart = objs.find((o) => o.type === 'Chart') as unknown as { svg?: string } | undefined
        setPreview(chart?.svg ?? '')
        setPreviewing(false)
      })
    }, 250)
    return () => { alive = false; clearTimeout(h) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [specKey, JSON.stringify(roles), stat, errbar])

  const pick = (key: string) => {
    setSpecKey(key)
    setRoles({ x: [], y: [], group: [], series: [] })
    setErrbar(false)
    setStat('COUNT')
  }

  return (
    <AnalysisFrame
      title="Chart Builder"
      onOk={() => { void window.spss.execute(s()); onClose() }}
      onPaste={() => { window.spss.paste(s()); onClose() }}
      onReset={() => setRoles({ x: [], y: [], group: [], series: [] })}
      onCancel={onClose}
      okDisabled={!ready}
    >
      <div className="cb2">
        {/* Variables palette */}
        <div className="cb2-vars">
          <div className="cb2-head">Variables</div>
          <div className="cb2-varlist">
            {variables.map((v) => (
              <div key={v.name} className="cb-chip" draggable title={v.label || v.name}
                onDragStart={(e) => e.dataTransfer.setData('text/plain', v.name)}>
                {v.label ? v.label : v.name}
              </div>
            ))}
          </div>
        </div>

        {/* Canvas: live preview + drop zones */}
        <div className="cb2-canvas">
          <div className="cb2-canvas-title">Chart preview</div>
          <div className="cb2-preview">
            {preview ? <div dangerouslySetInnerHTML={{ __html: preview }} /> : <div className="cb2-empty">{previewing ? 'Rendering…' : 'Drop variables onto the axes.'}</div>}
          </div>
          <div className="cb2-zones">
            {spec.roles.map((role) => (
              <div key={role} className="cb2-zone"
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => {
                  e.preventDefault()
                  const nm = e.dataTransfer.getData('text/plain')
                  if (!nm) return
                  if ((role === 'y' || role === 'series') && variables.find((v) => v.name === nm)?.isString) return
                  setRole(role, role === 'series' ? [...roles.series, nm] : [nm])
                }}>
                <span className="cb2-zone-label">{ROLE_LABEL[role]}{role === 'group' ? ' (opt)' : ''}?</span>
                <span className="cb2-zone-vals">
                  {roles[role].length
                    ? roles[role].map((nm) => <span key={nm} className="cb-chip cb-chip--placed" onClick={() => setRole(role, roles[role].filter((x) => x !== nm))}>{nm} ×</span>)
                    : <span className="cb2-zone-hint">drop here</span>}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Element Properties */}
        <div className="cb2-props">
          <div className="cb2-head">Element Properties</div>
          {spec.stat && (
            <label className="cb2-field">Statistic
              <select value={stat} onChange={(e) => setStat(e.target.value)} disabled={errbar}>
                <option value="COUNT">Count</option>
                <option value="MEAN">Mean</option>
                <option value="SUM">Sum</option>
                <option value="PCT">Percentage</option>
              </select>
            </label>
          )}
          {spec.errbar && (
            <label className="cb2-check">
              <input type="checkbox" checked={errbar} onChange={(e) => setErrbar(e.target.checked)} /> Display error bars (95% CI)
            </label>
          )}
          {!spec.stat && !spec.errbar && <div className="cb2-note">No element options for this chart type.</div>}
        </div>
      </div>

      {/* Gallery */}
      <div className="cb2-gallery">
        <div className="cb2-gallery-groups">
          {GROUPS.map((g) => (
            <div key={g} className={'cb2-gname' + (g === group ? ' cb2-gname--sel' : '')}
              onClick={() => { setGroup(g); const first = SPECS.find((s2) => s2.group === g); if (first) pick(first.key) }}>
              {g}
            </div>
          ))}
        </div>
        <div className="cb2-gallery-items">
          {galleryItems.map((it) => (
            <button key={it.key} className={'cb2-gitem' + (it.key === specKey ? ' cb2-gitem--sel' : '')} onClick={() => pick(it.key)}>
              {it.label}
            </button>
          ))}
        </div>
      </div>
    </AnalysisFrame>
  )
}

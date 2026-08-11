import { useEffect, useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { MeasureIcon } from '../../common/icons'
import './chartbuilder.css'

// Small original chart-type glyphs for the gallery (SPSS shows thumbnails, not
// text). Blue = fill, drawn in a 24×18 viewBox.
const B = '#4e79c4'
const THUMBS: Record<string, JSX.Element> = {
  bar: (<svg viewBox="0 0 24 18"><rect x="2" y="8" width="4" height="8" fill={B} /><rect x="8" y="4" width="4" height="12" fill={B} /><rect x="14" y="10" width="4" height="6" fill={B} /><rect x="20" y="6" width="3" height="10" fill={B} /></svg>),
  bar3d: (<svg viewBox="0 0 24 18"><rect x="3" y="7" width="5" height="9" fill={B} /><rect x="11" y="4" width="5" height="12" fill="#3a5f9e" /><rect x="18" y="9" width="4" height="7" fill={B} /></svg>),
  line: (<svg viewBox="0 0 24 18"><polyline points="2,14 8,6 14,10 22,3" fill="none" stroke={B} strokeWidth="1.6" /></svg>),
  area: (<svg viewBox="0 0 24 18"><polygon points="2,16 2,12 9,5 16,9 22,4 22,16" fill={B} opacity="0.6" /></svg>),
  pie: (<svg viewBox="0 0 24 18"><circle cx="12" cy="9" r="7" fill={B} /><path d="M12 9 L12 2 A7 7 0 0 1 19 9 Z" fill="#e08a2f" /></svg>),
  scatter: (<svg viewBox="0 0 24 18"><circle cx="5" cy="13" r="1.6" fill={B} /><circle cx="10" cy="8" r="1.6" fill={B} /><circle cx="15" cy="11" r="1.6" fill={B} /><circle cx="19" cy="5" r="1.6" fill={B} /></svg>),
  hist: (<svg viewBox="0 0 24 18"><rect x="2" y="11" width="3" height="5" fill={B} /><rect x="6" y="6" width="3" height="10" fill={B} /><rect x="10" y="3" width="3" height="13" fill={B} /><rect x="14" y="7" width="3" height="9" fill={B} /><rect x="18" y="12" width="3" height="4" fill={B} /></svg>),
  hilo: (<svg viewBox="0 0 24 18"><line x1="6" y1="3" x2="6" y2="15" stroke={B} strokeWidth="1.4" /><line x1="12" y1="5" x2="12" y2="13" stroke={B} strokeWidth="1.4" /><line x1="18" y1="2" x2="18" y2="16" stroke={B} strokeWidth="1.4" /></svg>),
  box: (<svg viewBox="0 0 24 18"><line x1="12" y1="2" x2="12" y2="16" stroke={B} strokeWidth="1" /><rect x="6" y="6" width="12" height="7" fill="#cfe0f2" stroke={B} /><line x1="6" y1="9" x2="18" y2="9" stroke={B} strokeWidth="1.4" /></svg>),
  errorbar: (<svg viewBox="0 0 24 18"><line x1="8" y1="3" x2="8" y2="15" stroke={B} strokeWidth="1.4" /><circle cx="8" cy="9" r="2" fill={B} /><line x1="16" y1="5" x2="16" y2="13" stroke={B} strokeWidth="1.4" /><circle cx="16" cy="9" r="2" fill={B} /></svg>),
  pyramid: (<svg viewBox="0 0 24 18"><rect x="4" y="4" width="7" height="3" fill={B} /><rect x="4" y="8" width="5" height="3" fill={B} /><rect x="13" y="4" width="7" height="3" fill="#e08a2f" /><rect x="13" y="8" width="5" height="3" fill="#e08a2f" /></svg>)
}

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
                <MeasureIcon measure={v.measure} isString={v.isString} isDate={v.type === 'Date'} size={13} />
                <span className="cb-chip-name">{v.label ? v.label : v.name}</span>
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
            <button key={it.key} className={'cb2-gitem' + (it.key === specKey ? ' cb2-gitem--sel' : '')} onClick={() => pick(it.key)} title={it.label}>
              <span className="cb2-thumb">{THUMBS[it.key]}</span>
              <span className="cb2-gitem-label">{it.label}</span>
            </button>
          ))}
        </div>
      </div>
    </AnalysisFrame>
  )
}

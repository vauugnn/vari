import { useEffect, useLayoutEffect, useRef, useState } from 'react'

const SWATCHES = ['#4e79c4', '#5aa552', '#d9a441', '#d9433f', '#8c66b5', '#41b2c2', '#6d6e71', '#1192e8']

type Sel =
  | { kind: 'bar'; el: SVGElement; fill: string; edge: string; width: number }
  | { kind: 'text'; el: SVGElement; text: string; size: number; bold: boolean; color: string }
  | null

const styleOf = (el: Element, prop: string): string => {
  const m = new RegExp(`(?:^|;)\\s*${prop}:\\s*([^;]+)`, 'i').exec(el.getAttribute('style') || '')
  return m ? m[1].trim() : ''
}
const hex = (c: string): string => (/^#[0-9a-f]{6}$/i.test(c) ? c.toLowerCase() : '#000000')

// A data element: a filled shape inside a matplotlib `patch_N` group, past the
// two background patches (figure and axes).
function barOf(target: Element): SVGElement | null {
  const g = target.closest('g[id^="patch_"]')
  if (!g) return null
  const n = Number(g.id.replace('patch_', ''))
  const shape = g.querySelector('path') as SVGElement | null
  if (!shape || n <= 2) return null
  const fill = styleOf(shape, 'fill') || shape.getAttribute('fill') || ''
  return fill && fill !== 'none' ? shape : null
}

export function describe(target: Element): Sel {
  const bar = barOf(target)
  if (bar) {
    return {
      kind: 'bar',
      el: bar,
      fill: hex(styleOf(bar, 'fill') || bar.getAttribute('fill') || ''),
      edge: hex(styleOf(bar, 'stroke')),
      width: parseFloat(styleOf(bar, 'stroke-width')) || 0.5
    }
  }
  const t = target.closest('text') as SVGElement | null
  if (t) {
    const font = styleOf(t, 'font')
    const size = parseFloat(styleOf(t, 'font-size')) || parseFloat(/(\d+(?:\.\d+)?)px/.exec(font)?.[1] ?? '') || 10
    const weight = styleOf(t, 'font-weight') || font
    return {
      kind: 'text',
      el: t,
      text: t.textContent ?? '',
      size,
      bold: /bold|[6-9]00/.test(weight),
      color: hex(styleOf(t, 'fill') || t.getAttribute('fill') || '#000000')
    }
  }
  return null
}

export function setStyle(el: SVGElement, prop: string, value: string): void {
  const style = el.getAttribute('style') || ''
  const re = new RegExp(`(^|;)\\s*${prop}:\\s*[^;]+`, 'i')
  el.setAttribute('style', re.test(style) ? style.replace(re, `$1 ${prop}: ${value}`) : `${style}; ${prop}: ${value}`)
  if (prop === 'fill' && el.hasAttribute('fill')) el.setAttribute('fill', value)
}

export function ChartEditor({ svg, onApply, onCancel }: {
  svg: string
  onApply: (svg: string) => void
  onCancel: () => void
}): JSX.Element {
  const host = useRef<HTMLDivElement>(null)
  const stage = useRef<HTMLDivElement>(null)
  const [sel, setSel] = useState<Sel>(null)
  const [box, setBox] = useState<{ x: number; y: number; w: number; h: number } | null>(null)
  const undo = useRef<string[]>([])
  const redo = useRef<string[]>([])
  const [, bump] = useState(0)
  const [allBars, setAllBars] = useState(false)

  useLayoutEffect(() => {
    if (host.current) host.current.innerHTML = svg
  }, [svg])

  const snapshot = (): string => host.current?.innerHTML ?? ''
  const remember = (): void => {
    undo.current.push(snapshot())
    redo.current = []
    bump((n) => n + 1)
  }
  const restore = (html: string): void => {
    if (host.current) host.current.innerHTML = html
    setSel(null)
    setBox(null)
    bump((n) => n + 1)
  }

  // Keep the selection outline glued to the element (bounds in stage coordinates).
  useEffect(() => {
    if (!sel || !stage.current) return setBox(null)
    const s = stage.current.getBoundingClientRect()
    const r = sel.el.getBoundingClientRect()
    setBox({ x: r.left - s.left, y: r.top - s.top, w: r.width, h: r.height })
  }, [sel])

  const pick = (e: React.MouseEvent): void => {
    const target = e.target as Element
    setSel(target === e.currentTarget ? null : describe(target))
  }

  // Apply a change to the selected element, remembering the state for undo.
  const edit = (fn: (el: SVGElement) => void, refresh: (s: NonNullable<Sel>) => Sel): void => {
    if (!sel) return
    remember()
    fn(sel.el)
    setSel(refresh(sel))
  }

  const sameBars = (el: SVGElement): SVGElement[] => {
    const f = styleOf(el, 'fill')
    return Array.from(host.current?.querySelectorAll<SVGElement>('g[id^="patch_"] path') ?? []).filter(
      (p) => barOf(p) === p && styleOf(p, 'fill') === f
    )
  }

  const paintBars = (prop: 'fill' | 'stroke', value: string): void => {
    if (sel?.kind !== 'bar') return
    remember()
    const targets = allBars ? sameBars(sel.el) : [sel.el]
    targets.forEach((el) => setStyle(el, prop, value))
    setSel(describe(sel.el))
  }

  const finish = (): void => {
    setSel(null)
    const out = host.current?.querySelector('svg')
    if (out) onApply(out.outerHTML)
  }

  return (
    <div className="out-chart-lightbox" onClick={onCancel}>
      <div className="chart-editor" onClick={(e) => e.stopPropagation()}>
        <div className="chart-editor-head">Chart Editor</div>
        <div className="chart-editor-toolbar">
          <button disabled={!undo.current.length} onClick={() => {
            const prev = undo.current.pop()
            if (prev === undefined) return
            redo.current.push(snapshot())
            restore(prev)
          }}>Undo</button>
          <button disabled={!redo.current.length} onClick={() => {
            const next = redo.current.pop()
            if (next === undefined) return
            undo.current.push(snapshot())
            restore(next)
          }}>Redo</button>
          <span className="chart-editor-tip">Click any bar or text to edit it</span>
        </div>
        <div className="chart-editor-body">
          <div className="chart-editor-stage" ref={stage} onClick={pick}>
            <div className="chart-editor-svg" ref={host} />
            {box && <div className="chart-editor-sel" style={{ left: box.x - 2, top: box.y - 2, width: box.w + 4, height: box.h + 4 }} />}
          </div>
          <div className="chart-editor-controls">
            <div className="chart-editor-hint">
              {sel ? (sel.kind === 'bar' ? 'Properties: Bar' : 'Properties: Text') : 'Nothing selected'}
            </div>
            {sel?.kind === 'bar' && (
              <>
                <label>Fill colour
                  <input type="color" value={sel.fill} onChange={(e) => paintBars('fill', e.target.value)} />
                </label>
                <div className="chart-editor-swatches">
                  {SWATCHES.map((c) => (
                    <button key={c} className="chart-editor-swatch" style={{ background: c }} title={c}
                      onClick={() => paintBars('fill', c)} />
                  ))}
                </div>
                <label>Border colour
                  <input type="color" value={sel.edge} onChange={(e) => paintBars('stroke', e.target.value)} />
                </label>
                <label>Border weight
                  <input type="number" min={0} max={5} step={0.5} value={sel.width}
                    onChange={(e) => edit((el) => setStyle(el, 'stroke-width', e.target.value || '0'),
                      () => describe(sel.el))} />
                </label>
                <label className="chart-editor-check">
                  <input type="checkbox" checked={allBars} onChange={(e) => setAllBars(e.target.checked)} />
                  Apply to all bars of this colour
                </label>
              </>
            )}
            {sel?.kind === 'text' && (
              <>
                <label>Text
                  <input type="text" value={sel.text}
                    onChange={(e) => edit((el) => { el.textContent = e.target.value }, () => describe(sel.el))} />
                </label>
                <label>Size (px)
                  <input type="number" min={4} max={48} value={sel.size}
                    onChange={(e) => edit((el) => setStyle(el, 'font-size', `${e.target.value || 10}px`), () => describe(sel.el))} />
                </label>
                <label className="chart-editor-check">
                  <input type="checkbox" checked={sel.bold}
                    onChange={(e) => edit((el) => setStyle(el, 'font-weight', e.target.checked ? 'bold' : 'normal'), () => describe(sel.el))} />
                  Bold
                </label>
                <label>Colour
                  <input type="color" value={sel.color}
                    onChange={(e) => edit((el) => setStyle(el, 'fill', e.target.value), () => describe(sel.el))} />
                </label>
              </>
            )}
            <div className="chart-editor-actions">
              <button onClick={finish}>OK</button>
              <button onClick={onCancel}>Cancel</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

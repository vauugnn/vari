// Original measure-level and toolbar icons drawn as inline SVG. These evoke the
// SPSS Variable-measure glyphs (ruler = Scale, ascending bars = Ordinal, three
// circles = Nominal) without copying IBM artwork (see CLAUDE.md: no IBM assets).
import type { Measure } from '../../shared/types'

export function MeasureIcon({
  measure,
  isString,
  isDate,
  size = 16
}: {
  measure: Measure
  isString?: boolean
  isDate?: boolean
  size?: number
}): JSX.Element {
  const glyph = isDate ? <DateGlyph /> : measure === 'scale' ? <ScaleGlyph /> : measure === 'ordinal' ? <OrdinalGlyph /> : <NominalGlyph />
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" className="measure-icon" aria-hidden>
      {glyph}
      {isString && <StringBadge />}
    </svg>
  )
}

function ScaleGlyph(): JSX.Element {
  // A little ruler.
  return (
    <g>
      <rect x="1" y="5" width="14" height="6" rx="1" fill="#f2c14e" stroke="#b8860b" />
      <g stroke="#7a5b00">
        <line x1="4" y1="5" x2="4" y2="9" />
        <line x1="7" y1="5" x2="7" y2="8" />
        <line x1="10" y1="5" x2="10" y2="9" />
        <line x1="13" y1="5" x2="13" y2="8" />
      </g>
    </g>
  )
}

function OrdinalGlyph(): JSX.Element {
  // Three ascending bars.
  return (
    <g>
      <rect x="2" y="10" width="3" height="4" fill="#e6b800" stroke="#8a6d00" />
      <rect x="6.5" y="7" width="3" height="7" fill="#7ab648" stroke="#4d7a2a" />
      <rect x="11" y="3" width="3" height="11" fill="#4e79c4" stroke="#2f4f8a" />
    </g>
  )
}

function NominalGlyph(): JSX.Element {
  // Three overlapping circles.
  return (
    <g>
      <circle cx="6" cy="6" r="3.4" fill="#d9433f" stroke="#9c2b28" />
      <circle cx="10" cy="6" r="3.4" fill="#4e79c4" stroke="#2f4f8a" />
      <circle cx="8" cy="10" r="3.4" fill="#7ab648" stroke="#4d7a2a" />
    </g>
  )
}

function DateGlyph(): JSX.Element {
  return (
    <g>
      <rect x="2" y="3" width="12" height="11" rx="1" fill="#ffffff" stroke="#666" />
      <rect x="2" y="3" width="12" height="3" fill="#c0392b" stroke="#666" />
      <g stroke="#999">
        <line x1="5" y1="8" x2="11" y2="8" />
        <line x1="5" y1="11" x2="11" y2="11" />
      </g>
    </g>
  )
}

function StringBadge(): JSX.Element {
  return (
    <g>
      <text x="11" y="15" fontSize="8" fontStyle="italic" fill="#c0392b" fontFamily="Georgia,serif">
        a
      </text>
    </g>
  )
}

// --- simple toolbar glyphs ---
export function OpenIcon(): JSX.Element {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden>
      <path d="M2 4h5l2 2h7v8H2z" fill="#f2c14e" stroke="#9c7a1a" strokeWidth="1" />
      <path d="M2 7h14l-2 7H2z" fill="#ffe08a" stroke="#9c7a1a" strokeWidth="1" />
    </svg>
  )
}

export function SaveIcon(): JSX.Element {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden>
      <rect x="2" y="2" width="14" height="14" rx="1" fill="#4e79c4" stroke="#2f4f8a" />
      <rect x="5" y="2" width="8" height="5" fill="#dfe8f5" />
      <rect x="10" y="3" width="2" height="3" fill="#2f4f8a" />
      <rect x="5" y="9" width="8" height="5" fill="#eef2f8" stroke="#2f4f8a" />
    </svg>
  )
}

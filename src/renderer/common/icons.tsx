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

function Ico({ children }: { children: JSX.Element }): JSX.Element {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden>
      {children}
    </svg>
  )
}

// A small SPSS-style data table: light-blue cells, a darker blue header row,
// hairline grid. Reused as the base of several toolbar glyphs.
function TableBase({ x = 2, y = 3, w = 14, h = 12 }: { x?: number; y?: number; w?: number; h?: number }): JSX.Element {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} fill="#eaf1fb" stroke="#3f6fb0" />
      <rect x={x} y={y} width={w} height={3} fill="#4e79c4" stroke="#3f6fb0" />
      <g stroke="#b7cbe6" strokeWidth="0.6">
        <line x1={x + w / 3} y1={y + 3} x2={x + w / 3} y2={y + h} />
        <line x1={x + (2 * w) / 3} y1={y + 3} x2={x + (2 * w) / 3} y2={y + h} />
        <line x1={x} y1={y + 6} x2={x + w} y2={y + 6} />
        <line x1={x} y1={y + 9} x2={x + w} y2={y + 9} />
        <line x1={x} y1={y + 12} x2={x + w} y2={y + 12} />
      </g>
    </g>
  )
}

export const NewIcon = (): JSX.Element => (
  <Ico>
    <g>
      <path d="M4 2h7l3 3v11H4z" fill="#ffffff" stroke="#5a6673" />
      <path d="M11 2v3h3" fill="#dfe8f5" stroke="#5a6673" />
      <g stroke="#2f8f2f" strokeWidth="1.6">
        <line x1="12" y1="10" x2="12" y2="15" />
        <line x1="9.5" y1="12.5" x2="14.5" y2="12.5" />
      </g>
    </g>
  </Ico>
)

export const PrintIcon = (): JSX.Element => (
  <Ico>
    <g>
      <rect x="4" y="2" width="10" height="5" fill="#f2f2f2" stroke="#5a6673" />
      <rect x="2" y="7" width="14" height="6" rx="1" fill="#9aa7b4" stroke="#5a6673" />
      <rect x="4" y="11" width="10" height="5" fill="#fff" stroke="#5a6673" />
      <circle cx="13" cy="9.5" r="1" fill="#2f8f2f" />
    </g>
  </Ico>
)

export const RecallIcon = (): JSX.Element => (
  <Ico>
    <g>
      <rect x="3" y="9" width="12" height="6" rx="1" fill="#eef0f2" stroke="#5a6673" />
      <path d="M9 2v6" stroke="#d9342b" strokeWidth="2" />
      <path d="M5.5 6.5L9 10l3.5-3.5z" fill="#d9342b" />
    </g>
  </Ico>
)

export const UndoIcon = (): JSX.Element => (
  <Ico>
    <path d="M6 5L2 9l4 4V10h5a3 3 0 010 6H8" fill="none" stroke="#3a6ea5" strokeWidth="1.7" strokeLinejoin="round" />
  </Ico>
)

export const RedoIcon = (): JSX.Element => (
  <Ico>
    <path d="M12 5l4 4-4 4V10H7a3 3 0 000 6h3" fill="none" stroke="#3a6ea5" strokeWidth="1.7" strokeLinejoin="round" />
  </Ico>
)

export const GotoCaseIcon = (): JSX.Element => (
  <Ico>
    <g>
      <TableBase />
      <rect x="2" y="9" width="14" height="3" fill="#ffe08a" stroke="#3f6fb0" opacity="0.85" />
      <path d="M0 10.5h5" stroke="#d9342b" strokeWidth="1.8" />
      <path d="M4 8l3 2.5-3 2.5z" fill="#d9342b" />
    </g>
  </Ico>
)

export const GotoVarIcon = (): JSX.Element => (
  <Ico>
    <g>
      <TableBase />
      <rect x="6.7" y="3" width="4.6" height="12" fill="#ffe08a" stroke="#3f6fb0" opacity="0.85" />
      <path d="M9 0v5" stroke="#d9342b" strokeWidth="1.8" />
      <path d="M6.5 4l2.5 3 2.5-3z" fill="#d9342b" />
    </g>
  </Ico>
)

export const VariablesIcon = (): JSX.Element => (
  <Ico>
    <g>
      <rect x="2" y="2" width="14" height="14" rx="1" fill="#ffffff" stroke="#5a6673" />
      <rect x="2" y="2" width="14" height="3" fill="#4e79c4" stroke="#3f6fb0" />
      <g stroke="#7ab648" strokeWidth="1.3">
        <line x1="4" y1="8" x2="6" y2="8" />
        <line x1="4" y1="11" x2="6" y2="11" />
        <line x1="4" y1="14" x2="6" y2="14" />
      </g>
      <g stroke="#9aa7b4">
        <line x1="8" y1="8" x2="14" y2="8" />
        <line x1="8" y1="11" x2="14" y2="11" />
        <line x1="8" y1="14" x2="14" y2="14" />
      </g>
    </g>
  </Ico>
)

export const FindIcon = (): JSX.Element => (
  <Ico>
    <g fill="#8a939c" stroke="#555">
      <circle cx="6" cy="10" r="3.6" fill="#8a939c" />
      <circle cx="12" cy="10" r="3.6" fill="#8a939c" />
      <circle cx="6" cy="10" r="1.7" fill="#dfe8f5" stroke="none" />
      <circle cx="12" cy="10" r="1.7" fill="#dfe8f5" stroke="none" />
      <path d="M4 6l2-2 1 1M14 6l-2-2-1 1" fill="none" stroke="#555" strokeWidth="1.2" />
    </g>
  </Ico>
)

export const InsertCaseIcon = (): JSX.Element => (
  <Ico>
    <g>
      <TableBase />
      <rect x="2" y="9" width="14" height="3" fill="#cdeccd" stroke="#3f6fb0" />
      <g stroke="#2f8f2f" strokeWidth="1.6">
        <line x1="0.5" y1="10.5" x2="4.5" y2="10.5" />
        <line x1="2.5" y1="8.5" x2="2.5" y2="12.5" />
      </g>
    </g>
  </Ico>
)

export const InsertVarIcon = (): JSX.Element => (
  <Ico>
    <g>
      <TableBase />
      <rect x="6.7" y="3" width="4.6" height="12" fill="#cdeccd" stroke="#3f6fb0" />
      <g stroke="#2f8f2f" strokeWidth="1.6">
        <line x1="9" y1="0.5" x2="9" y2="4.5" />
        <line x1="7" y1="2.5" x2="11" y2="2.5" />
      </g>
    </g>
  </Ico>
)

export const SplitFileIcon = (): JSX.Element => (
  <Ico>
    <g>
      <TableBase x={1} y={4} w={7} h={10} />
      <g transform="translate(9,0)">
        <rect x="0" y="4" width="7" height="10" fill="#fdf3d6" stroke="#c9a94e" />
        <rect x="0" y="4" width="7" height="2.5" fill="#e6b800" stroke="#c9a94e" />
      </g>
    </g>
  </Ico>
)

export const WeightIcon = (): JSX.Element => (
  <Ico>
    <g stroke="#5a6673" strokeWidth="1.1" fill="none">
      <line x1="9" y1="2" x2="9" y2="14" />
      <line x1="4" y1="5" x2="14" y2="5" />
      <path d="M4 5l-2 5h4z" fill="#f2c14e" />
      <path d="M14 5l-2 5h4z" fill="#f2c14e" />
      <line x1="5.5" y1="15" x2="12.5" y2="15" strokeWidth="1.4" />
    </g>
  </Ico>
)

export const SelectCasesIcon = (): JSX.Element => (
  <Ico>
    <g>
      <TableBase />
      <path d="M4 5h10l-3.5 4v4l-3-1.5V9z" fill="#d9342b" stroke="#9c2b28" opacity="0.92" />
    </g>
  </Ico>
)

export const ValueLabelsIcon = (): JSX.Element => (
  <Ico>
    <g>
      <rect x="2" y="4" width="14" height="10" rx="1" fill="#ffffff" stroke="#5a6673" />
      <text x="5" y="12" fontSize="8" fontWeight="bold" fill="#4e79c4" textAnchor="middle">
        1
      </text>
      <path d="M7.5 9h3" stroke="#d9342b" strokeWidth="1.2" />
      <path d="M9.5 7.6l1.4 1.4-1.4 1.4" fill="none" stroke="#d9342b" strokeWidth="1.2" />
      <text x="13" y="12" fontSize="8" fontStyle="italic" fill="#2f8f2f" textAnchor="middle" fontFamily="Georgia,serif">
        a
      </text>
    </g>
  </Ico>
)

export const VarSetsIcon = (): JSX.Element => (
  <Ico>
    <g fillOpacity="0.55">
      <circle cx="7" cy="9" r="5" fill="#4e79c4" stroke="#2f4f8a" />
      <circle cx="11" cy="9" r="5" fill="#e08a2f" stroke="#a85f14" />
    </g>
  </Ico>
)

export const ShowAllVarsIcon = (): JSX.Element => (
  <Ico>
    <g stroke="#ffffff" strokeWidth="0.8">
      <rect x="2" y="2" width="6.5" height="6.5" fill="#d9433f" />
      <rect x="9.5" y="2" width="6.5" height="6.5" fill="#7ab648" />
      <rect x="2" y="9.5" width="6.5" height="6.5" fill="#4e79c4" />
      <rect x="9.5" y="9.5" width="6.5" height="6.5" fill="#e6a417" />
    </g>
  </Ico>
)

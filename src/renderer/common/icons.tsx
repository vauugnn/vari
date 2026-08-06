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

export const NewIcon = (): JSX.Element => (
  <Ico>
    <g>
      <path d="M4 2h7l3 3v11H4z" fill="#ffffff" stroke="#666" />
      <path d="M11 2v3h3" fill="none" stroke="#666" />
      <g stroke="#7ab648" strokeWidth="1.4">
        <line x1="12" y1="10" x2="12" y2="16" />
        <line x1="9" y1="13" x2="15" y2="13" />
      </g>
    </g>
  </Ico>
)

export const PrintIcon = (): JSX.Element => (
  <Ico>
    <g>
      <rect x="4" y="2" width="10" height="5" fill="#eee" stroke="#666" />
      <rect x="2" y="7" width="14" height="6" rx="1" fill="#9aa7b4" stroke="#5a6673" />
      <rect x="4" y="11" width="10" height="5" fill="#fff" stroke="#666" />
      <circle cx="13" cy="9" r="1" fill="#7ab648" />
    </g>
  </Ico>
)

export const RecallIcon = (): JSX.Element => (
  <Ico>
    <g>
      <rect x="2" y="3" width="14" height="12" rx="1" fill="#f2f2f2" stroke="#888" />
      <line x1="2" y1="6" x2="16" y2="6" stroke="#888" />
      <path d="M6 9l3 3 3-3z" fill="#4e79c4" />
    </g>
  </Ico>
)

export const UndoIcon = (): JSX.Element => (
  <Ico>
    <path d="M6 5L2 9l4 4V10h5a3 3 0 010 6H8" fill="none" stroke="#2f6f2f" strokeWidth="1.6" />
  </Ico>
)

export const RedoIcon = (): JSX.Element => (
  <Ico>
    <path d="M12 5l4 4-4 4V10H7a3 3 0 000 6h3" fill="none" stroke="#6a2f2f" strokeWidth="1.6" />
  </Ico>
)

export const GotoCaseIcon = (): JSX.Element => (
  <Ico>
    <g>
      <rect x="2" y="3" width="14" height="12" fill="#fff" stroke="#888" />
      <rect x="2" y="7" width="14" height="3" fill="#cfe0f2" stroke="#888" />
      <path d="M15 8.5l3 0M16 6l2 2.5-2 2.5" fill="none" stroke="#c0392b" strokeWidth="1.4" transform="translate(-4,0)" />
    </g>
  </Ico>
)

export const GotoVarIcon = (): JSX.Element => (
  <Ico>
    <g>
      <rect x="2" y="3" width="14" height="12" fill="#fff" stroke="#888" />
      <rect x="6" y="3" width="3" height="12" fill="#cfe0f2" stroke="#888" />
      <path d="M8 1.5l0 3M6 3l2-2 2 2" fill="none" stroke="#c0392b" strokeWidth="1.4" transform="translate(0,-0)" />
    </g>
  </Ico>
)

export const VariablesIcon = (): JSX.Element => (
  <Ico>
    <g>
      <rect x="2" y="2" width="14" height="14" rx="2" fill="#4e79c4" stroke="#2f4f8a" />
      <text x="9" y="13" fontSize="11" fontWeight="bold" fill="#fff" textAnchor="middle" fontFamily="Georgia,serif">
        i
      </text>
    </g>
  </Ico>
)

export const FindIcon = (): JSX.Element => (
  <Ico>
    <g stroke="#444" strokeWidth="1.6" fill="none">
      <circle cx="7" cy="7" r="4" fill="#dfe8f5" />
      <line x1="10" y1="10" x2="15" y2="15" />
    </g>
  </Ico>
)

export const InsertCaseIcon = (): JSX.Element => (
  <Ico>
    <g>
      <rect x="2" y="3" width="14" height="12" fill="#fff" stroke="#888" />
      <line x1="2" y1="7" x2="16" y2="7" stroke="#888" />
      <line x1="2" y1="11" x2="16" y2="11" stroke="#888" />
      <rect x="2" y="7" width="14" height="4" fill="#d9f0d0" />
      <g stroke="#2f6f2f" strokeWidth="1.4">
        <line x1="12" y1="4" x2="12" y2="8" />
        <line x1="10" y1="6" x2="14" y2="6" />
      </g>
    </g>
  </Ico>
)

export const InsertVarIcon = (): JSX.Element => (
  <Ico>
    <g>
      <rect x="2" y="3" width="14" height="12" fill="#fff" stroke="#888" />
      <line x1="7" y1="3" x2="7" y2="15" stroke="#888" />
      <line x1="11" y1="3" x2="11" y2="15" stroke="#888" />
      <rect x="7" y="3" width="4" height="12" fill="#d9f0d0" />
      <g stroke="#2f6f2f" strokeWidth="1.4">
        <line x1="9" y1="6" x2="9" y2="10" />
        <line x1="7" y1="8" x2="11" y2="8" />
      </g>
    </g>
  </Ico>
)

export const SplitFileIcon = (): JSX.Element => (
  <Ico>
    <g>
      <rect x="2" y="3" width="6" height="12" fill="#cfe0f2" stroke="#888" />
      <rect x="10" y="3" width="6" height="12" fill="#f2dfcf" stroke="#888" />
    </g>
  </Ico>
)

export const WeightIcon = (): JSX.Element => (
  <Ico>
    <g stroke="#5a6673" strokeWidth="1.2" fill="none">
      <line x1="9" y1="2" x2="9" y2="14" />
      <line x1="4" y1="5" x2="14" y2="5" />
      <path d="M4 5l-2 5h4z" fill="#f2c14e" />
      <path d="M14 5l-2 5h4z" fill="#f2c14e" />
      <line x1="5" y1="15" x2="13" y2="15" />
    </g>
  </Ico>
)

export const SelectCasesIcon = (): JSX.Element => (
  <Ico>
    <path d="M2 3h14l-5 6v6l-4-2V9z" fill="#cfe0f2" stroke="#5a6673" />
  </Ico>
)

export const ValueLabelsIcon = (): JSX.Element => (
  <Ico>
    <g>
      <path d="M2 6l6-3 8 3-8 3z" fill="#f2c14e" stroke="#9c7a1a" />
      <text x="8" y="14" fontSize="7" fill="#333" textAnchor="middle">
        1→a
      </text>
    </g>
  </Ico>
)

export const VarSetsIcon = (): JSX.Element => (
  <Ico>
    <g fill="#4e79c4" stroke="#2f4f8a">
      <rect x="2" y="2" width="6" height="6" />
      <rect x="10" y="2" width="6" height="6" />
      <rect x="2" y="10" width="6" height="6" />
      <rect x="10" y="10" width="6" height="6" />
    </g>
  </Ico>
)

export const ShowAllVarsIcon = (): JSX.Element => (
  <Ico>
    <g fill="none" stroke="#444" strokeWidth="1.3">
      <path d="M2 9s3-5 7-5 7 5 7 5-3 5-7 5-7-5-7-5z" fill="#dfe8f5" />
      <circle cx="9" cy="9" r="2" fill="#4e79c4" />
    </g>
  </Ico>
)

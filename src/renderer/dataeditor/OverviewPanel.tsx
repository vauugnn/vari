import type { DatasetSummary, Measure } from '../../shared/types'
import { MeasureIcon } from '../common/icons'
import './overview.css'

// The Overview dashboard (SPSS's third Data Editor tab): dataset size, the
// measurement-level distribution, and a missing-values note. All derived from
// the variable metadata already in the summary — no extra sidecar call.
export function OverviewPanel({ summary }: { summary: DatasetSummary }): JSX.Element {
  const total = summary.variables.length || 1
  const levels: { key: Measure; label: string; isString?: boolean; isDate?: boolean }[] = [
    { key: 'scale', label: 'Scale' },
    { key: 'ordinal', label: 'Ordinal' },
    { key: 'nominal', label: 'Nominal' }
  ]
  const counts = levels.map((l) => ({
    ...l,
    n: summary.variables.filter((v) => v.measure === l.key).length
  }))
  const withMissing = summary.variables.filter((v) => v.missing && v.missing.kind !== 'none').length

  return (
    <div className="ov-root">
      <div className="ov-cards">
        <div className="ov-card ov-card--count">
          <div className="ov-file">{summary.name}</div>
          <div className="ov-big">{summary.nVars}</div>
          <div className="ov-small">Variables</div>
          <div className="ov-big">{summary.nRows.toLocaleString()}</div>
          <div className="ov-small">Cases</div>
        </div>

        <div className="ov-card">
          <div className="ov-title">Measurement Level</div>
          <div className="ov-bars">
            {counts.map((c) => {
              const pct = (c.n / total) * 100
              return (
                <div key={c.key} className="ov-barcol">
                  <div className="ov-pct">{pct.toFixed(1)}%</div>
                  <div className="ov-bar" style={{ height: `${Math.max(4, pct * 1.6)}px` }} />
                  <div className="ov-barlabel">
                    <MeasureIcon measure={c.key} size={13} /> {c.label}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        <div className="ov-card">
          <div className="ov-title">Summary of Missing Values</div>
          <div className="ov-missing">
            {withMissing > 0 ? (
              <>
                <div className="ov-big">{withMissing}</div>
                <div className="ov-small">
                  variable{withMissing === 1 ? '' : 's'} with user-missing definitions
                </div>
              </>
            ) : (
              <div className="ov-small">No user-missing values are defined in this dataset.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

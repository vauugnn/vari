import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'
import { StatsPicker, type StatOption } from './StatsPicker'

const STAT_OPTIONS: StatOption[] = [
  { key: 'MEAN', label: 'Mean' },
  { key: 'MEDIAN', label: 'Median' },
  { key: 'MODE', label: 'Mode' },
  { key: 'SUM', label: 'Sum' },
  { key: 'STDDEV', label: 'Std. deviation' },
  { key: 'VARIANCE', label: 'Variance' },
  { key: 'RANGE', label: 'Range' },
  { key: 'MINIMUM', label: 'Minimum' },
  { key: 'MAXIMUM', label: 'Maximum' },
  { key: 'SEMEAN', label: 'S.E. mean' },
  { key: 'SKEWNESS', label: 'Skewness' },
  { key: 'KURTOSIS', label: 'Kurtosis' }
]

export function FrequenciesDialog({
  variables,
  onClose
}: {
  variables: VariableMetaJson[]
  onClose: () => void
}): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [displayTables, setDisplayTables] = useState(true)
  const [stats, setStats] = useState<Set<string>>(new Set())
  const [showStats, setShowStats] = useState(false)

  const toSyntax = (): string => {
    let s = `FREQUENCIES VARIABLES=${vars.join(' ')}`
    const chosen = STAT_OPTIONS.filter((o) => stats.has(o.key)).map((o) => o.key)
    if (chosen.length) s += `\n  /STATISTICS=${chosen.join(' ')}`
    if (!displayTables) s += `\n  /FORMAT=NOTABLE`
    return s + '.'
  }

  const ok = () => {
    void window.spss.execute(toSyntax())
    onClose()
  }
  const paste = () => {
    window.spss.paste(toSyntax())
    onClose()
  }
  const reset = () => {
    setVars([])
    setDisplayTables(true)
    setStats(new Set())
  }

  return (
    <>
      <AnalysisFrame
        title="Frequencies"
        onOk={ok}
        onPaste={paste}
        onReset={reset}
        onCancel={onClose}
        okDisabled={vars.length === 0}
        subButtons={[{ label: 'Statistics…', onClick: () => setShowStats(true) }]}
      >
        <VarMover variables={variables} value={vars} onChange={setVars} label="Variable(s):" />
        <div className="opts">
          <label>
            <input type="checkbox" checked={displayTables} onChange={(e) => setDisplayTables(e.target.checked)} />
            Display frequency tables
          </label>
        </div>
      </AnalysisFrame>
      {showStats && (
        <StatsPicker
          title="Frequencies: Statistics"
          options={STAT_OPTIONS}
          initial={stats}
          onOk={(s) => {
            setStats(s)
            setShowStats(false)
          }}
          onCancel={() => setShowStats(false)}
        />
      )}
    </>
  )
}

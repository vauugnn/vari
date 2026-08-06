import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'
import { StatsPicker, type StatOption } from './StatsPicker'

const STAT_OPTIONS: StatOption[] = [
  { key: 'MEAN', label: 'Mean' },
  { key: 'SUM', label: 'Sum' },
  { key: 'STDDEV', label: 'Std. deviation' },
  { key: 'VARIANCE', label: 'Variance' },
  { key: 'RANGE', label: 'Range' },
  { key: 'MINIMUM', label: 'Minimum' },
  { key: 'MAXIMUM', label: 'Maximum' },
  { key: 'SEMEAN', label: 'S.E. mean' },
  { key: 'KURTOSIS', label: 'Kurtosis' },
  { key: 'SKEWNESS', label: 'Skewness' }
]
const DEFAULTS = new Set(['MEAN', 'STDDEV', 'MINIMUM', 'MAXIMUM'])

export function DescriptivesDialog({
  variables,
  onClose
}: {
  variables: VariableMetaJson[]
  onClose: () => void
}): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [stats, setStats] = useState<Set<string>>(new Set(DEFAULTS))
  const [showStats, setShowStats] = useState(false)

  const toSyntax = (): string => {
    let s = `DESCRIPTIVES VARIABLES=${vars.join(' ')}`
    const chosen = STAT_OPTIONS.filter((o) => stats.has(o.key)).map((o) => o.key)
    if (chosen.length) s += `\n  /STATISTICS=${chosen.join(' ')}`
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

  return (
    <>
      <AnalysisFrame
        title="Descriptives"
        onOk={ok}
        onPaste={paste}
        onReset={() => {
          setVars([])
          setStats(new Set(DEFAULTS))
        }}
        onCancel={onClose}
        okDisabled={vars.length === 0}
        subButtons={[{ label: 'Options…', onClick: () => setShowStats(true) }]}
      >
        <VarMover
          variables={variables}
          value={vars}
          onChange={setVars}
          label="Variable(s):"
          accept={(v) => !v.isString}
        />
      </AnalysisFrame>
      {showStats && (
        <StatsPicker
          title="Descriptives: Options"
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

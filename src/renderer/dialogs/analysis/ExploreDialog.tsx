import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'
import { Modal } from '../Modal'

export function ExploreDialog({
  variables,
  onClose
}: {
  variables: VariableMetaJson[]
  onClose: () => void
}): JSX.Element {
  const [deps, setDeps] = useState<string[]>([])
  const [factor, setFactor] = useState<string[]>([])
  const [display, setDisplay] = useState<'both' | 'stats' | 'plots'>('both')
  const [boxplot, setBoxplot] = useState(true)
  const [npplot, setNpplot] = useState(true)
  const [dlg, setDlg] = useState(false)

  const syntax = (): string => {
    const by = factor.length ? ` BY ${factor[0]}` : ''
    const plots = [boxplot && 'BOXPLOT', npplot && 'NPPLOT'].filter(Boolean) as string[]
    const lines = [`EXAMINE VARIABLES=${deps.join(' ')}${by}`]
    if (display !== 'stats') lines.push(`  /PLOT ${plots.join(' ') || 'NONE'}`)
    if (display !== 'plots') lines.push(`  /STATISTICS DESCRIPTIVES`)
    return lines.join('\n') + '.'
  }
  return (
    <>
      <AnalysisFrame
        title="Explore"
        onOk={() => {
          void window.spss.execute(syntax())
          onClose()
        }}
        onPaste={() => {
          window.spss.paste(syntax())
          onClose()
        }}
        onReset={() => {
          setDeps([])
          setFactor([])
        }}
        onCancel={onClose}
        okDisabled={deps.length === 0}
        subButtons={[{ label: 'Plots…', onClick: () => setDlg(true) }]}
      >
        <VarMover variables={variables} value={deps} onChange={setDeps} label="Dependent List:" accept={(v) => !v.isString} />
        <div style={{ height: 8 }} />
        <VarMover variables={variables} value={factor} onChange={(v) => setFactor(v.slice(-1))} label="Factor List:" />
        <fieldset style={{ marginTop: 8, border: '1px solid #c0c0c0', padding: '4px 8px' }}>
          <legend>Display</legend>
          <label><input type="radio" checked={display === 'both'} onChange={() => setDisplay('both')} /> Both</label>
          <label><input type="radio" checked={display === 'stats'} onChange={() => setDisplay('stats')} /> Statistics</label>
          <label><input type="radio" checked={display === 'plots'} onChange={() => setDisplay('plots')} /> Plots</label>
        </fieldset>
      </AnalysisFrame>
      {dlg && (
        <Modal title="Explore: Plots" onOk={() => setDlg(false)} onCancel={() => setDlg(false)}>
          <div className="stat-grid">
            <label><input type="checkbox" checked={boxplot} onChange={(e) => setBoxplot(e.target.checked)} /> Boxplots</label>
            <label><input type="checkbox" checked={npplot} onChange={(e) => setNpplot(e.target.checked)} /> Normality plots (Q-Q)</label>
          </div>
        </Modal>
      )}
    </>
  )
}

export function PartialCorrDialog({
  variables,
  onClose
}: {
  variables: VariableMetaJson[]
  onClose: () => void
}): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [controls, setControls] = useState<string[]>([])
  const syntax = (): string => `PARTIAL CORR\n  /VARIABLES=${vars.join(' ')} BY ${controls.join(' ')}.`
  return (
    <AnalysisFrame
      title="Partial Correlations"
      onOk={() => {
        void window.spss.execute(syntax())
        onClose()
      }}
      onPaste={() => {
        window.spss.paste(syntax())
        onClose()
      }}
      onReset={() => {
        setVars([])
        setControls([])
      }}
      onCancel={onClose}
      okDisabled={vars.length < 2 || controls.length === 0}
    >
      <VarMover variables={variables} value={vars} onChange={setVars} label="Variables:" accept={(v) => !v.isString} />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={controls} onChange={setControls} label="Controlling for:" accept={(v) => !v.isString} />
    </AnalysisFrame>
  )
}

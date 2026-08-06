import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

export function ExploreDialog({
  variables,
  onClose
}: {
  variables: VariableMetaJson[]
  onClose: () => void
}): JSX.Element {
  const [deps, setDeps] = useState<string[]>([])
  const [factor, setFactor] = useState<string[]>([])

  const syntax = (): string => {
    const by = factor.length ? ` BY ${factor[0]}` : ''
    return `EXAMINE VARIABLES=${deps.join(' ')}${by}\n  /PLOT BOXPLOT NPPLOT\n  /STATISTICS DESCRIPTIVES.`
  }
  return (
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
    >
      <VarMover variables={variables} value={deps} onChange={setDeps} label="Dependent List:" accept={(v) => !v.isString} />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={factor} onChange={(v) => setFactor(v.slice(-1))} label="Factor List:" />
    </AnalysisFrame>
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

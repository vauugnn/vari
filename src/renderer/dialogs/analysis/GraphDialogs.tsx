import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

type Props = { variables: VariableMetaJson[]; onClose: () => void }

function oneVarDialog(title: string, label: string, build: (v: string) => string, accept?: (v: VariableMetaJson) => boolean) {
  return function Dialog({ variables, onClose }: Props): JSX.Element {
    const [vars, setVars] = useState<string[]>([])
    const syntax = () => build(vars[0])
    return (
      <AnalysisFrame
        title={title}
        onOk={() => {
          void window.spss.execute(syntax())
          onClose()
        }}
        onPaste={() => {
          window.spss.paste(syntax())
          onClose()
        }}
        onReset={() => setVars([])}
        onCancel={onClose}
        okDisabled={vars.length === 0}
      >
        <VarMover variables={variables} value={vars} onChange={(v) => setVars(v.slice(-1))} label={label} accept={accept} />
      </AnalysisFrame>
    )
  }
}

export const HistogramDialog = oneVarDialog('Histogram', 'Variable:', (v) => `GRAPH\n  /HISTOGRAM=${v}.`, (v) => !v.isString)
export const BarChartDialog = oneVarDialog('Bar Charts', 'Category Axis:', (v) => `GRAPH\n  /BAR(SIMPLE)=COUNT BY ${v}.`)
export const PieChartDialog = oneVarDialog('Pie Charts', 'Define Slices by:', (v) => `GRAPH\n  /PIE=COUNT BY ${v}.`)

export function ScatterDialog({ variables, onClose }: Props): JSX.Element {
  const [y, setY] = useState<string[]>([])
  const [x, setX] = useState<string[]>([])
  const syntax = () => `GRAPH\n  /SCATTERPLOT(BIVAR)=${x[0]} WITH ${y[0]}.`
  return (
    <AnalysisFrame
      title="Simple Scatterplot"
      onOk={() => {
        void window.spss.execute(syntax())
        onClose()
      }}
      onPaste={() => {
        window.spss.paste(syntax())
        onClose()
      }}
      onReset={() => {
        setX([])
        setY([])
      }}
      onCancel={onClose}
      okDisabled={x.length === 0 || y.length === 0}
    >
      <VarMover variables={variables} value={y} onChange={(v) => setY(v.slice(-1))} label="Y Axis:" accept={(v) => !v.isString} />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={x} onChange={(v) => setX(v.slice(-1))} label="X Axis:" accept={(v) => !v.isString} />
    </AnalysisFrame>
  )
}

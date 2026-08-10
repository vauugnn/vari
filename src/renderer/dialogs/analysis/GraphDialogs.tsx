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

export function BoxplotDialog({ variables, onClose }: Props): JSX.Element {
  const [dep, setDep] = useState<string[]>([])
  const [grp, setGrp] = useState<string[]>([])
  const syntax = () => (grp[0] ? `GRAPH\n  /BOXPLOT=${dep[0]} BY ${grp[0]}.` : `GRAPH\n  /BOXPLOT=${dep.join(' ')}.`)
  return (
    <AnalysisFrame title="Boxplot" onOk={() => { void window.spss.execute(syntax()); onClose() }} onPaste={() => { window.spss.paste(syntax()); onClose() }} onReset={() => { setDep([]); setGrp([]) }} onCancel={onClose} okDisabled={dep.length === 0}>
      <VarMover variables={variables} value={dep} onChange={setDep} label="Variable(s):" accept={(v) => !v.isString} />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={grp} onChange={(v) => setGrp(v.slice(-1))} label="Category Axis (optional):" />
    </AnalysisFrame>
  )
}

export function HighLowDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const syntax = () => `GRAPH\n  /HILO=${vars.join(' ')}.`
  return (
    <AnalysisFrame title="High-Low" onOk={() => { void window.spss.execute(syntax()); onClose() }} onPaste={() => { window.spss.paste(syntax()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={vars.length < 2}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="High, Low[, Close]:" accept={(v) => !v.isString} />
    </AnalysisFrame>
  )
}

export function PyramidDialog({ variables, onClose }: Props): JSX.Element {
  const [cat, setCat] = useState<string[]>([])
  const [split, setSplit] = useState<string[]>([])
  const syntax = () => `GRAPH\n  /PYRAMID=${cat[0]} BY ${split[0]}.`
  return (
    <AnalysisFrame title="Population Pyramid" onOk={() => { void window.spss.execute(syntax()); onClose() }} onPaste={() => { window.spss.paste(syntax()); onClose() }} onReset={() => { setCat([]); setSplit([]) }} onCancel={onClose} okDisabled={!cat.length || !split.length}>
      <VarMover variables={variables} value={cat} onChange={(v) => setCat(v.slice(-1))} label="Show Distribution over:" />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={split} onChange={(v) => setSplit(v.slice(-1))} label="Split by:" />
    </AnalysisFrame>
  )
}

export function Bar3dDialog({ variables, onClose }: Props): JSX.Element {
  const [row, setRow] = useState<string[]>([])
  const [col, setCol] = useState<string[]>([])
  const syntax = () => `GRAPH\n  /BAR3D=${row[0]} BY ${col[0]}.`
  return (
    <AnalysisFrame title="3-D Bar" onOk={() => { void window.spss.execute(syntax()); onClose() }} onPaste={() => { window.spss.paste(syntax()); onClose() }} onReset={() => { setRow([]); setCol([]) }} onCancel={onClose} okDisabled={!row.length || !col.length}>
      <VarMover variables={variables} value={row} onChange={(v) => setRow(v.slice(-1))} label="X Category Axis:" />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={col} onChange={(v) => setCol(v.slice(-1))} label="Z Category Axis:" />
    </AnalysisFrame>
  )
}

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

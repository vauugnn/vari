import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

type Props = { variables: VariableMetaJson[]; onClose: () => void }

function frame(title: string, syntax: () => string, disabled: boolean, onClose: () => void, body: JSX.Element, reset: () => void) {
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
      onReset={reset}
      onCancel={onClose}
      okDisabled={disabled}
    >
      {body}
    </AnalysisFrame>
  )
}

export function SelectCasesDialog({ onClose }: Props): JSX.Element {
  const [cond, setCond] = useState('')
  const [mode, setMode] = useState<'filter' | 'delete'>('filter')
  const syntax = () =>
    mode === 'filter'
      ? `COMPUTE filter_$ = (${cond}).\nFILTER BY filter_$.`
      : `SELECT IF (${cond}).`
  return frame(
    'Select Cases',
    syntax,
    !cond.trim(),
    onClose,
    <div>
      <div>If condition is satisfied:</div>
      <textarea
        value={cond}
        onChange={(e) => setCond(e.target.value)}
        spellCheck={false}
        style={{ width: '100%', height: 60, fontFamily: 'Menlo, monospace', fontSize: 12, resize: 'none' }}
      />
      <div className="radio-block" style={{ marginTop: 6 }}>
        <label>
          <input type="radio" checked={mode === 'filter'} onChange={() => setMode('filter')} /> Filter out unselected cases
        </label>
        <label>
          <input type="radio" checked={mode === 'delete'} onChange={() => setMode('delete')} /> Delete unselected cases
        </label>
      </div>
    </div>,
    () => setCond('')
  )
}

export function WeightCasesDialog({ variables, onClose }: Props): JSX.Element {
  const [wv, setWv] = useState<string[]>([])
  const [on, setOn] = useState(true)
  const syntax = () => (on && wv[0] ? `WEIGHT BY ${wv[0]}.` : `WEIGHT OFF.`)
  return frame(
    'Weight Cases',
    syntax,
    on && wv.length === 0,
    onClose,
    <div>
      <div className="radio-block" style={{ marginBottom: 6 }}>
        <label>
          <input type="radio" checked={!on} onChange={() => setOn(false)} /> Do not weight cases
        </label>
        <label>
          <input type="radio" checked={on} onChange={() => setOn(true)} /> Weight cases by
        </label>
      </div>
      <VarMover variables={variables} value={wv} onChange={(v) => setWv(v.slice(-1))} label="Frequency Variable:" accept={(v) => !v.isString} />
    </div>,
    () => setWv([])
  )
}

export function SplitFileDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [on, setOn] = useState(true)
  const syntax = () => (on && vars.length ? `SORT CASES BY ${vars.join(' ')}.\nSPLIT FILE LAYERED BY ${vars.join(' ')}.` : `SPLIT FILE OFF.`)
  return frame(
    'Split File',
    syntax,
    on && vars.length === 0,
    onClose,
    <div>
      <div className="radio-block" style={{ marginBottom: 6 }}>
        <label>
          <input type="radio" checked={!on} onChange={() => setOn(false)} /> Analyze all cases, do not create groups
        </label>
        <label>
          <input type="radio" checked={on} onChange={() => setOn(true)} /> Compare / organize output by groups
        </label>
      </div>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Groups Based on:" />
    </div>,
    () => setVars([])
  )
}

export function SortCasesDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [asc, setAsc] = useState(true)
  const syntax = () => `SORT CASES BY ${vars.join(' ')} (${asc ? 'A' : 'D'}).`
  return frame(
    'Sort Cases',
    syntax,
    vars.length === 0,
    onClose,
    <div>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Sort by:" />
      <div className="radio-block" style={{ marginTop: 6 }}>
        <label>
          <input type="radio" checked={asc} onChange={() => setAsc(true)} /> Ascending
        </label>
        <label>
          <input type="radio" checked={!asc} onChange={() => setAsc(false)} /> Descending
        </label>
      </div>
    </div>,
    () => setVars([])
  )
}

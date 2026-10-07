import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'
import { MeasureIcon } from '../../common/icons'

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

type SelectMode = 'all' | 'if' | 'sample' | 'range' | 'filtervar'
type SelectOutput = 'filter' | 'copy' | 'delete'

const sq = (text: string): string => text.replace(/'/g, "''")

// Select Cases, as in SPSS: choose how cases are picked, then what happens to the rest.
export function SelectCasesDialog({ variables, onClose }: Props): JSX.Element {
  const [mode, setMode] = useState<SelectMode>('if')
  const [cond, setCond] = useState('')
  const [exact, setExact] = useState(false)
  const [pct, setPct] = useState('10')
  const [n, setN] = useState('')
  const [m, setM] = useState('')
  const [first, setFirst] = useState('1')
  const [last, setLast] = useState('')
  const [fvar, setFvar] = useState('')
  const [out, setOut] = useState<SelectOutput>('filter')
  const [copyName, setCopyName] = useState('Selected')

  const num = (t: string): number => (t.trim() === '' ? NaN : Number(t))
  // The condition that keeps a case, in a form usable by SELECT IF (delete / copy output).
  const keepCond = (): string =>
    mode === 'if'
      ? cond.trim()
      : mode === 'range'
        ? `$CASENUM >= ${first} & $CASENUM <= ${last}`
        : `${fvar} ~= 0 & ~MISSING(${fvar})`

  const problem = (): string => {
    if (mode === 'if' && !cond.trim()) return 'Enter a condition.'
    if (mode === 'sample') {
      if (!exact && !(num(pct) > 0 && num(pct) < 100)) return 'Enter a percentage between 0 and 100.'
      if (exact && !(num(n) > 0 && num(m) >= num(n))) return 'Enter how many cases, out of at least that many.'
      if (exact && out === 'filter') return 'An exact sample can be copied or deleted, not filtered.'
    }
    if (mode === 'range' && !(num(first) >= 1 && num(last) >= num(first))) return 'Enter a valid first and last case.'
    if (mode === 'filtervar' && !fvar) return 'Pick a filter variable.'
    if (mode !== 'all' && out === 'copy' && !/^[A-Za-z@#$][\w@#$.]*$/.test(copyName)) return 'Enter a valid dataset name.'
    return ''
  }

  const syntax = (): string => {
    if (mode === 'all') return 'USE ALL.'
    const lines: string[] = []
    if (out === 'copy') {
      lines.push(`DATASET COPY ${copyName}.`, `DATASET ACTIVATE ${copyName}.`, 'FILTER OFF.', 'USE ALL.')
    }
    if (out === 'filter') {
      lines.push('USE ALL.')
      if (mode === 'range') {
        lines.push(`USE ${first} THRU ${last}.`)
      } else if (mode === 'filtervar') {
        lines.push(`FILTER BY ${fvar}.`)
      } else {
        const test = mode === 'if' ? cond.trim() : `UNIFORM(1) <= ${Number(pct) / 100}`
        const label = mode === 'if' ? `${cond.trim()} (FILTER)` : `Approximately ${pct}% of the cases (SAMPLE)`
        lines.push(
          `COMPUTE filter_$=(${test}).`,
          `VARIABLE LABELS filter_$ '${sq(label)}'.`,
          "VALUE LABELS filter_$ 0 'Not Selected' 1 'Selected'.",
          'FORMATS filter_$ (f1.0).',
          'FILTER BY filter_$.'
        )
      }
    } else if (mode === 'sample') {
      lines.push(exact ? `SAMPLE ${n} FROM ${m}.` : `SAMPLE ${Number(pct) / 100}.`)
    } else {
      lines.push(`SELECT IF (${keepCond()}).`)
    }
    lines.push('EXECUTE.')
    return lines.join('\n')
  }

  const err = problem()
  const radio = (value: SelectMode, label: string, extra?: JSX.Element): JSX.Element => (
    <div className="sc-opt">
      <label>
        <input type="radio" name="sc-mode" checked={mode === value} onChange={() => setMode(value)} /> {label}
      </label>
      {mode === value && extra && <div className="sc-sub">{extra}</div>}
    </div>
  )
  const field = (value: string, set: (v: string) => void, width = 64): JSX.Element => (
    <input type="text" value={value} style={{ width }} onChange={(e) => set(e.target.value)} />
  )

  return frame(
    'Select Cases',
    syntax,
    !!err,
    onClose,
    <div className="sc">
      <div className="sc-vars">
        <div className="sc-head">Variables</div>
        <div className="sc-list">
          {variables.map((v) => (
            <div
              key={v.name}
              className={'vm-item' + (mode === 'filtervar' && fvar === v.name ? ' vm-item--sel' : '')}
              title="Double-click to use"
              onClick={() => mode === 'filtervar' && setFvar(v.name)}
              onDoubleClick={() => {
                if (mode === 'if') setCond((c) => (c ? `${c} ${v.name}` : v.name))
                else if (mode === 'filtervar') setFvar(v.name)
              }}
            >
              <MeasureIcon measure={v.measure} isString={v.isString} isDate={v.type === 'Date'} size={14} />
              <span className="vm-name">{v.label || v.name}</span>
              <span className="vm-varname">[{v.name}]</span>
            </div>
          ))}
        </div>
      </div>
      <div className="sc-main">
        <fieldset className="sc-group">
          <legend>Select</legend>
          {radio('all', 'All cases')}
          {radio(
            'if',
            'If condition is satisfied',
            <textarea
              value={cond}
              spellCheck={false}
              placeholder="e.g. Age >= 13 & Sex = 1"
              onChange={(e) => setCond(e.target.value)}
            />
          )}
          {radio(
            'sample',
            'Random sample of cases',
            <div className="sc-stack">
              <label>
                <input type="radio" name="sc-kind" checked={!exact} onChange={() => setExact(false)} /> Approximately{' '}
                {field(pct, setPct, 48)} % of all cases
              </label>
              <label>
                <input type="radio" name="sc-kind" checked={exact} onChange={() => setExact(true)} /> Exactly{' '}
                {field(n, setN, 56)} cases from the first {field(m, setM, 56)} cases
              </label>
            </div>
          )}
          {radio(
            'range',
            'Based on time or case range',
            <div className="sc-stack">
              <label>
                First Case: {field(first, setFirst)}
              </label>
              <label>
                Last Case: {field(last, setLast)}
              </label>
            </div>
          )}
          {radio(
            'filtervar',
            'Use filter variable',
            <div className="sc-fvar">{fvar ? `${fvar}` : 'Click a variable in the list'}</div>
          )}
        </fieldset>
        <fieldset className="sc-group" disabled={mode === 'all'}>
          <legend>Output</legend>
          <label>
            <input type="radio" name="sc-out" checked={out === 'filter'} onChange={() => setOut('filter')} /> Filter out unselected cases
          </label>
          <label>
            <input type="radio" name="sc-out" checked={out === 'copy'} onChange={() => setOut('copy')} /> Copy selected cases to a new dataset
          </label>
          {out === 'copy' && (
            <div className="sc-sub">
              Dataset name: <input type="text" value={copyName} style={{ width: 140 }} onChange={(e) => setCopyName(e.target.value)} />
            </div>
          )}
          <label>
            <input type="radio" name="sc-out" checked={out === 'delete'} onChange={() => setOut('delete')} /> Delete unselected cases
          </label>
        </fieldset>
        <div className="sc-status">{err ? err : mode === 'all' ? 'Current Status: Do not filter cases' : ' '}</div>
      </div>
    </div>,
    () => {
      setMode('if')
      setCond('')
      setFvar('')
      setOut('filter')
    }
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

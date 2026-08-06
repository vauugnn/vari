import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

type Props = { variables: VariableMetaJson[]; onClose: () => void }

function useRun(onClose: () => void) {
  return (syntax: string) => {
    void window.spss.execute(syntax)
    onClose()
  }
}

function checkRow(set: Set<string>, k: string, upd: (s: Set<string>) => void, label: string) {
  return (
    <label key={k}>
      <input
        type="checkbox"
        checked={set.has(k)}
        onChange={(e) => {
          const n = new Set(set)
          if (e.target.checked) n.add(k)
          else n.delete(k)
          upd(n)
        }}
      />
      {label}
    </label>
  )
}

export function ChiSquareDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const run = useRun(onClose)
  const s = () => `NPAR TESTS\n  /CHISQUARE=${vars.join(' ')}.`
  return (
    <AnalysisFrame title="Chi-square Test" onOk={() => run(s())} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={!vars.length}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Test Variable List:" />
    </AnalysisFrame>
  )
}

export function BinomialDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const run = useRun(onClose)
  const s = () => `NPAR TESTS\n  /BINOMIAL(0.5)=${vars.join(' ')}.`
  return (
    <AnalysisFrame title="Binomial Test" onOk={() => run(s())} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={!vars.length}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Test Variable List:" />
    </AnalysisFrame>
  )
}

export function RunsDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const run = useRun(onClose)
  const s = () => `NPAR TESTS\n  /RUNS(MEDIAN)=${vars.join(' ')}.`
  return (
    <AnalysisFrame title="Runs Test" onOk={() => run(s())} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={!vars.length}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Test Variable List:" accept={(v) => !v.isString} />
    </AnalysisFrame>
  )
}

export function OneSampleKSDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const run = useRun(onClose)
  const s = () => `NPAR TESTS\n  /K-S(NORMAL)=${vars.join(' ')}.`
  return (
    <AnalysisFrame title="One-Sample Kolmogorov-Smirnov Test" onOk={() => run(s())} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={!vars.length}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Test Variable List:" accept={(v) => !v.isString} />
    </AnalysisFrame>
  )
}

export function TwoIndependentDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [grp, setGrp] = useState<string[]>([])
  const [g1, setG1] = useState('1')
  const [g2, setG2] = useState('2')
  const [tests, setTests] = useState<Set<string>>(new Set(['M-W']))
  const run = useRun(onClose)
  const s = () => {
    const lines = [...tests].map((tk) => `  /${tk}=${vars.join(' ')} BY ${grp[0]}(${g1} ${g2})`)
    return `NPAR TESTS\n${lines.join('\n')}.`
  }
  return (
    <AnalysisFrame title="Two-Independent-Samples Tests" onOk={() => run(s())} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setVars([]); setGrp([]) }} onCancel={onClose} okDisabled={!vars.length || !grp.length || tests.size === 0}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Test Variable List:" accept={(v) => !v.isString} />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={grp} onChange={(v) => setGrp(v.slice(-1))} label="Grouping Variable:" />
      <div className="field-row"><span>Group 1:</span><input value={g1} onChange={(e) => setG1(e.target.value)} style={{ width: 50 }} /><span>Group 2:</span><input value={g2} onChange={(e) => setG2(e.target.value)} style={{ width: 50 }} /></div>
      <fieldset className="opts"><legend>Test Type</legend>{checkRow(tests, 'M-W', setTests, 'Mann-Whitney U')}{checkRow(tests, 'K-S', setTests, 'Kolmogorov-Smirnov Z')}</fieldset>
    </AnalysisFrame>
  )
}

export function KIndependentDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [grp, setGrp] = useState<string[]>([])
  const [lo, setLo] = useState('1')
  const [hi, setHi] = useState('3')
  const run = useRun(onClose)
  const s = () => `NPAR TESTS\n  /K-W=${vars.join(' ')} BY ${grp[0]}(${lo} ${hi}).`
  return (
    <AnalysisFrame title="Tests for Several Independent Samples" onOk={() => run(s())} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setVars([]); setGrp([]) }} onCancel={onClose} okDisabled={!vars.length || !grp.length}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Test Variable List:" accept={(v) => !v.isString} />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={grp} onChange={(v) => setGrp(v.slice(-1))} label="Grouping Variable:" />
      <div className="field-row"><span>Range Min:</span><input value={lo} onChange={(e) => setLo(e.target.value)} style={{ width: 50 }} /><span>Max:</span><input value={hi} onChange={(e) => setHi(e.target.value)} style={{ width: 50 }} /></div>
    </AnalysisFrame>
  )
}

export function TwoRelatedDialog({ variables, onClose }: Props): JSX.Element {
  const [v1, setV1] = useState<string[]>([])
  const [v2, setV2] = useState<string[]>([])
  const [tests, setTests] = useState<Set<string>>(new Set(['WILCOXON']))
  const run = useRun(onClose)
  const n = Math.min(v1.length, v2.length)
  const s = () => {
    const lines = [...tests].map((tk) => `  /${tk}=${v1.slice(0, n).join(' ')} WITH ${v2.slice(0, n).join(' ')}`)
    return `NPAR TESTS\n${lines.join('\n')}.`
  }
  return (
    <AnalysisFrame title="Two-Related-Samples Tests" onOk={() => run(s())} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setV1([]); setV2([]) }} onCancel={onClose} okDisabled={n === 0 || tests.size === 0}>
      <div style={{ display: 'flex', gap: 10 }}>
        <div style={{ flex: 1 }}><VarMover variables={variables} value={v1} onChange={setV1} label="Variable 1:" accept={(v) => !v.isString} /></div>
        <div style={{ flex: 1 }}><VarMover variables={variables} value={v2} onChange={setV2} label="Variable 2:" accept={(v) => !v.isString} /></div>
      </div>
      <fieldset className="opts"><legend>Test Type</legend>{checkRow(tests, 'WILCOXON', setTests, 'Wilcoxon')}{checkRow(tests, 'SIGN', setTests, 'Sign')}{checkRow(tests, 'MCNEMAR', setTests, 'McNemar')}</fieldset>
    </AnalysisFrame>
  )
}

export function KRelatedDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [tests, setTests] = useState<Set<string>>(new Set(['FRIEDMAN']))
  const run = useRun(onClose)
  const s = () => {
    const lines = [...tests].map((tk) => `  /${tk}=${vars.join(' ')}`)
    return `NPAR TESTS\n${lines.join('\n')}.`
  }
  return (
    <AnalysisFrame title="Tests for Several Related Samples" onOk={() => run(s())} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setVars([])} onCancel={onClose} okDisabled={vars.length < 2 || tests.size === 0}>
      <VarMover variables={variables} value={vars} onChange={setVars} label="Test Variables:" accept={(v) => !v.isString} />
      <fieldset className="opts"><legend>Test Type</legend>{checkRow(tests, 'FRIEDMAN', setTests, 'Friedman')}{checkRow(tests, 'KENDALL', setTests, "Kendall's W")}{checkRow(tests, 'COCHRAN', setTests, "Cochran's Q")}</fieldset>
    </AnalysisFrame>
  )
}

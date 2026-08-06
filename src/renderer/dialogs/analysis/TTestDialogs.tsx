import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

type Props = { variables: VariableMetaJson[]; onClose: () => void }

function run(syntax: string, onClose: () => void): void {
  void window.spss.execute(syntax)
  onClose()
}

export function OneSampleTTestDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [testVal, setTestVal] = useState('0')
  const syntax = (): string => `T-TEST\n  /TESTVAL=${testVal || 0}\n  /VARIABLES=${vars.join(' ')}.`
  return (
    <AnalysisFrame
      title="One-Sample T Test"
      onOk={() => run(syntax(), onClose)}
      onPaste={() => {
        window.spss.paste(syntax())
        onClose()
      }}
      onReset={() => {
        setVars([])
        setTestVal('0')
      }}
      onCancel={onClose}
      okDisabled={vars.length === 0}
    >
      <VarMover variables={variables} value={vars} onChange={setVars} label="Test Variable(s):" accept={(v) => !v.isString} />
      <div className="field-row" style={{ marginTop: 8 }}>
        <span>Test Value:</span>
        <input type="text" value={testVal} onChange={(e) => setTestVal(e.target.value)} style={{ width: 90 }} />
      </div>
    </AnalysisFrame>
  )
}

export function IndependentTTestDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [group, setGroup] = useState<string[]>([])
  const [g1, setG1] = useState('1')
  const [g2, setG2] = useState('2')
  const gv = group[0]
  const syntax = (): string =>
    `T-TEST GROUPS=${gv}(${g1} ${g2})\n  /VARIABLES=${vars.join(' ')}.`
  return (
    <AnalysisFrame
      title="Independent-Samples T Test"
      onOk={() => run(syntax(), onClose)}
      onPaste={() => {
        window.spss.paste(syntax())
        onClose()
      }}
      onReset={() => {
        setVars([])
        setGroup([])
      }}
      onCancel={onClose}
      okDisabled={vars.length === 0 || !gv}
    >
      <VarMover variables={variables} value={vars} onChange={setVars} label="Test Variable(s):" accept={(v) => !v.isString} />
      <div style={{ height: 8 }} />
      <VarMover variables={variables} value={group} onChange={(v) => setGroup(v.slice(-1))} label="Grouping Variable:" />
      <div className="field-row" style={{ marginTop: 6 }}>
        <span>Group 1:</span>
        <input type="text" value={g1} onChange={(e) => setG1(e.target.value)} style={{ width: 60 }} />
        <span>Group 2:</span>
        <input type="text" value={g2} onChange={(e) => setG2(e.target.value)} style={{ width: 60 }} />
      </div>
    </AnalysisFrame>
  )
}

export function PairedTTestDialog({ variables, onClose }: Props): JSX.Element {
  const [v1, setV1] = useState<string[]>([])
  const [v2, setV2] = useState<string[]>([])
  const n = Math.min(v1.length, v2.length)
  const syntax = (): string =>
    `T-TEST\n  /PAIRS=${v1.slice(0, n).join(' ')} WITH ${v2.slice(0, n).join(' ')} (PAIRED).`
  return (
    <AnalysisFrame
      title="Paired-Samples T Test"
      onOk={() => run(syntax(), onClose)}
      onPaste={() => {
        window.spss.paste(syntax())
        onClose()
      }}
      onReset={() => {
        setV1([])
        setV2([])
      }}
      onCancel={onClose}
      okDisabled={n === 0}
    >
      <div style={{ display: 'flex', gap: 10 }}>
        <div style={{ flex: 1 }}>
          <VarMover variables={variables} value={v1} onChange={setV1} label="Variable 1:" accept={(v) => !v.isString} />
        </div>
        <div style={{ flex: 1 }}>
          <VarMover variables={variables} value={v2} onChange={setV2} label="Variable 2:" accept={(v) => !v.isString} />
        </div>
      </div>
    </AnalysisFrame>
  )
}

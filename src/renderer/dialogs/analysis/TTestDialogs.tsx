import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'
import { Modal } from '../Modal'

type Props = { variables: VariableMetaJson[]; onClose: () => void }

function run(syntax: string, onClose: () => void): void {
  void window.spss.execute(syntax)
  onClose()
}

// Shared Options sub-dialog: confidence-interval percentage (maps to
// /CRITERIA=CI(fraction), honored by the T-TEST procedure).
function OptionsModal({ ci, setCi, onClose }: { ci: string; setCi: (v: string) => void; onClose: () => void }): JSX.Element {
  return (
    <Modal title="T Test: Options" onOk={onClose} onCancel={onClose}>
      <div className="field-row">
        <span>Confidence Interval Percentage:</span>
        <input type="number" min={50} max={99.9} value={ci} onChange={(e) => setCi(e.target.value)} style={{ width: 70 }} /> %
      </div>
    </Modal>
  )
}

function criteria(ci: string): string {
  const pct = parseFloat(ci)
  return pct && pct !== 95 ? `\n  /CRITERIA=CI(${(pct / 100).toFixed(4)})` : ''
}

export function OneSampleTTestDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [testVal, setTestVal] = useState('0')
  const [ci, setCi] = useState('95')
  const [opts, setOpts] = useState(false)
  const syntax = (): string => `T-TEST\n  /TESTVAL=${testVal || 0}${criteria(ci)}\n  /VARIABLES=${vars.join(' ')}.`
  return (
    <>
      <AnalysisFrame
        title="One-Sample T Test"
        onOk={() => run(syntax(), onClose)}
        onPaste={() => { window.spss.paste(syntax()); onClose() }}
        onReset={() => { setVars([]); setTestVal('0') }}
        onCancel={onClose}
        okDisabled={vars.length === 0}
        subButtons={[{ label: 'Options…', onClick: () => setOpts(true) }]}
      >
        <VarMover variables={variables} value={vars} onChange={setVars} label="Test Variable(s):" accept={(v) => !v.isString} />
        <div className="field-row" style={{ marginTop: 8 }}>
          <span>Test Value:</span>
          <input type="text" value={testVal} onChange={(e) => setTestVal(e.target.value)} style={{ width: 90 }} />
        </div>
      </AnalysisFrame>
      {opts && <OptionsModal ci={ci} setCi={setCi} onClose={() => setOpts(false)} />}
    </>
  )
}

export function IndependentTTestDialog({ variables, onClose }: Props): JSX.Element {
  const [vars, setVars] = useState<string[]>([])
  const [group, setGroup] = useState<string[]>([])
  const [g1, setG1] = useState('1')
  const [g2, setG2] = useState('2')
  const [ci, setCi] = useState('95')
  const [opts, setOpts] = useState(false)
  const gv = group[0]
  const syntax = (): string => `T-TEST GROUPS=${gv}(${g1} ${g2})${criteria(ci)}\n  /VARIABLES=${vars.join(' ')}.`
  return (
    <>
      <AnalysisFrame
        title="Independent-Samples T Test"
        onOk={() => run(syntax(), onClose)}
        onPaste={() => { window.spss.paste(syntax()); onClose() }}
        onReset={() => { setVars([]); setGroup([]) }}
        onCancel={onClose}
        okDisabled={vars.length === 0 || !gv}
        subButtons={[{ label: 'Options…', onClick: () => setOpts(true) }]}
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
      {opts && <OptionsModal ci={ci} setCi={setCi} onClose={() => setOpts(false)} />}
    </>
  )
}

export function PairedTTestDialog({ variables, onClose }: Props): JSX.Element {
  const [v1, setV1] = useState<string[]>([])
  const [v2, setV2] = useState<string[]>([])
  const [ci, setCi] = useState('95')
  const [opts, setOpts] = useState(false)
  const n = Math.min(v1.length, v2.length)
  const syntax = (): string =>
    `T-TEST\n  /PAIRS=${v1.slice(0, n).join(' ')} WITH ${v2.slice(0, n).join(' ')} (PAIRED)${criteria(ci)}.`
  return (
    <>
      <AnalysisFrame
        title="Paired-Samples T Test"
        onOk={() => run(syntax(), onClose)}
        onPaste={() => { window.spss.paste(syntax()); onClose() }}
        onReset={() => { setV1([]); setV2([]) }}
        onCancel={onClose}
        okDisabled={n === 0}
        subButtons={[{ label: 'Options…', onClick: () => setOpts(true) }]}
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
      {opts && <OptionsModal ci={ci} setCi={setCi} onClose={() => setOpts(false)} />}
    </>
  )
}

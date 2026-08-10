import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

type Props = { variables: VariableMetaJson[]; onClose: () => void }
const num = (v: VariableMetaJson) => !v.isString

function go(s: string, onClose: () => void) {
  void window.spss.execute(s)
  onClose()
}

function StatusRow({ value, onChange, event, onEvent, variables }: {
  value: string[]; onChange: (v: string[]) => void; event: string; onEvent: (e: string) => void; variables: VariableMetaJson[]
}) {
  return (
    <>
      <VarMover variables={variables} value={value} onChange={(v) => onChange(v.slice(-1))} label="Status Variable:" />
      <div className="field-row"><span>Event value:</span><input value={event} onChange={(e) => onEvent(e.target.value)} style={{ width: 60 }} /></div>
    </>
  )
}

export function KaplanMeierDialog({ variables, onClose }: Props): JSX.Element {
  const [time, setTime] = useState<string[]>([])
  const [factor, setFactor] = useState<string[]>([])
  const [status, setStatus] = useState<string[]>([])
  const [event, setEvent] = useState('1')
  const s = () => `KM ${time[0]}${factor[0] ? ' BY ' + factor[0] : ''}\n  /STATUS=${status[0]}(${event}).`
  return (
    <AnalysisFrame title="Kaplan-Meier" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setTime([]); setFactor([]); setStatus([]) }} onCancel={onClose} okDisabled={!time.length || !status.length}>
      <VarMover variables={variables} value={time} onChange={(v) => setTime(v.slice(-1))} label="Time:" accept={num} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={factor} onChange={(v) => setFactor(v.slice(-1))} label="Factor (optional):" />
      <div style={{ height: 6 }} />
      <StatusRow value={status} onChange={setStatus} event={event} onEvent={setEvent} variables={variables} />
    </AnalysisFrame>
  )
}

export function CoxDialog({ variables, onClose }: Props): JSX.Element {
  const [time, setTime] = useState<string[]>([])
  const [covars, setCovars] = useState<string[]>([])
  const [status, setStatus] = useState<string[]>([])
  const [event, setEvent] = useState('1')
  const s = () => `COXREG ${time[0]} WITH ${covars.join(' ')}\n  /STATUS=${status[0]}(${event}).`
  return (
    <AnalysisFrame title="Cox Regression" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setTime([]); setCovars([]); setStatus([]) }} onCancel={onClose} okDisabled={!time.length || !covars.length || !status.length}>
      <VarMover variables={variables} value={time} onChange={(v) => setTime(v.slice(-1))} label="Time:" accept={num} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={covars} onChange={setCovars} label="Covariates:" accept={num} />
      <div style={{ height: 6 }} />
      <StatusRow value={status} onChange={setStatus} event={event} onEvent={setEvent} variables={variables} />
    </AnalysisFrame>
  )
}

export function LifeTableDialog({ variables, onClose }: Props): JSX.Element {
  const [time, setTime] = useState<string[]>([])
  const [status, setStatus] = useState<string[]>([])
  const [event, setEvent] = useState('1')
  const [hi, setHi] = useState('50')
  const [by, setBy] = useState('5')
  const s = () => `SURVIVAL TABLE=${time[0]}\n  /INTERVAL=THRU ${hi} BY ${by}\n  /STATUS=${status[0]}(${event}).`
  return (
    <AnalysisFrame title="Life Tables" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setTime([]); setStatus([]) }} onCancel={onClose} okDisabled={!time.length || !status.length}>
      <VarMover variables={variables} value={time} onChange={(v) => setTime(v.slice(-1))} label="Time:" accept={num} />
      <div className="field-row"><span>Display Time Intervals 0 to:</span><input value={hi} onChange={(e) => setHi(e.target.value)} style={{ width: 60 }} /><span>by</span><input value={by} onChange={(e) => setBy(e.target.value)} style={{ width: 50 }} /></div>
      <StatusRow value={status} onChange={setStatus} event={event} onEvent={setEvent} variables={variables} />
    </AnalysisFrame>
  )
}

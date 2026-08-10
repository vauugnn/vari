import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'

type Props = { variables: VariableMetaJson[]; onClose: () => void }
const num = (v: VariableMetaJson) => !v.isString

function go(syntax: string, onClose: () => void) {
  void window.spss.execute(syntax)
  onClose()
}

const DISTS = ['NORMAL', 'POISSON', 'BINOMIAL', 'GAMMA']
const LINKS = ['IDENTITY', 'LOG', 'LOGIT', 'INVERSE']

function rhs(factors: string[], covars: string[]): string {
  const parts: string[] = []
  if (factors.length) parts.push('BY ' + factors.join(' '))
  if (covars.length) parts.push('WITH ' + covars.join(' '))
  return parts.join(' ')
}

export function GenlinDialog({ variables, onClose }: Props): JSX.Element {
  const [dep, setDep] = useState<string[]>([])
  const [factors, setFactors] = useState<string[]>([])
  const [covars, setCovars] = useState<string[]>([])
  const [dist, setDist] = useState('NORMAL')
  const [link, setLink] = useState('IDENTITY')
  const s = () => `GENLIN ${dep[0]} ${rhs(factors, covars)}\n  /MODEL DISTRIBUTION=${dist} LINK=${link}.`
  return (
    <AnalysisFrame title="Generalized Linear Models" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setDep([]); setFactors([]); setCovars([]) }} onCancel={onClose} okDisabled={!dep.length}>
      <VarMover variables={variables} value={dep} onChange={(v) => setDep(v.slice(-1))} label="Dependent:" accept={num} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={factors} onChange={setFactors} label="Factors:" />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={covars} onChange={setCovars} label="Covariates:" accept={num} />
      <div className="field-row" style={{ marginTop: 6 }}>
        <span>Distribution:</span>
        <select value={dist} onChange={(e) => setDist(e.target.value)}>{DISTS.map((d) => <option key={d}>{d}</option>)}</select>
        <span>Link:</span>
        <select value={link} onChange={(e) => setLink(e.target.value)}>{LINKS.map((l) => <option key={l}>{l}</option>)}</select>
      </div>
    </AnalysisFrame>
  )
}

export function GeeDialog({ variables, onClose }: Props): JSX.Element {
  const [dep, setDep] = useState<string[]>([])
  const [subject, setSubject] = useState<string[]>([])
  const [covars, setCovars] = useState<string[]>([])
  const [dist, setDist] = useState('NORMAL')
  const [link, setLink] = useState('IDENTITY')
  const s = () => `GEE ${dep[0]} WITH ${covars.join(' ')}\n  /SUBJECT=${subject[0]}\n  /MODEL DISTRIBUTION=${dist} LINK=${link}.`
  return (
    <AnalysisFrame title="Generalized Estimating Equations" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setDep([]); setSubject([]); setCovars([]) }} onCancel={onClose} okDisabled={!dep.length || !subject.length || !covars.length}>
      <VarMover variables={variables} value={dep} onChange={(v) => setDep(v.slice(-1))} label="Dependent:" accept={num} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={subject} onChange={(v) => setSubject(v.slice(-1))} label="Subject Variable:" />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={covars} onChange={setCovars} label="Covariates:" accept={num} />
      <div className="field-row" style={{ marginTop: 6 }}>
        <span>Distribution:</span>
        <select value={dist} onChange={(e) => setDist(e.target.value)}>{DISTS.map((d) => <option key={d}>{d}</option>)}</select>
        <span>Link:</span>
        <select value={link} onChange={(e) => setLink(e.target.value)}>{LINKS.map((l) => <option key={l}>{l}</option>)}</select>
      </div>
    </AnalysisFrame>
  )
}

export function MixedDialog({ variables, onClose }: Props): JSX.Element {
  const [dep, setDep] = useState<string[]>([])
  const [subject, setSubject] = useState<string[]>([])
  const [covars, setCovars] = useState<string[]>([])
  const s = () => `MIXED ${dep[0]} WITH ${covars.join(' ')}\n  /RANDOM=${subject[0]}.`
  return (
    <AnalysisFrame title="Linear Mixed Models" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => { setDep([]); setSubject([]); setCovars([]) }} onCancel={onClose} okDisabled={!dep.length || !subject.length || !covars.length}>
      <VarMover variables={variables} value={dep} onChange={(v) => setDep(v.slice(-1))} label="Dependent:" accept={num} />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={subject} onChange={(v) => setSubject(v.slice(-1))} label="Subject (random):" />
      <div style={{ height: 6 }} />
      <VarMover variables={variables} value={covars} onChange={setCovars} label="Covariates (fixed):" accept={num} />
    </AnalysisFrame>
  )
}

export function GenlogDialog({ variables, onClose }: Props): JSX.Element {
  const [factors, setFactors] = useState<string[]>([])
  const s = () => `GENLOG ${factors.join(' ')}.`
  return (
    <AnalysisFrame title="General Loglinear Analysis" onOk={() => go(s(), onClose)} onPaste={() => { window.spss.paste(s()); onClose() }} onReset={() => setFactors([])} onCancel={onClose} okDisabled={factors.length < 2}>
      <VarMover variables={variables} value={factors} onChange={setFactors} label="Factors (2+):" />
    </AnalysisFrame>
  )
}

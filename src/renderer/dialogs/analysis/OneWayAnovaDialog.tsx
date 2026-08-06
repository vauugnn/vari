import { useState } from 'react'
import type { VariableMetaJson } from '../../../shared/types'
import { AnalysisFrame } from './AnalysisFrame'
import { VarMover } from './VarMover'
import { Modal } from '../Modal'

const POSTHOC: [string, string][] = [
  ['LSD', 'LSD'],
  ['BONFERRONI', 'Bonferroni'],
  ['SIDAK', 'Sidak'],
  ['SCHEFFE', 'Scheffe'],
  ['TUKEY', 'Tukey'],
  ['GH', 'Games-Howell']
]

export function OneWayAnovaDialog({
  variables,
  onClose
}: {
  variables: VariableMetaJson[]
  onClose: () => void
}): JSX.Element {
  const [deps, setDeps] = useState<string[]>([])
  const [factor, setFactor] = useState<string[]>([])
  const [ph, setPh] = useState<Set<string>>(new Set())
  const [desc, setDesc] = useState(false)
  const [homog, setHomog] = useState(false)
  const [dlg, setDlg] = useState<'posthoc' | 'options' | null>(null)

  const syntax = (): string => {
    let s = `ONEWAY ${deps.join(' ')} BY ${factor[0]}`
    const stats = [desc && 'DESCRIPTIVES', homog && 'HOMOGENEITY'].filter(Boolean)
    if (stats.length) s += `\n  /STATISTICS=${stats.join(' ')}`
    const p = POSTHOC.filter(([k]) => ph.has(k)).map(([k]) => k)
    if (p.length) s += `\n  /POSTHOC=${p.join(' ')} ALPHA(0.05)`
    return s + '.'
  }
  const ok = () => {
    void window.spss.execute(syntax())
    onClose()
  }

  return (
    <>
      <AnalysisFrame
        title="One-Way ANOVA"
        onOk={ok}
        onPaste={() => {
          window.spss.paste(syntax())
          onClose()
        }}
        onReset={() => {
          setDeps([])
          setFactor([])
          setPh(new Set())
        }}
        onCancel={onClose}
        okDisabled={deps.length === 0 || factor.length === 0}
        subButtons={[
          { label: 'Post Hoc…', onClick: () => setDlg('posthoc') },
          { label: 'Options…', onClick: () => setDlg('options') }
        ]}
      >
        <VarMover variables={variables} value={deps} onChange={setDeps} label="Dependent List:" accept={(v) => !v.isString} />
        <div style={{ height: 8 }} />
        <VarMover variables={variables} value={factor} onChange={(v) => setFactor(v.slice(-1))} label="Factor:" />
      </AnalysisFrame>

      {dlg === 'posthoc' && (
        <Modal title="One-Way ANOVA: Post Hoc" onOk={() => setDlg(null)} onCancel={() => setDlg(null)}>
          <div className="stat-grid">
            {POSTHOC.map(([k, lab]) => (
              <label key={k}>
                <input
                  type="checkbox"
                  checked={ph.has(k)}
                  onChange={(e) => {
                    const n = new Set(ph)
                    if (e.target.checked) n.add(k)
                    else n.delete(k)
                    setPh(n)
                  }}
                />
                {lab}
              </label>
            ))}
          </div>
        </Modal>
      )}
      {dlg === 'options' && (
        <Modal title="One-Way ANOVA: Options" onOk={() => setDlg(null)} onCancel={() => setDlg(null)}>
          <label>
            <input type="checkbox" checked={desc} onChange={(e) => setDesc(e.target.checked)} /> Descriptive
          </label>
          <br />
          <label>
            <input type="checkbox" checked={homog} onChange={(e) => setHomog(e.target.checked)} /> Homogeneity of variance test
          </label>
        </Modal>
      )}
    </>
  )
}

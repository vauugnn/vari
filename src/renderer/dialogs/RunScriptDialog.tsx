import { useState } from 'react'
import { Modal } from './Modal'

const SAMPLE = `# Python script — the active dataset is 'df' (a pandas DataFrame).
# pandas is 'pd', numpy is 'np'. Rebinding or adding columns to df updates
# the Data Editor. Anything you print appears below.
print(df.describe())
`

// Vari's scripting surface: run Python against the active dataset. Not IBM's
// plugin API — a local convenience console.
export function RunScriptDialog({ onClose }: { onClose: () => void }): JSX.Element {
  const [code, setCode] = useState(SAMPLE)
  const [output, setOutput] = useState('')
  const [running, setRunning] = useState(false)

  const run = async () => {
    setRunning(true)
    try {
      const res = await window.spss.runScript(code)
      setOutput((res.error ? `Error: ${res.error}\n\n` : '') + (res.output || '(no output)'))
    } catch (err) {
      setOutput(String(err instanceof Error ? err.message : err))
    } finally {
      setRunning(false)
    }
  }

  return (
    <Modal title="Run Script" onOk={() => void run()} okLabel={running ? 'Running…' : 'Run'} okDisabled={running} onCancel={onClose}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, width: 520 }}>
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          spellCheck={false}
          style={{ width: '100%', height: 180, fontFamily: 'Menlo, monospace', fontSize: 12, border: '1px solid #7f9db9' }}
        />
        <div style={{ fontSize: 11, color: '#555' }}>Output:</div>
        <pre style={{ margin: 0, height: 140, overflow: 'auto', background: '#f6f6f6', border: '1px solid #d0d0d0', padding: 6, fontSize: 12, whiteSpace: 'pre-wrap' }}>
          {output}
        </pre>
      </div>
    </Modal>
  )
}

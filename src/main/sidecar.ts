import { spawn, ChildProcess } from 'child_process'
import { EventEmitter } from 'events'
import { existsSync } from 'fs'
import { join } from 'path'
import { app } from 'electron'
import type { SidecarStatus } from '../shared/types'

interface Pending {
  resolve: (value: unknown) => void
  reject: (err: Error) => void
  timer: NodeJS.Timeout
}

const REQUEST_TIMEOUT_MS = 15000
const PING_INTERVAL_MS = 200
const PING_MAX_ATTEMPTS = 150 // ~30s: a frozen build's first-run imports are slow
const RESPAWN_DELAY_MS = 800

/**
 * Supervises the Python compute sidecar.
 *
 * Responsibilities (PHASE-0 section 4):
 *  - spawn ./venv python running sidecar/server.py
 *  - JSON-RPC 2.0 request/response over newline-delimited stdio
 *  - ping() until ready before the renderer may Run
 *  - on crash: reject in-flight requests (never hang), emit 'down', respawn
 *  - killed on app quit
 *
 * Emits: 'status' (SidecarStatus).
 */
export class Sidecar extends EventEmitter {
  private proc: ChildProcess | null = null
  private buffer = ''
  private lastStderr = ''
  private nextId = 1
  private pending = new Map<number, Pending>()
  private quitting = false
  private respawnTimer: NodeJS.Timeout | null = null
  private status: SidecarStatus = { state: 'starting' }

  get currentStatus(): SidecarStatus {
    return this.status
  }

  private pythonPath(): string {
    const override = process.env.SPSS_SIDECAR_PYTHON
    if (override) return override
    const root = app.getAppPath()
    const win = process.platform === 'win32'
    return join(root, 'venv', win ? 'Scripts' : 'bin', win ? 'python.exe' : 'python')
  }

  /** In a packaged build, the sidecar is a PyInstaller binary under resources. */
  private frozenPath(): string {
    const exe = process.platform === 'win32' ? 'vari-sidecar.exe' : 'vari-sidecar'
    return join(process.resourcesPath, 'sidecar-bin', exe)
  }

  private appRoot(): string {
    return app.getAppPath()
  }

  start(): void {
    this.setStatus({ state: 'starting' })

    // Packaged: run the frozen sidecar binary. Dev: run the venv as a module.
    const frozen = this.frozenPath()
    const useFrozen = app.isPackaged && existsSync(frozen)
    const command = useFrozen ? frozen : this.pythonPath()
    const spawnArgs = useFrozen ? [] : ['-m', 'sidecar.server']

    if (!existsSync(command)) {
      this.setStatus({
        state: 'down',
        detail: app.isPackaged
          ? `Sidecar binary not found at ${frozen}. The packaged build is incomplete.`
          : `Python interpreter not found at ${command}. Create the venv (see CLAUDE.md) or set SPSS_SIDECAR_PYTHON.`
      })
      return
    }

    let proc: ChildProcess
    try {
      proc = spawn(command, spawnArgs, {
        cwd: this.appRoot(),
        stdio: ['pipe', 'pipe', 'pipe']
      })
    } catch (err) {
      this.setStatus({ state: 'down', detail: `Failed to spawn sidecar: ${String(err)}` })
      return
    }
    this.proc = proc
    this.buffer = ''
    this.lastStderr = ''

    proc.stdout?.setEncoding('utf8')
    proc.stdout?.on('data', (chunk: string) => this.onStdout(chunk))
    proc.stderr?.setEncoding('utf8')
    proc.stderr?.on('data', (chunk: string) => {
      // Keep the tail so a crash reason can be surfaced in the UI.
      this.lastStderr = (this.lastStderr + chunk).slice(-2000)
      console.error('[sidecar]', chunk.trimEnd())
    })
    proc.on('error', (err) => {
      console.error('[sidecar] process error', err)
      this.handleExit(`process error: ${err.message}`)
    })
    proc.on('exit', (code, signal) => {
      this.handleExit(`exited (code=${code}, signal=${signal})`)
    })

    void this.waitForReady()
  }

  private async waitForReady(): Promise<void> {
    const proc = this.proc
    for (let attempt = 0; attempt < PING_MAX_ATTEMPTS; attempt++) {
      if (this.proc !== proc || !proc || proc.exitCode !== null) return // died / replaced
      try {
        const res = (await this.request('ping', {}, 1000)) as { ok?: boolean }
        if (res && res.ok) {
          this.setStatus({ state: 'ready' })
          return
        }
      } catch {
        // not up yet; retry
      }
      await delay(PING_INTERVAL_MS)
    }
    const tail = this.lastStderr.trim()
    this.setStatus({
      state: 'down',
      detail: 'Sidecar did not answer ping() in time.' + (tail ? `\n\n${tail}` : '')
    })
  }

  private onStdout(chunk: string): void {
    this.buffer += chunk
    let idx: number
    while ((idx = this.buffer.indexOf('\n')) >= 0) {
      const line = this.buffer.slice(0, idx).trim()
      this.buffer = this.buffer.slice(idx + 1)
      if (!line) continue
      this.handleMessage(line)
    }
  }

  private handleMessage(line: string): void {
    let msg: { id?: number; result?: unknown; error?: { message?: string } }
    try {
      msg = JSON.parse(line)
    } catch {
      console.error('[sidecar] non-JSON line:', line)
      return
    }
    if (typeof msg.id !== 'number') return
    const p = this.pending.get(msg.id)
    if (!p) return
    this.pending.delete(msg.id)
    clearTimeout(p.timer)
    if (msg.error) {
      p.reject(new Error(msg.error.message || 'sidecar error'))
    } else {
      p.resolve(msg.result)
    }
  }

  request(method: string, params: unknown = {}, timeoutMs = REQUEST_TIMEOUT_MS): Promise<unknown> {
    const proc = this.proc
    if (!proc || !proc.stdin || proc.exitCode !== null) {
      return Promise.reject(new Error('Sidecar is not running.'))
    }
    const id = this.nextId++
    const payload = JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n'
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id)
        reject(new Error(`Sidecar request '${method}' timed out.`))
      }, timeoutMs)
      this.pending.set(id, { resolve, reject, timer })
      proc.stdin!.write(payload, (err) => {
        if (err) {
          this.pending.delete(id)
          clearTimeout(timer)
          reject(err)
        }
      })
    })
  }

  private handleExit(reason: string): void {
    if (!this.proc) return
    this.proc = null
    this.rejectAllPending(`Sidecar ${reason}.`)
    if (this.quitting) {
      this.setStatus({ state: 'down', detail: 'Sidecar stopped (app quitting).' })
      return
    }
    const tail = this.lastStderr.trim()
    this.setStatus({ state: 'down', detail: `Sidecar ${reason}. Restarting…` + (tail ? `\n\n${tail}` : '') })
    if (this.respawnTimer) clearTimeout(this.respawnTimer)
    this.respawnTimer = setTimeout(() => {
      this.respawnTimer = null
      if (!this.quitting) this.start()
    }, RESPAWN_DELAY_MS)
  }

  private rejectAllPending(message: string): void {
    for (const [, p] of this.pending) {
      clearTimeout(p.timer)
      p.reject(new Error(message))
    }
    this.pending.clear()
  }

  private setStatus(status: SidecarStatus): void {
    this.status = status
    this.emit('status', status)
  }

  stop(): void {
    this.quitting = true
    if (this.respawnTimer) {
      clearTimeout(this.respawnTimer)
      this.respawnTimer = null
    }
    this.rejectAllPending('Sidecar shutting down.')
    const proc = this.proc
    this.proc = null
    if (proc && proc.exitCode === null) {
      proc.kill('SIGTERM')
      // Hard-kill if it lingers.
      setTimeout(() => {
        if (proc.exitCode === null) proc.kill('SIGKILL')
      }, 1500)
    }
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms))
}

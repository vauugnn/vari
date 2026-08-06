# Phase 0 — Skeleton and round trip

**Read first:** `docs/HLD.md` sections 2 (Architecture), 2.4 (IPC contract), 11 (Tech stack).

## Goal

Prove the three-part architecture works end to end with the smallest possible
payload. No statistics, no data model, no dialogs.

When this phase is done, typing `TITLE 'hello'.` in the Syntax Editor and
clicking Run makes the words appear in the Output Viewer, having travelled
renderer → main → Python sidecar → back.

That round trip is the whole phase. Everything after it is filling in.

## Scope

### 1. Electron shell

- `src/main/index.ts`: app lifecycle, window creation
- `contextIsolation: true`, `nodeIntegration: false`, preload script exposing
  a narrow API via `contextBridge`
- Three windows:
  - **Data Editor** — main window, empty body, tabs at bottom left reading
    `Data View` | `Variable View` (non-functional, correct position and style)
  - **Output Viewer** — split pane, outline tree on left (empty), content pane
    on right
  - **Syntax Editor** — plain `<textarea>` plus a Run button
- Window menu switches between them; closing the Data Editor quits the app

### 2. Menu bar

Full top-level menu bar, correct order and labels:

```
File  Edit  View  Data  Transform  Analyze  Graphs  Utilities  Extensions  Window  Help
```

Populate `Analyze` with the correct submenu structure (Descriptive Statistics,
Compare Means, General Linear Model, Correlate, Regression, Dimension
Reduction, Scale, Nonparametric Tests) with all leaf items present and
disabled. This costs an hour now and makes every later phase a matter of
enabling an item rather than restructuring a menu.

Everything else can be a stub that logs.

### 3. Python sidecar

- `sidecar/server.py`: reads newline-delimited JSON-RPC 2.0 from stdin, writes
  responses to stdout, logs to stderr
- Implements exactly two methods:
  - `syntax.execute(text)` → returns a list of output objects
  - `ping()` → returns `{"ok": true}`, used for readiness
- The only command it understands is `TITLE 'string'.`, which returns a single
  `{"type": "Title", "text": "..."}` object
- Anything else returns an `{"type": "Error", "text": "..."}` object. Do not
  build a real parser yet.

### 4. Sidecar supervision (`src/main/sidecar.ts`)

- Spawn on app start from `./venv/bin/python` (or `./venv/Scripts/python.exe`
  on Windows), path configurable via env var
- Wait for `ping()` before enabling the Run button
- **Crash handling is part of this phase, not a later polish item.** If the
  process exits, surface an error in the Viewer, reject any in-flight request
  rather than hanging, and respawn. A hung promise waiting on a dead process
  is miserable to debug in month four.
- Kill the sidecar on app quit, including on force quit

### 5. Minimal output rendering

The Viewer renders a list of output objects. Only `Title` and `Error` need to
render. Build it as a component that switches on `type` with a fallback for
unknown types, so later phases add `PivotTable` without touching the plumbing.

## Explicitly NOT in this phase

Do not build: any dataset model, any file I/O, any grid, any dialog, any
statistical procedure, any real syntax lexer or parser, the expression
language, charts, or packaging config. If any of these seem needed to finish
Phase 0, they aren't. Say so and stop.

## Acceptance criteria

- [ ] `npm run dev` launches all three windows
- [ ] Menu bar matches the structure above, Analyze submenu fully present
- [ ] Sidecar spawns automatically and answers `ping()`
- [ ] Typing `TITLE 'hello'.` and clicking Run renders "hello" in the Viewer
- [ ] Typing `FREQUENCIES x.` renders an Error object, not a crash
- [ ] Killing the Python process manually shows an error and respawns; the
      app does not hang
- [ ] Quitting the app leaves no orphaned Python process
- [ ] `pytest` runs and passes at least one test of `syntax.execute`

Stop here when these pass. Do not begin Phase 1.

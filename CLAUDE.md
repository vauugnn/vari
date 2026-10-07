# CLAUDE.md

Project context for Claude Code. Read this at the start of every session.

## What this is

A desktop reimplementation of IBM SPSS Statistics (Base), built for personal
use in a social statistics course. Electron shell, React renderer, Python
sidecar for all data and statistics.

Full design: `docs/HLD.md`. Do not read it end to end every session. Read the
sections the current phase file names.

## Where we are

Current phase: **Phase 0**. See `docs/phases/PHASE-0.md`.

Do not implement anything outside the current phase's scope, even if it seems
small and adjacent. Phases exist to stop this project from becoming thirty
half-built features. If something out of scope seems necessary, say so and
stop rather than building it.

## Non-negotiable architecture rules

These are load-bearing. Violating any of them means a rewrite later.

1. **All execution routes through syntax.** Dialogs generate SPSS command
   syntax strings. Those strings go to the lexer, then the parser, then a
   procedure. Nothing in the renderer may call a procedure directly. This is
   what makes the Paste button, the Syntax Editor, and the journal free
   instead of three separate implementations. Enforce it structurally: the
   renderer's only path to computation is `syntax.execute`.

2. **The sidecar owns the data.** The renderer holds a windowed view of rows
   for the grid and the output document model. It never holds the
   authoritative dataset and never computes a statistic.

3. **System-missing and user-missing are different things.** Never convert
   user-missing values to NaN. Store raw values; keep missing definitions in
   metadata; compute a boolean mask at procedure time. See HLD section 3.3.
   Getting this wrong silently corrupts every survey scale score.

4. **Output is a document tree, not HTML strings.** Procedures return
   `PivotTable` / `Title` / `Notes` / `Chart` objects. The renderer renders
   them. See HLD section 4.

5. **SPSS defaults, not library defaults.** Every statistic must match SPSS,
   not scipy or R. HLD section 9 lists the known divergences. Read it before
   writing any procedure. Log new ones in `docs/PARITY.md`.

## Stack

- Electron (main + renderer), `contextIsolation: true`, `nodeIntegration: false`
- React 18 + TypeScript, Zustand for state
- Plain CSS modules. We are matching a Java Swing look, not building a design
  system. Do not add Tailwind or a component library.
- Python 3.11 sidecar: numpy, scipy, pandas, statsmodels, pingouin, pyreadstat
- IPC: JSON-RPC 2.0 over the sidecar's stdio, newline-delimited. No HTTP, no
  ports, no server.
- Tests: pytest (sidecar and parity), Vitest (renderer)

## Commands

```
npm run dev          # Electron in dev, spawns sidecar from ./venv
npm run test         # Vitest
npm run lint
pytest               # sidecar + parity tests
```

## Visual target

Keep SPSS's layout, menus, dialogs and workflow so it feels familiar, but the
look is a refined version of it (owner's call: "close but better looking").
All colours, radii, shadows and motion come from the tokens at the top of
`src/renderer/common/base.css`; use those, never hard-coded values. Pivot
tables keep the SPSS TableLook structure because that is what gets submitted.
Icons are original SVG redrawn to match SPSS's symbols; never copy IBM
artwork.

## Things that are out of scope, permanently

(Chart Builder and the IBM `.spv` format were moved in scope at the owner's request; see `sidecar/io/spv*.py`.)

Server mode,
database connectivity, the Python/R plugin system, and all add-on modules
(Complex Samples, Forecasting, Decision Trees, Neural Networks, Conjoint,
Amos).

Do not bundle or commit any IBM assets: no SPSS icons, no artwork, no sample
datasets from an SPSS install, no decompiled anything. Functionality is fair
game; assets are not.

## Working style

- Small commits, one concern each.
- When a phase's acceptance criteria are met, stop and say so. Do not roll
  into the next phase.
- If the HLD is wrong or ambiguous about something, say so explicitly rather
  than guessing and moving on. The HLD is a draft, not scripture.

<div align="center">

<img src="build/icon.png" width="120" alt="Vari icon" />

# Vari

**A desktop statistics application with an SPSS-style workflow.**

Data Editor · Syntax · Output Viewer — everything routes through command syntax.

[![Build Vari](https://github.com/vauugnn/vari/actions/workflows/build.yml/badge.svg)](https://github.com/vauugnn/vari/actions/workflows/build.yml)

</div>

---

Vari is a from-scratch reimplementation of the IBM® SPSS® Statistics Base
workflow, built for a social-statistics course. Electron shell, React renderer,
and a Python compute sidecar that owns all data and statistics. The load-bearing
rule: **dialogs generate SPSS command syntax → lexer → parser → procedure.**
Nothing in the UI computes a statistic directly, so the **Paste** button, the
Syntax Editor, and the journal come for free.

## Features

- **Data Editor** — spreadsheet grid (virtualized to 100k+ rows), Variable View
  with all 11 attributes, measure icons, value-labels toggle, column resize,
  copy/paste, context menus, customizable toolbar.
- **Analyze** — Frequencies, Descriptives, Explore, Crosstabs (χ² + phi/Cramér's
  V/gamma/tau), Means, One-Sample/Independent/Paired T-Tests, One-Way ANOVA
  (+ post-hoc), Correlate (Pearson/Spearman/Kendall), Partial correlation,
  Linear & Logistic & Ordinal & Multinomial Regression, GLM Univariate, Factor,
  Reliability (Cronbach's α), K-Means/Hierarchical Cluster, Discriminant, the
  full Nonparametric suite, ROC, Curve Estimation, Case Summaries, Codebook.
- **Transform** — COMPUTE / RECODE / IF / COUNT / RANK / AUTORECODE / RMV, backed
  by a real SPSS expression engine (operator precedence, `MEAN.3(q1 TO q5)`
  scale scores, SPSS missing-value propagation).
- **Data** — Sort, Select If, Filter, Weight, Split File, Aggregate, Transpose,
  Merge (Add Cases / Add Variables).
- **Graphs** — histogram, bar, pie, scatter, boxplot, line, area, error bar,
  P-P / Q-Q (matplotlib → inline SVG).
- **Files** — read `.sav` `.por` `.dta` `.xlsx` `.csv` (with an import wizard);
  save `.sav` `.csv` `.xlsx`; export output to HTML / Excel / PDF.

Statistics match SPSS defaults (n−1 variance, Type III SS, Levene on the mean,
HAVERAGE percentiles, G1/G2 skew/kurtosis, half-away-from-zero rounding, …) and
are verified against SciPy / statsmodels / scikit-learn / pingouin in the test
suite. Divergences are logged in [`docs/PARITY.md`](docs/PARITY.md).

## Install

Grab an installer from the latest green **[Actions run](https://github.com/vauugnn/vari/actions)**
(Artifacts) — `vari-macos` (`.dmg`) or `vari-windows` (`.exe`).

- **macOS** — open the `.dmg`, drag **Vari** to Applications. The build is
  unsigned, so on first launch right-click the app ▸ **Open** (once).
- **Windows** — run the `.exe`. SmartScreen shows an "unknown publisher"
  warning (unsigned) → **More info ▸ Run anyway**.

## Run from source

```bash
# 1. Python sidecar
python3.11 -m venv venv
./venv/bin/pip install -r requirements.txt

# 2. Node
npm install

# 3. Dev (Electron + Vite, spawns the sidecar from ./venv)
npm run dev
```

## Build installers

CI (`.github/workflows/build.yml`) builds macOS and Windows on their native
runners: PyInstaller freezes the sidecar, then electron-builder packages it.
Locally, on the target OS:

```bash
npm run sidecar:freeze   # PyInstaller -> packaging/dist/vari-sidecar
npm run dist             # electron-vite build + electron-builder
```

## Architecture

```
Electron main ──contextBridge──▶ React renderer (grids, dialogs, viewer)
      │
      └──JSON-RPC 2.0 over stdio──▶ Python sidecar
                                     (dataset store, syntax engine,
                                      expression language, procedures,
                                      output model, .sav I/O, charts)
```

- **State** lives in the sidecar; the renderer holds a windowed view + the output
  document tree.
- **Output** is a typed object tree (`PivotTable` / `Chart` / `Title` …), not
  HTML — which is what makes HTML/Excel/PDF export and the outline pane possible.
- See [`docs/HLD.md`](docs/HLD.md) for the full design.

## Tech stack

Electron · React 18 + TypeScript · Zustand · plain CSS · Python 3.11 · NumPy ·
SciPy · pandas · statsmodels · scikit-learn · pingouin · pyreadstat · openpyxl ·
matplotlib · PyInstaller · electron-builder.

## Tests

```bash
pytest          # sidecar + parity (stats verified vs scipy/statsmodels/sklearn)
npm run test    # renderer (Vitest)
npm run lint
```

## Disclaimer

Vari is an independent, original reimplementation built for personal and
coursework use. It is **not affiliated with, endorsed by, or derived from** IBM
or IBM SPSS Statistics, and ships **no IBM assets** — all icons and artwork are
original, and test fixtures are synthetic. "SPSS" is a trademark of IBM;
referenced here only to describe compatibility.

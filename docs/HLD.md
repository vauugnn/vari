# SPSS Statistics Clone — High Level Design

**Status:** design spec, pre-implementation
**Target:** personal-use desktop reimplementation of IBM SPSS Statistics (Base) for social statistics coursework
**Handoff:** this document is written to be given to Claude Code as the root context for a phased build

---

## 0. How to use this document with Claude Code

Do not hand Claude Code this whole document and say "build it." It will produce a shallow version of everything and a working version of nothing.

Instead:

1. Put this file in the repo root as `docs/HLD.md`.
2. Create `docs/phases/PHASE-N.md` for the phase you're on, containing only that phase's scope, its acceptance criteria, and the sections of this doc it depends on.
3. Start each Claude Code session with: "Read `docs/HLD.md` sections X, Y, Z and `docs/phases/PHASE-N.md`. Implement only what PHASE-N describes."
4. Keep `docs/PARITY.md` as a running log of every SPSS-vs-our-output discrepancy found and how it was resolved. This file becomes the most valuable artifact in the repo.

Sections 9 (numeric parity) and 5.3 (the dialog shell) are the two that will save the most time. Read them before writing any code.

---

## 1. Goals and non-goals

### Goals

- **Visual fidelity.** A user familiar with SPSS should navigate this without relearning anything. Same menu structure, same dialog layouts, same button order, same output table shapes.
- **Numeric parity.** Results must match SPSS to at least 6 significant figures on every implemented procedure, using SPSS's defaults, not the defaults of whatever library is doing the math.
- **Syntax fidelity.** The Paste button produces runnable SPSS command syntax. The Syntax Editor runs it.
- **File compatibility.** Reads and writes `.sav` including variable labels, value labels, missing value definitions, and formats. Reads `.csv`, `.xlsx`, `.dta`, `.por`.

### Non-goals

- Distribution to anyone. This is personal use, which sidesteps the trade dress and EULA questions that would otherwise matter.
- Add-on modules: Complex Samples, Forecasting, Decision Trees, Neural Networks, Conjoint, Direct Marketing, Amos.
- Server mode, distributed analysis, database connectivity.
- The `.spv` output format. Export to HTML, PDF, and `.xlsx` instead.
- The Chart Builder drag-and-drop canvas. Legacy chart dialogs only. (See §11 Risks.)
- SPSS's Python/R integration plugin system.

---

## 2. Architecture

### 2.1 Process topology

```
┌─────────────────────────────────────────────────────────┐
│ Electron Main Process (Node)                            │
│  • window lifecycle (Data Editor / Viewer / Syntax)     │
│  • native file dialogs, menus, printing                 │
│  • spawns and supervises the compute sidecar            │
│  • JSON-RPC broker between renderer and sidecar         │
└───────────────┬─────────────────────────┬───────────────┘
                │ contextBridge IPC       │ JSON-RPC / stdio
                ▼                         ▼
┌───────────────────────────┐  ┌──────────────────────────┐
│ Renderer (React + TS)     │  │ Compute Sidecar (Python) │
│  • Data View grid         │  │  • dataset store         │
│  • Variable View grid     │  │  • syntax lexer/parser   │
│  • dialog shell + dialogs │  │  • procedure engine      │
│  • Output Viewer          │  │  • expression evaluator  │
│  • Syntax Editor          │  │  • output model producer │
│  • renders output model   │  │  • .sav reader/writer    │
└───────────────────────────┘  └──────────────────────────┘
```

**The renderer holds no statistical logic and no authoritative data.** It holds a *view* of the active dataset (a windowed slice for the grid) and the output document model. The sidecar owns the truth.

### 2.2 The central design decision: everything routes through syntax

This is the single most important architectural choice in the project, and getting it wrong will cost months.

Dialogs do not call procedures. Dialogs **generate command syntax strings**. Those strings go to the parser, which produces a command object, which dispatches to a procedure.

```
Dialog state  ──▶  syntax string  ──▶  lexer  ──▶  parser  ──▶  Command AST
                                                                     │
                                                                     ▼
Output Viewer ◀──  Output Document  ◀──  Procedure  ◀──  dispatcher
```

Consequences, all of them good:

- The **Paste** button is free. It's the same string, routed to the Syntax Editor instead of the executor.
- The **Syntax Editor** is free. Same pipeline, string typed by hand.
- The **journal file** is free. Log every string that enters the pipeline.
- Every procedure has exactly one entry point, so testing is one path, not two.
- Dialogs become dumb. They are forms that serialize to text. No dialog needs to know how an ANOVA works.

The temptation, especially early, is to let the Frequencies dialog just call `run_frequencies(vars, stats)` directly because it's faster. Resist it. Retrofitting the syntax layer later means rewriting every dialog.

### 2.3 Why Python for the sidecar

`pyreadstat` is the only mature `.sav` reader/writer with full metadata support, and it's Python. Once the sidecar is Python, keeping the stats there too (scipy, statsmodels, pingouin) avoids a second language boundary. R has better parity with SPSS on a few procedures, but the two-hop bridge isn't worth it.

### 2.4 IPC contract

JSON-RPC 2.0 over the sidecar's stdin/stdout, newline-delimited. Methods:

| Method | Purpose |
|---|---|
| `dataset.open` | load a file, return dataset handle + variable metadata |
| `dataset.save` | write active dataset |
| `dataset.getRows` | windowed row fetch for the grid (offset, limit) |
| `dataset.setCell` | edit one cell |
| `dataset.setVariableMeta` | Variable View edit |
| `dataset.insertVariable` / `deleteVariable` | structural edits |
| `dataset.insertCase` / `deleteCase` | structural edits |
| `syntax.execute` | run a syntax string, stream back output objects |
| `syntax.parse` | parse-only, for editor validation |
| `variables.list` | for populating dialog source lists |

Long-running procedures stream partial output objects so the Viewer populates progressively, matching SPSS's behavior.

---

## 3. Data model

### 3.1 Variable metadata

Every variable carries eleven attributes, matching Variable View exactly:

| Attribute | Type | Notes |
|---|---|---|
| `name` | string | max 64 bytes, case-preserving, case-insensitive matching, must not start with a digit, must not be a reserved keyword |
| `type` | enum | Numeric, Comma, Dot, Scientific, Date, Dollar, Custom currency, String, Restricted Numeric |
| `width` | int | display width |
| `decimals` | int | decimal places |
| `label` | string | max 256 bytes |
| `valueLabels` | map | value → label, max 120 bytes per label |
| `missing` | union | none \| discrete (up to 3 values) \| range (lo, hi) + optional discrete |
| `columns` | int | grid column width in characters |
| `align` | enum | Left, Right, Center |
| `measure` | enum | Nominal, Ordinal, Scale |
| `role` | enum | Input, Target, Both, None, Partition, Split |

Reserved keywords that cannot be variable names: `ALL AND BY EQ GE GT LE LT NE NOT OR TO WITH`.

### 3.2 Print and write formats

Formats drive display everywhere and must be modeled as first-class objects, not strings. Format is `TYPE` + `width` + optional `decimals`, e.g. `F8.2`, `A10`, `DATE11`, `DOLLAR12.2`, `PCT5.1`, `COMMA10.0`, `E10.3`.

Implement a `Format` class with `parse(str)`, `render(value) -> str`, and `defaultFor(dtype)`.

### 3.3 The missing value trap

**This is the bug you will hit and it will be hard to find.**

SPSS distinguishes:

- **System-missing** (`$SYSMIS`): no value present. Displayed as `.` in Data View.
- **User-missing**: a real value the user declared as missing (e.g. 99 = "declined to answer"). Displayed as the value, with a shaded cell if value labels are on.

Pandas has only `NaN`. If you convert user-missing to `NaN` on load, you have destroyed information: the value must survive a round-trip to `.sav`, must appear in the Data Editor, and must be *includable* in some procedures (`MISSING=INCLUDE`).

**Design:** store the raw values in the DataFrame. Keep user-missing definitions in the metadata. Compute a boolean mask at procedure time:

```python
def missing_mask(series, meta, include_user_missing=False):
    m = series.isna()                     # system-missing
    if not include_user_missing:
        m |= meta.missing.matches(series) # user-missing
    return m
```

Every procedure takes the mask, never assumes `NaN` is the whole story.

### 3.4 Backing store

`pandas.DataFrame` for the values, a parallel `list[VariableMeta]` for metadata, kept in index-order lockstep. Wrap both in a `Dataset` class so structural edits (insert/delete variable) update both atomically.

For datasets above ~500k rows, revisit with Arrow. Coursework datasets will not get there.

### 3.5 Multiple datasets

SPSS supports several open datasets with one *active*. Model as `DatasetRegistry` keyed by dataset name (`DataSet1`, `DataSet2`, ...), with an active pointer. Needed for `MATCH FILES` and `ADD FILES`.

---

## 4. Output document model

Output is **not** HTML and **not** strings. It is a tree that the renderer renders. This separation is what makes export, printing, and the outline pane possible.

```
OutputDocument
└── CommandBlock (one per executed command)
    ├── Title       (the procedure name, e.g. "Frequencies")
    ├── Notes       (collapsed by default, matches SPSS)
    ├── PivotTable  (0..n)
    ├── Chart       (0..n)
    ├── TextBlock   (0..n)
    └── Warning / Error
```

### 4.1 PivotTable

The workhorse. SPSS tables are not grids, they are pivoted multi-dimensional structures:

```typescript
interface PivotTable {
  title: string;
  caption?: string;
  dimensions: {
    rows: Dimension[];     // nested, outermost first
    columns: Dimension[];  // nested, outermost first
    layers: Dimension[];   // shown one slice at a time
  };
  cells: Map<CellKey, Cell>;   // key = tuple of category indices
  footnotes: Footnote[];
  look: TableLook;
}

interface Dimension {
  label: string;            // e.g. "Statistics", "Group"
  categories: Category[];   // e.g. ["Mean", "Std. Deviation", "N"]
}

interface Cell {
  value: number | string | null;
  format: Format;           // controls decimals, leading zero, etc.
  footnoteRefs: number[];
}
```

A Crosstabs table with row variable, column variable, and Count/Expected/% cells is: rows = [rowVar, statistic], columns = [colVar]. Nesting falls out naturally.

### 4.2 TableLook

Fonts, borders, cell padding, header shading, alignment per cell class. Model it as a style object applied at render time, not baked into cells. SPSS ships several TableLooks; implement the default one and leave the mechanism open.

Default that matters: **SPSS uses a serif-free 9pt-ish font with hairline borders on header rows and no vertical interior borders.** Match the outer double rule and the header underline and it reads as SPSS immediately.

### 4.3 Rendering

Renderer walks the tree and emits HTML tables with CSS. Export to HTML is then near-free. PDF via Electron's `printToPDF`. Excel export via a serializer over the same tree.

---

## 5. UI specification

### 5.1 Windows

Three window types, matching SPSS:

- **Data Editor** — the main window. Tabs at bottom left: `Data View` | `Variable View`.
- **Output Viewer** — split pane, outline tree on the left, content on the right.
- **Syntax Editor** — text editor with a Run menu and a toolbar run button.

Menu bar (present in all three, contents contextual): `File  Edit  View  Data  Transform  Analyze  Graphs  Utilities  Extensions  Window  Help`.

### 5.2 Data View grid

- Column headers are variable names, row headers are case numbers (1-based).
- Empty numeric cells show `.`.
- Typing into the first empty column creates `VAR00001` with format `F8.2`.
- Toggle button shows value labels instead of raw values.
- Selection: cell, row (click row header), column (click column header), block drag.
- Frozen row and column headers, virtualized body.

**Grid implementation:** do not use a generic data-grid library. The requirements (per-cell formatting, frozen headers, cell-level edit state, 100k+ rows, right-aligned numerics with format-driven display) fight most libraries. Build a virtualized grid over a windowed row cache fed by `dataset.getRows`. Budget real time for this; it is the single largest UI component.

### 5.3 The universal dialog shell

**Build this first, before any actual dialog.** Roughly 30 dialogs reuse it. Getting it right once is the difference between a two-day dialog and a two-hour dialog.

```
┌──────────────────────────────────────────────────────┐
│ Frequencies                                      [X] │
├──────────────────────────────────────────────────────┤
│ ┌────────────────┐        ┌──────────────────┐       │
│ │ [icon] age     │  [▶]   │ Variable(s):     │ ┌────────────┐
│ │ [icon] gender  │        │ ┌──────────────┐ │ │ Statistics…│
│ │ [icon] income  │  [◀]   │ │ [icon] educ  │ │ ├────────────┤
│ │ [icon] educ    │        │ │              │ │ │ Charts…    │
│ │                │        │ └──────────────┘ │ ├────────────┤
│ └────────────────┘        └──────────────────┘ │ │ Format…    │
│                                                 └────────────┘
│ ☑ Display frequency tables                           │
├──────────────────────────────────────────────────────┤
│        [ OK ] [ Paste ] [ Reset ] [ Cancel ] [ Help ]│
└──────────────────────────────────────────────────────┘
```

Required behaviors:

- **Source list** shows a measure-level icon per variable (ruler = Scale, stepped bars = Ordinal, three circles = Nominal) plus a type indicator for string/date.
- Right-click the source list toggles: Display Variable Names / Labels, Sort Alphabetically / By File Order.
- Variables move via arrow button, double-click, or drag.
- The arrow button greys out when the selected variable's type is invalid for the target box (e.g. a string variable into a Dependent List that requires numeric).
- Variables in a target box are removed from the source list, and returned to their file-order position when moved back.
- **Reset** restores the dialog to its opened-fresh state.
- **Paste** writes syntax to the Syntax Editor and closes the dialog.
- Sub-dialog buttons on the right edge open modal children whose state feeds the same syntax generator.
- Dialog state persists for the session (reopening Frequencies shows your last selection), matching SPSS's Recall Recently Used Dialogs.

**API sketch:**

```typescript
interface DialogSpec {
  id: string;
  title: string;
  targets: TargetBox[];        // label, arity, accepted types
  options: OptionControl[];    // checkboxes, radios, numeric fields
  subDialogs: SubDialogSpec[];
  toSyntax(state: DialogState): string;   // the only procedure-specific code
}
```

Each concrete dialog is then a declarative spec plus one `toSyntax` function. That is the whole point.

---

## 6. Procedure catalog

Ordered by build priority. Syntax command in parentheses.

### Tier 1 — required for any social statistics course

**Analyze ▸ Descriptive Statistics**
- Frequencies (`FREQUENCIES`) — freq table, percentiles, central tendency, dispersion, distribution, bar/pie/histogram
- Descriptives (`DESCRIPTIVES`) — with Z-score saving
- Explore (`EXAMINE`) — descriptives, M-estimators, outliers, percentiles, normality tests, stem-and-leaf, boxplot, Q-Q
- Crosstabs (`CROSSTABS`) — chi-square, phi/Cramér's V, contingency coefficient, lambda, gamma, Somers' d, Kendall's tau-b/c, eta, risk, McNemar, Cochran/Mantel-Haenszel; cell counts observed/expected, row/column/total %, residuals

**Analyze ▸ Compare Means**
- Means (`MEANS`) — with ANOVA table and eta
- One-Sample T Test (`T-TEST /TESTVAL`)
- Independent-Samples T Test (`T-TEST /GROUPS`)
- Paired-Samples T Test (`T-TEST /PAIRS`)
- One-Way ANOVA (`ONEWAY`) — contrasts, post hoc, homogeneity, Welch/Brown-Forsythe, means plot

**Analyze ▸ Correlate**
- Bivariate (`CORRELATIONS`, `NONPAR CORR`) — Pearson, Kendall's tau-b, Spearman
- Partial (`PARTIAL CORR`)

**Analyze ▸ Regression**
- Linear (`REGRESSION`) — enter/stepwise/remove/backward/forward, statistics, plots, save residuals, collinearity, Durbin-Watson

**Analyze ▸ Nonparametric Tests ▸ Legacy Dialogs** (`NPAR TESTS`)
- Chi-Square, Binomial, Runs, 1-Sample K-S
- 2 Independent Samples: Mann-Whitney U, Kolmogorov-Smirnov Z, Moses, Wald-Wolfowitz
- K Independent Samples: Kruskal-Wallis H, Median, Jonckheere-Terpstra
- 2 Related Samples: Wilcoxon, Sign, McNemar, Marginal Homogeneity
- K Related Samples: Friedman, Kendall's W, Cochran's Q

**Analyze ▸ Scale**
- Reliability Analysis (`RELIABILITY`) — alpha, split-half, item-total statistics

### Tier 2

- General Linear Model ▸ Univariate (`UNIANOVA`) — factorial ANOVA, covariates, Type I–IV SS, post hoc, estimated marginal means, effect size
- General Linear Model ▸ Repeated Measures (`GLM ... /WSFACTOR`) — sphericity, Greenhouse-Geisser, Huynh-Feldt
- Dimension Reduction ▸ Factor (`FACTOR`) — PCA/PAF/ML extraction, varimax/oblimin/promax rotation, KMO, Bartlett's, scree
- Regression ▸ Binary Logistic (`LOGISTIC REGRESSION`)
- Regression ▸ Ordinal (`PLUM`), Multinomial (`NOMREG`)
- Classify ▸ K-Means (`QUICK CLUSTER`), Hierarchical (`CLUSTER`), Discriminant (`DISCRIMINANT`)

### Tier 3

- General Linear Model ▸ Multivariate
- Mixed Models (`MIXED`)
- Survival (`KM`, `COXREG`)

### Data menu

`SORT CASES`, `FLIP` (Transpose), `ADD FILES` / `MATCH FILES` (Merge), `AGGREGATE`, `SPLIT FILE`, `SELECT IF` / `FILTER` (Select Cases), `WEIGHT`, Define Variable Properties, Copy Data Properties, Identify Duplicate Cases.

### Transform menu

`COMPUTE`, `RECODE` (into same / into different), `AUTORECODE`, `RANK`, `RMV` (Replace Missing Values), `COUNT`, Visual Binning, Random Number Generators.

**Split File and Weight Cases are cross-cutting.** Every procedure must respect them:
- `SPLIT FILE` = run the procedure once per split group, emit one table set per group (or layered, if `LAYERED` is set)
- `WEIGHT BY var` = replicate-weight every count, mean, and SS calculation

Bake both into the procedure base class from day one. Retrofitting them across 30 procedures is miserable.

---

## 7. The expression language

`COMPUTE`, `IF`, `SELECT IF`, and `DO IF` all evaluate SPSS expressions. This needs its own lexer, parser, and evaluator, separate from the command parser.

### 7.1 Operators, by precedence (highest first)

1. `()`
2. `**` (exponentiation)
3. unary `-`
4. `*` `/`
5. `+` `-`
6. `<` `>` `<=` `>=` `=` `~=` (and word forms `LT GT LE GE EQ NE`)
7. `NOT` / `~`
8. `AND` / `&`
9. `OR` / `|`

### 7.2 Function library

- **Arithmetic:** `ABS RND TRUNC MOD SQRT EXP LN LG10 SIN COS ARSIN ARTAN`
- **Across-variable statistical:** `SUM MEAN SD VARIANCE MIN MAX CFVAR` — each supports the `.n` minimum-valid-arguments suffix, e.g. `MEAN.3(q1 TO q5)` returns the mean only if at least 3 of the 5 are valid
- **Missing:** `MISSING(x)` `SYSMIS(x)` `VALUE(x)` `NMISS(...)` `NVALID(...)`
- **String:** `CONCAT SUBSTR LTRIM RTRIM UPCASE LOWER INDEX RINDEX LENGTH NUMBER STRING REPLACE CHAR.SUBSTR`
- **Date/time:** `DATE.DMY DATE.MDY DATE.YRDAY XDATE.YEAR XDATE.MONTH XDATE.WKDAY CTIME.DAYS CTIME.HOURS DATEDIFF DATESUM TIME.HMS`
- **Random:** `RV.NORMAL RV.UNIFORM RV.BINOM RV.POISSON NORMAL UNIFORM`
- **Distribution:** `CDF.<dist> IDF.<dist> PDF.<dist> SIG.<dist> NCDF.<dist>` for NORMAL, T, CHISQ, F, BINOM, POISSON, BETA, GAMMA, etc.

### 7.3 Missing propagation rule

Any operand that is missing makes the result system-missing, **except**:
- the `.n` forms of the across-variable functions
- `MISSING()`, `SYSMIS()`, `NMISS()`, `NVALID()`, `VALUE()`
- logical short-circuit cases: `FALSE AND missing` is `FALSE`, `TRUE OR missing` is `TRUE`

Get this wrong and every computed scale score in a survey dataset will be subtly incorrect.

---

## 8. Syntax engine

### 8.1 Lexer

- A command ends at a period **at end of line**, or at a blank line.
- `/` introduces a subcommand.
- `=` is largely optional and often ignored: `/STATISTICS=MEAN` and `/STATISTICS MEAN` are equivalent.
- `TO` expands variable ranges by file position: `q1 TO q10`.
- `ALL` means all variables in the active dataset.
- Strings are single- or double-quoted; doubled quotes escape.
- Comments: `*` at start of a command, or `/* ... */`.
- Keywords are case-insensitive and abbreviatable to any unambiguous prefix (`FREQ` for `FREQUENCIES`, `VAR` for `VARIABLES`). Implement prefix matching against the command table.

### 8.2 Parser

Recursive descent, one grammar per command, driven by a command registry:

```python
@command("FREQUENCIES", abbrev="FREQ")
class Frequencies(Procedure):
    subcommands = {
        "VARIABLES": VarListSpec(required=True),
        "STATISTICS": KeywordListSpec(STAT_KEYWORDS),
        "PERCENTILES": NumberListSpec(),
        "NTILES": IntSpec(),
        "HISTOGRAM": FlagWithOptionsSpec(),
        "BARCHART": FlagWithOptionsSpec(),
        "FORMAT": KeywordListSpec(FORMAT_KEYWORDS),
        "ORDER": EnumSpec(["ANALYSIS", "VARIABLE"]),
        "MISSING": EnumSpec(["EXCLUDE", "INCLUDE"]),
    }
    def run(self, dataset, args) -> list[OutputObject]: ...
```

New procedures are then a spec plus a `run`. This registry is also what powers Syntax Editor autocomplete and the abbreviation matcher.

### 8.3 Non-procedure commands needed

`GET FILE`, `GET DATA`, `SAVE`, `SAVE TRANSLATE`, `DATASET ACTIVATE/NAME/CLOSE/COPY`, `VARIABLE LABELS`, `VALUE LABELS`, `ADD VALUE LABELS`, `MISSING VALUES`, `FORMATS`, `VARIABLE LEVEL`, `VARIABLE WIDTH`, `RENAME VARIABLES`, `DELETE VARIABLES`, `EXECUTE`, `TEMPORARY`, `DO IF` / `ELSE IF` / `ELSE` / `END IF`, `DO REPEAT` / `END REPEAT`, `LOOP` / `END LOOP`, `VECTOR`, `NUMERIC`, `STRING`, `SET`, `SHOW`, `TITLE`, `SUBTITLE`, `INSERT`.

`TEMPORARY` deserves a note: it makes the *next* procedure see the transformations, then discards them. It's a transaction boundary. Model the dataset as copy-on-write to support it.

---

## 9. Numeric parity: the SPSS-specific defaults

**This is the section that determines whether the project succeeds.** Every item below is a place where SPSS's default differs from the obvious scipy/statsmodels/R default. Each one produces a number that looks plausible and is wrong.

### 9.1 Known divergences

| Area | SPSS behavior | Naive library default |
|---|---|---|
| Levene's test (in T-TEST) | centered on the **mean** | `car::leveneTest` centers on the **median**; `scipy.stats.levene` defaults to `center='median'` |
| Independent-samples t | reports **both** equal-variances-assumed and Welch-Satterthwaite rows | libraries return one |
| `UNIANOVA` sums of squares | **Type III** by default | statsmodels `anova_lm` defaults to Type I |
| `CORRELATIONS` missing | **pairwise** deletion by default | varies |
| `REGRESSION` missing | **listwise** deletion by default | varies |
| Skewness / kurtosis | sample-adjusted G1 and G2 with standard errors `SES = sqrt(6n(n-1)/((n-2)(n+1)(n+3)))` | `scipy.stats.skew` defaults `bias=True` (moment estimator) |
| Percentiles | HAVERAGE (weighted average at `(n+1)p`) by default; `EXAMINE` offers 5 methods | numpy `percentile` defaults to linear interpolation on `(n-1)p` |
| Std. deviation | denominator `n-1` | numpy defaults to `n` (`ddof=0`) |
| Crosstabs chi-square | reports Pearson, likelihood ratio, linear-by-linear; continuity correction **only** for 2×2; Fisher's exact **only** for 2×2 | libraries apply Yates by default in some cases |
| Spearman with ties | midrank correction | usually matches, verify |
| Mann-Whitney | reports both exact and asymptotic; asymptotic **with** tie correction | verify tie correction is on |
| Kruskal-Wallis | tie-corrected H | verify |
| Cronbach's alpha | raw and standardized reported separately | pingouin returns one |
| Rounding | half **away from zero** | Python `round()` is half-to-even (banker's) |
| p-value display | leading zero **suppressed**: `.000` not `0.000`; modern versions show `<.001` | libraries print `0.000` |
| Correlation display | leading zero suppressed: `.847` | |
| Post hoc default alpha | `.05` | |

### 9.2 Post hoc test roster for ONEWAY

Equal variances assumed: LSD, Bonferroni, Sidak, Scheffé, R-E-G-W F, R-E-G-W Q, S-N-K, Tukey, Tukey's-b, Duncan, Hochberg's GT2, Gabriel, Waller-Duncan, Dunnett (with control group and 1-/2-sided options).

Equal variances not assumed: Tamhane's T2, Dunnett's T3, Games-Howell, Dunnett's C.

Most are not in any Python library. Budget real time, or implement the common six (LSD, Bonferroni, Sidak, Scheffé, Tukey, Games-Howell) and stub the rest.

### 9.3 Parity test harness

```
tests/parity/
  datasets/           # fixture .sav files
  expected/           # SPSS output, saved as SPSS's own Excel export
  test_frequencies.py
  test_ttest.py
  ...
```

Procedure: run the analysis in real SPSS (trial license, university lab machine, or a classmate's install), export output to `.xlsx`, commit it, then assert your values match to `rtol=1e-6`, with degrees of freedom matched exactly.

Do this **as each procedure lands**, not at the end. A parity bug found the day you write the procedure takes ten minutes. Found six months later, it takes a day.

Use SPSS's bundled sample datasets (`Employee data.sav`, `cars.sav`, `survey_sample.sav`) as fixtures. They're widely mirrored and every SPSS textbook uses them, so expected values are easy to cross-check.

---

## 10. Build phases

| Phase | Scope | Done when |
|---|---|---|
| **0** | Electron shell, sidecar spawn, JSON-RPC round trip, three empty windows, menu bar | `syntax.execute("TITLE 'hi'.")` renders a title in the Viewer |
| **1** | `Dataset`, `VariableMeta`, `Format`, missing-value mask, `.sav` read/write, Variable View grid, Data View grid | Open `Employee data.sav`, see correct values, labels, and formats; edit a cell; save; reopen unchanged |
| **2** | Output document model, PivotTable renderer, TableLook, outline pane, export to HTML | A hand-constructed PivotTable renders indistinguishably from an SPSS screenshot |
| **3** | Dialog shell (§5.3) + Frequencies + Descriptives end to end, including Paste | Frequencies dialog produces correct output *and* correct pasted syntax |
| **4** | Lexer, parser, command registry, Syntax Editor, journal | Typed `FREQUENCIES VARIABLES=jobcat /STATISTICS=MEAN.` runs |
| **5** | Expression language, `COMPUTE`, `RECODE`, `IF`, `DO IF` | Computed scale score with `MEAN.3()` matches SPSS on a survey dataset |
| **6** | Tier 1 procedures, in catalog order | Each lands with parity tests green |
| **7** | `SPLIT FILE`, `SELECT IF`/`FILTER`, `WEIGHT`, `SORT CASES`, `AGGREGATE`, merge | Split-file Frequencies matches SPSS |
| **8** | Legacy chart dialogs: histogram, bar, pie, scatter, boxplot, error bar | Charts render and export |
| **9** | Tier 2 procedures, parity sweep, `PARITY.md` cleanup | |

Phases 1–5 are the foundation and are non-negotiably sequential. Phase 6 parallelizes across people cleanly, since every procedure is an independent registry entry with an independent test file. That's where the group splits up.

---

## 11. Tech stack

| Layer | Choice | Note |
|---|---|---|
| Shell | Electron | `contextIsolation: true`, `nodeIntegration: false`, all privileged work in main |
| Renderer | React 18 + TypeScript | |
| State | Zustand | Redux is overkill; the sidecar holds real state |
| Styling | plain CSS modules | You are matching a Java Swing look, not building a design system. Tailwind will fight you. |
| Grid | custom virtualized | See §5.2 |
| Sidecar | Python 3.11 | |
| Stats | numpy, scipy, pandas, statsmodels, pingouin | |
| File I/O | pyreadstat (`.sav`, `.por`, `.dta`), openpyxl (`.xlsx`) | |
| Charts | matplotlib in the sidecar, returned as SVG | Keeps chart code next to the data |
| IPC | JSON-RPC 2.0 over stdio | |
| Packaging | electron-builder + PyInstaller (onedir) | |
| Testing | pytest (sidecar + parity), Vitest (renderer), Playwright (E2E) | |

### Directory layout

```
spss-clone/
├── docs/
│   ├── HLD.md                 # this file
│   ├── PARITY.md              # running divergence log
│   └── phases/PHASE-N.md
├── src/
│   ├── main/                  # Electron main
│   │   ├── index.ts
│   │   ├── menu.ts
│   │   └── sidecar.ts
│   ├── renderer/
│   │   ├── windows/{DataEditor,Viewer,SyntaxEditor}/
│   │   ├── grid/              # virtualized grid
│   │   ├── dialogs/
│   │   │   ├── shell/         # §5.3, build first
│   │   │   └── specs/         # one file per dialog
│   │   ├── output/            # PivotTable renderer
│   │   └── state/
│   └── shared/types/          # TS mirrors of the IPC contract
├── sidecar/
│   ├── server.py              # JSON-RPC loop
│   ├── data/                  # Dataset, VariableMeta, Format, missing
│   ├── io/                    # readers/writers
│   ├── syntax/                # lexer, parser, registry
│   ├── expr/                  # expression language
│   ├── procedures/            # one module per command
│   └── output/                # output model builders
└── tests/
    ├── parity/
    ├── sidecar/
    └── e2e/
```

---

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| **Numeric parity tail is unbounded.** There is always one more default that differs. | Set a stopping rule: a procedure is "done" when its parity test passes on two fixture datasets. Log the rest in `PARITY.md` and move on. |
| **Grid performance.** Naive DOM rendering dies past a few thousand rows. | Virtualize from Phase 1. Do not defer. |
| **Chart Builder is a trap.** It's a full drag-and-drop grammar-of-graphics canvas. | Explicitly out of scope. Legacy dialogs only, and they cover coursework. |
| **Sidecar packaging on macOS.** PyInstaller bundles need codesigning and notarization or Gatekeeper blocks them. | Personal use: run unsigned and add the security exception locally. Don't sink time here. |
| **Syntax bypass creep.** Under deadline, someone wires a dialog straight to a procedure. | Enforce architecturally: procedures live in a module the renderer cannot import. The only renderer-visible entry point is `syntax.execute`. |
| **Scope creep into Tier 2/3.** | Ship Tier 1 completely before starting Tier 2. A working Frequencies beats a broken MIXED. |
| **`TEMPORARY` and copy-on-write.** Easy to get wrong, easy to not notice. | Write the copy-on-write dataset semantics in Phase 1, not later. |

---

## 13. First session prompt for Claude Code

```
Read docs/HLD.md sections 2, 3, and 10.

Implement Phase 0 only:
- Electron app with main + renderer, contextIsolation on
- Python sidecar spawned by main, JSON-RPC 2.0 over stdio,
  newline-delimited
- Three windows: Data Editor (empty), Output Viewer (empty),
  Syntax Editor (plain textarea)
- Full menu bar with correct top-level items and stubbed handlers
- One working round trip: Syntax Editor "Run" sends the text to
  sidecar via syntax.execute; sidecar handles only TITLE '...'
  and returns a Title output object; Viewer renders it

Do not implement any statistics, any data model beyond a stub,
or any dialog. Stop when the round trip works.
```

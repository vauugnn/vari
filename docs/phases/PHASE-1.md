# Phase 1 — Data model, file I/O, and the two grids

**Read first:** `docs/HLD.md` sections 3 (Data model, all subsections), 5.1,
5.2 (Data View grid), 2.4 (IPC contract).

**Prerequisite:** Phase 0 acceptance criteria all pass.

## Goal

Open a real `.sav` file and see it correctly in both Data View and Variable
View. Edit it. Save it. Reopen it unchanged.

This is the largest and most important phase. Everything else in the project
sits on top of what gets built here. Take the time.

## Scope

### 1. `Format` (`sidecar/data/format.py`)

Build this first, standalone, with tests. Everything else depends on it.

A format is `TYPE` + `width` + optional `decimals`: `F8.2`, `A10`, `DATE11`,
`DOLLAR12.2`, `PCT5.1`, `COMMA10.0`, `E10.3`.

```python
class Format:
    @classmethod
    def parse(cls, s: str) -> "Format": ...
    def render(self, value) -> str: ...        # value -> display string
    def parse_input(self, s: str): ...          # display string -> value
    @classmethod
    def default_for(cls, dtype) -> "Format": ...
```

Formats drive display in the grid, in output tables, everywhere. Test the
round trip: `parse_input(render(x)) == x` for each type.

### 2. `VariableMeta` (`sidecar/data/variable.py`)

The eleven Variable View attributes, exactly as HLD 3.1 lists them: `name`,
`type`, `width`, `decimals`, `label`, `valueLabels`, `missing`, `columns`,
`align`, `measure`, `role`.

Name validation: max 64 bytes, must not start with a digit, must not be a
reserved keyword (`ALL AND BY EQ GE GT LE LT NE NOT OR TO WITH`), matching is
case-insensitive but display is case-preserving.

### 3. Missing values (`sidecar/data/missing.py`)

**Read HLD 3.3 before writing this.** It is the single easiest thing in the
project to get subtly wrong.

```python
class MissingSpec:
    # none | discrete (up to 3 values) | range(lo, hi) + optional discrete
    def matches(self, series) -> "boolean Series": ...

def missing_mask(series, meta, include_user_missing=False):
    m = series.isna()                      # system-missing
    if not include_user_missing:
        m |= meta.missing.matches(series)  # user-missing
    return m
```

User-missing values stay in the DataFrame as real values. They must survive a
round trip to `.sav`, display in Data View as their actual value, and be
includable via `MISSING=INCLUDE`. Never convert them to NaN on load.

Write a test that loads a file with user-missing codes, saves it, reloads it,
and asserts the codes are byte-identical.

### 4. `Dataset` (`sidecar/data/dataset.py`)

Holds a `pandas.DataFrame` plus a `list[VariableMeta]` in index-order
lockstep. Wrap both so structural edits update them atomically.

Operations: `insert_variable`, `delete_variable`, `rename_variable`,
`insert_case`, `delete_case`, `set_cell`, `get_rows(offset, limit)`.

Implement **copy-on-write** semantics now, even though nothing uses them
until Phase 5. `TEMPORARY` needs them, and retrofitting is painful.

`DatasetRegistry` keyed by name (`DataSet1`, `DataSet2`, ...) with an active
pointer. Needed later for merges.

### 5. File I/O (`sidecar/io/`)

`pyreadstat` for `.sav`. Read and write, with full metadata: variable labels,
value labels, missing definitions, formats, measure levels.

Also read: `.csv`, `.xlsx` (openpyxl), `.dta`, `.por`. Write: `.sav`, `.csv`,
`.xlsx`.

On CSV import, infer types and assign sensible default formats. Do not build
the full Text Import Wizard; a plain load is enough for this phase.

### 6. IPC additions

Implement the dataset methods from HLD 2.4: `dataset.open`, `dataset.save`,
`dataset.getRows`, `dataset.setCell`, `dataset.setVariableMeta`,
`dataset.insertVariable`, `dataset.deleteVariable`, `dataset.insertCase`,
`dataset.deleteCase`, `variables.list`.

`dataset.getRows` is windowed and will be called constantly by the grid. Keep
it fast and keep the payload small: send display strings already formatted by
`Format.render`, not raw values plus formatting instructions.

### 7. Variable View grid

Eleven columns, in order: Name, Type, Width, Decimals, Label, Values,
Missing, Columns, Align, Measure, Role. One row per variable.

Three cells open sub-dialogs when clicked:
- **Type** → Variable Type dialog: Numeric, Comma, Dot, Scientific notation,
  Date, Dollar, Custom currency, String, Restricted Numeric
- **Values** → Value Labels dialog: value/label pairs with Add, Change, Remove
- **Missing** → Missing Values dialog: three radio options (No missing values;
  Discrete missing values, up to 3 fields; Range plus one optional discrete)

Measure and Align are dropdowns. Editing a name validates and rejects
duplicates and reserved words.

### 8. Data View grid

**This is the biggest single UI component in the project. Read HLD 5.2.**

- Virtualized body over a windowed row cache fed by `dataset.getRows`
- Frozen column headers (variable names) and row headers (case numbers,
  1-based)
- Empty numeric cells display `.`
- Cell values rendered through `Format.render`, numerics right-aligned
- Typing into the first empty column creates `VAR00001` with format `F8.2`
- Selection: single cell, row (click row header), column (click column
  header), block drag
- A toolbar toggle switches between raw values and value labels
- Editing a cell commits on Enter or blur and calls `dataset.setCell`

Do not use a generic data-grid library. The combination of per-cell format
rendering, frozen headers, 100k+ rows, and cell-level edit state fights all of
them. Build it.

### 9. File menu

Wire up: New, Open (Data), Save, Save As, Recently Used Data. Native file
dialogs via the main process.

## Explicitly NOT in this phase

No procedures, no dialogs from the Analyze menu, no syntax parser, no
expression language, no charts, no Split File or Select Cases or Weight.

## Acceptance criteria

Use a real fixture file (any `.sav` with labelled categorical variables and
declared missing codes).

- [ ] Open a `.sav`; Data View shows correct values with correct formats
- [ ] Variable View shows all eleven columns correctly populated from file
      metadata
- [ ] Value Labels dialog shows the labels from the file
- [ ] Missing Values dialog shows the declared missing codes
- [ ] Toggling value labels swaps displayed values for labels in Data View
- [ ] Edit a cell, save, reopen: the edit persisted
- [ ] Round trip preserves user-missing codes exactly (test asserts this)
- [ ] Add a variable, set its type, label, and value labels, save, reopen:
      all metadata preserved
- [ ] Grid scrolls smoothly on a 50,000-row dataset
- [ ] Rejecting an invalid variable name (duplicate, leading digit, reserved
      word) shows an error and does not corrupt state
- [ ] `pytest` covers Format round trips, missing-mask behavior, and `.sav`
      metadata round trips

Stop here when these pass.

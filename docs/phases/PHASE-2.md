# Phase 2 — Output document model, PivotTable, export

**Read first:** HLD sections 4 (all), 2.4.

## Goal

A procedure returns a `PivotTable` object; the Viewer renders it looking like
SPSS (double outer rule, header underline, no interior vertical borders); the
outline pane lists it; it exports to HTML.

## Scope

- `sidecar/output/model.py`: `PivotTable`, `Dimension`, `Cell`, `Title`,
  `Notes`, `TextBlock`, `Warning`. Nested row/column dimensions. `to_json`.
  Numeric cells are pre-rendered to display strings via `Format` (parity lives
  in the sidecar).
- A builder helper (`simple_table`) so procedures emit tables in a few lines.
- A demo command `PIVOTDEMO.` in `syntax.execute` that emits a realistic
  Descriptive-Statistics-shaped table, so the renderer can be verified before
  real procedures exist.
- Renderer `output/PivotTable.tsx` + TableLook CSS. Handles nested dimensions
  with correct header spans.
- Viewer: outline lists Title + each PivotTable; clicking scrolls to it.
- Export the whole output document to a self-contained HTML file (File ▸ Export
  or a Viewer button), via a tree walker.

## Acceptance

- [ ] `PIVOTDEMO.` renders a multi-column table with SPSS TableLook
- [ ] Nested column dimensions render with correct spanning headers
- [ ] Outline lists the table; clicking scrolls to it
- [ ] Export produces a standalone HTML file that opens in a browser
- [ ] pytest covers `PivotTable.to_json` and the builder

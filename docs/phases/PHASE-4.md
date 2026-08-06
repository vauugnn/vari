# Phase 4 (core) — Syntax engine + first procedures

**Read first:** HLD sections 8 (lexer/parser/registry), 6 (Tier 1), 9 (parity).

Built ahead of the dialog shell so that "everything routes through syntax" is
true from the first procedure (HLD 2.2).

## Delivered

- `sidecar/syntax/lexer.py`: split a buffer into commands, split subcommands,
  expand variable lists (TO / ALL), quote handling, `/* */` comments.
- `sidecar/syntax/registry.py`: `Registry` (resolve by name or unambiguous
  prefix — FREQ → FREQUENCIES), `Procedure` / `DataProcedure` base,
  `execute_syntax` dispatcher, `Context`.
- `sidecar/procedures/`: `stats.py` (SPSS-parity descriptive stats),
  `frequencies.py`, `descriptives.py`, `nonproc.py` (TITLE, GET, SAVE,
  PIVOTDEMO), `registry.py` (builds the command table).
- `syntax.execute` now runs through the engine. GET FILE changing the active
  dataset emits an internal `_DatasetChanged` object the main process turns
  into a Data Editor refresh.

## Not yet (later phases)

Syntax Editor autocomplete, the journal file, and the general grammar for every
non-procedure command (only TITLE/GET/SAVE exist). Expression language (COMPUTE,
RECODE, IF) is Phase 5. Remaining Tier 1 procedures are Phase 6.

## Acceptance

- [x] Typed `FREQUENCIES VARIABLES=gender /STATISTICS=MEAN.` runs and renders
- [x] Abbreviations resolve (FREQ, DESC)
- [x] User-missing excluded from stats, reported as Missing in the freq table
- [x] pytest covers the pipeline and the two procedures

# PARITY.md

Running log of every place our output diverged from real SPSS, and how it was
resolved. Append as you go. This becomes the most valuable file in the repo.

Known divergences that have not yet been hit are listed in `docs/HLD.md`
section 9. Move them here as they come up, with the actual fix.

## Format

| Procedure | Symptom | Cause | Fix | Status |
|---|---|---|---|---|
| (example) T-TEST | Levene's F off by ~0.4 | scipy defaults `center='median'`; SPSS centers on the mean | pass `center='mean'` | resolved |

## Open

These are implemented but not yet verified against a real SPSS export (no
licensed SPSS available in this environment). Confirm and move to Resolved when
a fixture's SPSS output is on hand.

| Procedure | Item | Our behavior | Note |
|---|---|---|---|
| FREQUENCIES | Percentiles / Median | HAVERAGE — weighted average at rank `(n+1)p` | Matches SPSS default definition; not yet cross-checked numerically. |
| FREQUENCIES | Frequency table layout | Flat rows (value labels + Total, then Missing values, then grand Total) | SPSS nests a Valid/Missing/Total group column; our product-grid table can't render ragged groups, so the grouping is flattened. Values/percents match; visual nesting differs. |
| DESCRIPTIVES | Decimal places | Min/Max/Sum/Range use the variable's own decimals; Mean/Std.Dev use `max(varDecimals, 2)` | SPSS's per-cell decimal rules are more elaborate; revisit with a parity fixture. |
| FREQUENCIES/DESCRIPTIVES | Skewness/Kurtosis | G1/G2 with SES/SEK per HLD 9 formulas | Formula matches SPSS; not yet numerically cross-checked. |

## Resolved

_Nothing yet._

## Fixture datasets

Track which `.sav` files are used as parity fixtures and where the expected
SPSS output came from.

| Fixture | Source | SPSS version used | Expected output file |
|---|---|---|---|
| | | | |

## Stopping rule

A procedure is "done" when its parity test passes on two fixture datasets.
Remaining known-but-unhit divergences get logged under Open and left there.
Do not chase the tail before Tier 1 is complete.

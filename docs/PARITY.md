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

_Nothing yet._

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

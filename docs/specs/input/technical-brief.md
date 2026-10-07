# Version history: technical brief

## Document
A "document" is the working state of one dataset window: dataset (data + variable metadata),
syntax editor text, output items. Identity: `source_path` if saved, else a generated id kept for the session.

## Storage (sidecar owns it)
`<userData>/history/<doc-id>/`
- `index.json`: ordered list of versions `{id, time, kind: auto|save|manual|pre-op|restore, name, summary}`
- `<id>.vsnap`: a ZIP holding `data.pkl.gz` (DataFrame), `variables.json`, `syntax.txt`, `output.json`.
  Pickle is used because the files are written and read only by this app on this machine.
- Content hash of the state; an unchanged state is never stored twice.

## Triggers
- Autosave: every 5 min while the dataset's change counter has advanced.
- Save (data), "Save version" (named), before destructive commands (SELECT IF, SAMPLE, DELETE/recode-in-place), on restore.

## Retention
Keep everything from the last hour; then one per hour for a day; then one per day for 30 days;
named versions and `save` versions are never pruned. A size cap (default 1 GB per document) prunes oldest unnamed first.

## Operations (JSON-RPC)
`history.list`, `history.create`, `history.name`, `history.diff(a, b|current)`, `history.restore`, `history.delete`.
Restore always creates a `restore` snapshot of the current state first.

## Diff
Variables added / removed / renamed / metadata changed; case count change; number of changed cells (same
shape only, first 5 examples); syntax line diff; output item count. Cheap, computed on demand.

## Crash recovery
An `unclean` marker is written on start and cleared on clean exit. If found at launch, offer the newest autosave.

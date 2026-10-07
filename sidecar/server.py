"""SPSS-clone compute sidecar.

JSON-RPC 2.0 over newline-delimited stdin/stdout. Logs to stderr only.
Run as a package module so `sidecar/io` does not shadow stdlib `io`:

    python -m sidecar.server

Phase 0 methods: ping, syntax.execute (TITLE only — not a real parser yet).
Phase 1 methods: the dataset.* family + variables.list (HLD 2.4).
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any, Optional

from .data.dataset import Dataset, DatasetRegistry
from .data.format import Format
from .data.missing import MissingSpec
from .data.variable import VariableMeta
from .history import HistoryError, HistoryStore, doc_id_for
from .io.files import import_text, open_file, save_file
from .procedures.registry import build_registry
from .syntax.registry import Context, execute_syntax

REGISTRY = DatasetRegistry()
PROC_REGISTRY = build_registry()

# ---- version history (see sidecar/history.py) ----
_HISTORY: Optional[HistoryStore] = None
# Syntax text and output live in the app's other windows; the app passes them along when it
# snapshots, and we remember the latest so automatic snapshots (before destructive commands) include them.
_CONTEXT: dict[str, Any] = {"syntax": "", "output": []}
# Commands that rewrite or drop data. A safety snapshot is taken before they run.
_DESTRUCTIVE = re.compile(
    r"^\s*(SELECT\s+IF|SAMPLE|DELETE\s+VARIABLES|RECODE|FLIP|MATCH\s+FILES|ADD\s+FILES|AGGREGATE|"
    r"CASESTOVARS|VARSTOCASES|SORT\s+CASES)\b",
    re.IGNORECASE | re.MULTILINE,
)


def _store() -> HistoryStore:
    global _HISTORY
    if _HISTORY is None:
        import os
        from pathlib import Path

        root = os.environ.get("VARI_HISTORY_DIR") or str(Path.home() / ".vari" / "history")
        _HISTORY = HistoryStore(root)
    return _HISTORY


def _doc_id(ds: Dataset) -> str:
    if ds.source_path:
        return doc_id_for(ds.source_path)
    if not getattr(ds, "history_id", None):
        ds.history_id = doc_id_for(None)  # type: ignore[attr-defined]
    return ds.history_id  # type: ignore[attr-defined]


def _remember_context(p: Any) -> None:
    if isinstance(p, dict):
        if isinstance(p.get("syntax"), str):
            _CONTEXT["syntax"] = p["syntax"]
        if isinstance(p.get("output"), list):
            _CONTEXT["output"] = p["output"]


def _auto_snapshot(kind: str, name: Optional[str] = None, force: bool = False) -> Optional[dict[str, Any]]:
    """Best effort: history must never get in the way of the user's work."""
    ds = REGISTRY.active
    if ds is None or (kind in ("auto", "pre-op") and ds.n_vars == 0):
        return None  # nothing worth keeping in a blank document
    try:
        return _store().create(_doc_id(ds), ds, _CONTEXT["syntax"], _CONTEXT["output"], kind=kind, name=name, force=force)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"[sidecar] history snapshot failed: {exc}\n")
        return None


# ---- variable metadata (de)serialization ------------------------------
def _meta_to_json(v: VariableMeta) -> dict[str, Any]:
    return {
        "name": v.name,
        "type": v.type_label,
        "format": v.print_format.to_spss(),
        "width": v.width,
        "decimals": v.decimals,
        "label": v.label,
        "valueLabels": [{"value": val, "label": lab} for val, lab in v.value_labels.items()],
        "missing": v.missing.to_json(),
        "columns": v.columns,
        "align": v.align,
        "measure": v.measure,
        "role": v.role,
        "isString": v.is_string,
    }


def _meta_from_json(d: dict[str, Any]) -> VariableMeta:
    try:
        fmt = Format.parse(d["format"]) if d.get("format") else Format("F", 8, 2)
    except (ValueError, KeyError):
        fmt = Format("F", 8, 2)
    vlabels = {item["value"]: item["label"] for item in d.get("valueLabels", [])}
    return VariableMeta(
        name=d["name"],
        print_format=fmt,
        label=d.get("label", ""),
        value_labels=vlabels,
        missing=MissingSpec.from_json(d.get("missing")),
        columns=int(d.get("columns", fmt.width)),
        align=d.get("align", "right"),
        measure=d.get("measure", "scale"),
        role=d.get("role", "input"),
    )


def _dataset_summary(ds: Dataset) -> dict[str, Any]:
    return {
        "name": ds.name,
        "nRows": ds.n_rows,
        "nVars": ds.n_vars,
        "sourcePath": ds.source_path,
        "variables": [_meta_to_json(v) for v in ds.variables],
        "weight": getattr(ds, "weight_var", None),
        "filter": getattr(ds, "filter_var", None),
        "split": getattr(ds, "split_vars", None) or [],
    }


def _active() -> Dataset:
    ds = REGISTRY.active
    if ds is None:
        raise RuntimeError("No active dataset.")
    return ds


# ---- undo / redo (bounded in-place snapshot history of the active dataset) ----
_UNDO: list[Any] = []
_REDO: list[Any] = []
_MAX_HISTORY = 200
_MAX_UNDO_BYTES = 400 * 1024 * 1024  # total memory the undo stack may hold


def _snap_bytes(snap: Any) -> int:
    try:
        return int(snap.df.memory_usage(deep=False).sum())
    except Exception:  # noqa: BLE001
        return 0


def _trim_undo() -> None:
    """Keep the undo stack within the step limit and the memory budget (oldest steps go first,
    but the most recent step is always kept)."""
    while len(_UNDO) > _MAX_HISTORY:
        _UNDO.pop(0)
    total = sum(_snap_bytes(s) for s in _UNDO)
    while len(_UNDO) > 1 and total > _MAX_UNDO_BYTES:
        total -= _snap_bytes(_UNDO.pop(0))


def _snapshot_active() -> Any:
    ds = REGISTRY.active
    return ds.snapshot() if ds is not None else None


def _push_undo() -> None:
    snap = _snapshot_active()
    if snap is None:
        return
    _UNDO.append(snap)
    _trim_undo()
    _REDO.clear()


def _restore(snap: Any) -> None:
    ds = REGISTRY.active
    if ds is None or snap is None:
        return
    ds.df = snap.df
    ds.variables = snap.variables
    ds.name = snap.name


def m_dataset_undo(_p: Any) -> dict[str, Any]:
    if not _UNDO:
        return {"ok": False, **_dataset_summary(_active())}
    _REDO.append(_snapshot_active())
    _restore(_UNDO.pop())
    return {"ok": True, **_dataset_summary(_active())}


def m_dataset_redo(_p: Any) -> dict[str, Any]:
    if not _REDO:
        return {"ok": False, **_dataset_summary(_active())}
    _UNDO.append(_snapshot_active())
    _restore(_REDO.pop())
    return {"ok": True, **_dataset_summary(_active())}


# ---- methods ----------------------------------------------------------
def m_ping(_p: Any) -> dict[str, Any]:
    return {"ok": True}


def m_syntax_execute(p: Any) -> list[dict[str, Any]]:
    text = str(p.get("text", "")) if isinstance(p, dict) else str(p or "")
    before = REGISTRY.active
    if before is not None and _DESTRUCTIVE.search(text):
        _auto_snapshot("pre-op")
    pre = _snapshot_active()  # captured in case the command mutates in place
    ctx = Context(REGISTRY)
    outputs = execute_syntax(text, PROC_REGISTRY, ctx)
    # If a command changed the active dataset (opened one, or a transform mutated
    # it in place), tell the client so the Data Editor refreshes.
    after = REGISTRY.active
    changed = after is not None and (after is not before or ctx.data_changed)
    if changed:
        if after is before and pre is not None:  # in-place mutation is undoable
            _UNDO.append(pre)
            _trim_undo()
            _REDO.clear()
        outputs.append({"type": "_DatasetChanged", "summary": _dataset_summary(after)})
    return outputs


def m_dataset_new(_p: Any) -> dict[str, Any]:
    import pandas as pd

    ds = Dataset(pd.DataFrame(), [], name=REGISTRY.next_name())
    REGISTRY.add(ds, activate=True)
    return _dataset_summary(ds)


def m_dataset_open(p: dict[str, Any]) -> dict[str, Any]:
    path = p["path"]
    ds = open_file(path, name=REGISTRY.next_name())
    REGISTRY.add(ds, activate=True)
    _CONTEXT.update(syntax="", output=[])
    _auto_snapshot("open", "Opened file")  # the original is always one click away
    return _dataset_summary(ds)


def m_dataset_import_text(p: dict[str, Any]) -> dict[str, Any]:
    ds = import_text(p["path"], p.get("options", {}), name=REGISTRY.next_name())
    REGISTRY.add(ds, activate=True)
    return _dataset_summary(ds)


def m_dataset_open_database(p: dict[str, Any]) -> dict[str, Any]:
    from .io.files import open_database

    ds = open_database(str(p["conn"]), str(p["query"]), name=REGISTRY.next_name())
    REGISTRY.add(ds, activate=True)
    return _dataset_summary(ds)


def m_dataset_save(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    path = p.get("path") or ds.source_path
    if not path:
        raise RuntimeError("No path to save to.")
    save_file(ds, path)
    old_id = _doc_id(ds)
    ds.source_path = path
    _remember_context(p)
    try:
        _store().adopt(old_id, _doc_id(ds))  # an unsaved document's history follows it to its file
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"[sidecar] history adopt failed: {exc}\n")
    _auto_snapshot("save", "Saved")
    return {"ok": True, "path": path}


def m_dataset_get_rows(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    offset = int(p.get("offset", 0))
    limit = int(p.get("limit", 100))
    labels = bool(p.get("valueLabels", False))
    return {"offset": offset, "rows": ds.get_rows(offset, limit, labels), "nRows": ds.n_rows}


def m_dataset_set_cell(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    _push_undo()
    ds.set_cell(int(p["row"]), int(p["col"]), str(p.get("value", "")))
    return {"ok": True}


def m_dataset_set_variable_meta(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    _push_undo()
    ds.set_variable_meta(int(p["index"]), _meta_from_json(p["meta"]))
    return _dataset_summary(ds)


def m_dataset_insert_variable(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    _push_undo()
    if p.get("meta"):
        meta = _meta_from_json(p["meta"])
        ds.insert_variable(int(p.get("index", ds.n_vars)), meta)
    else:
        ds.append_empty_variable()
    return _dataset_summary(ds)


def m_dataset_delete_variable(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    _push_undo()
    ds.delete_variable(int(p["index"]))
    return _dataset_summary(ds)


def m_dataset_insert_case(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    _push_undo()
    ds.insert_case(int(p.get("index", ds.n_rows)))
    return {"ok": True, "nRows": ds.n_rows}


def m_dataset_delete_case(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    _push_undo()
    ds.delete_case(int(p["index"]))
    return {"ok": True, "nRows": ds.n_rows}


def m_output_export_excel(p: dict[str, Any]) -> dict[str, Any]:
    from .output.excel import export_xlsx

    export_xlsx(p.get("items", []), p["path"])
    return {"ok": True, "path": p["path"]}


def m_output_export_spv(p: dict[str, Any]) -> dict[str, Any]:
    from .io.spv import write_spv

    write_spv(p.get("items", []), p["path"])
    return {"ok": True, "path": p["path"]}


def m_output_open_spv(p: dict[str, Any]) -> dict[str, Any]:
    from .io.spv import read_spv

    return {"items": read_spv(p["path"])}


def m_dataset_find(p: dict[str, Any]) -> dict[str, Any]:
    """Find the next cell (row-major) at/after (row,col) whose rendered text
    contains the query. Returns {found, row, col} for the Find dialog."""
    ds = _active()
    query = str(p.get("query", ""))
    start_row = int(p.get("row", 0))
    start_col = int(p.get("col", 0))
    col_only = p.get("col_index")  # restrict to a single column when set
    if query == "":
        return {"found": False}
    q = query.lower()
    n_rows, n_vars = ds.n_rows, ds.n_vars
    cols = [int(col_only)] if col_only is not None else list(range(n_vars))
    for r in range(start_row, n_rows):
        for c in cols:
            if r == start_row and c < start_col and col_only is None:
                continue
            v = ds.variables[c]
            text = ds._render_cell(v, ds.df.iat[r, c], False)
            if q in str(text).lower():
                return {"found": True, "row": r, "col": c}
    return {"found": False}


def m_script_run(p: dict[str, Any]) -> dict[str, Any]:
    """Run a Python script with the active dataset's DataFrame in scope (`df`),
    plus pandas as `pd` and numpy as `np`. Captured stdout is returned. If the
    script rebinds `df`, the active dataset adopts the new frame (columns become
    new variables). This is Vari's own scripting surface, not IBM's plugin API.
    """
    import contextlib
    import io as _io

    import numpy as np
    import pandas as pd

    ds = REGISTRY.active
    code = str(p.get("code", ""))
    buf = _io.StringIO()
    env: dict[str, Any] = {"pd": pd, "np": np, "df": (ds.df if ds is not None else pd.DataFrame()), "ds": ds}
    cols_before = list(ds.df.columns) if ds is not None else []
    changed = False
    try:
        _push_undo()
        with contextlib.redirect_stdout(buf):
            exec(code, env)  # noqa: S102 — local personal scripting surface
        new_df = env.get("df")
        # A change means either df was rebound, or its columns changed in place.
        cols_after = list(new_df.columns) if isinstance(new_df, pd.DataFrame) else cols_before
        if ds is not None and isinstance(new_df, pd.DataFrame) and (new_df is not ds.df or cols_after != cols_before):
            from .data.variable import VariableMeta
            from .data.format import Format

            ds.df = new_df.reset_index(drop=True)
            existing = {v.name: v for v in ds.variables}
            metas = []
            for col in ds.df.columns:
                if col in existing:
                    metas.append(existing[col])
                elif ds.df[col].dtype == object:
                    metas.append(VariableMeta(name=str(col), print_format=Format("A", 16), measure="nominal", align="left"))
                else:
                    metas.append(VariableMeta(name=str(col), print_format=Format("F", 8, 2)))
            ds.variables = metas
            ds._sync_columns()
            changed = True
    except Exception as exc:  # noqa: BLE001
        if not changed:
            _UNDO.pop() if _UNDO else None
        return {"output": buf.getvalue(), "error": str(exc)}
    if not changed and _UNDO:
        _UNDO.pop()  # nothing mutated; discard the snapshot
    out: dict[str, Any] = {"output": buf.getvalue(), "error": None}
    if changed:
        out["summary"] = _dataset_summary(ds)
    return out


def m_variables_list(_p: Any) -> list[dict[str, Any]]:
    ds = REGISTRY.active
    if ds is None:
        return []
    return [_meta_to_json(v) for v in ds.variables]


def m_history_list(_p: Any) -> dict[str, Any]:
    ds = _active()
    doc = _doc_id(ds)
    return {"docId": doc, "versions": _store().list(doc)}


def m_history_create(p: Any) -> dict[str, Any]:
    _remember_context(p)
    p = p if isinstance(p, dict) else {}
    kind = p.get("kind", "auto")
    v = _auto_snapshot(kind, p.get("name") or None, force=kind not in ("auto", "pre-op"))
    return {"version": v}


def m_history_rename(p: dict[str, Any]) -> dict[str, Any]:
    return {"version": _store().rename(_doc_id(_active()), p["id"], str(p.get("name", "")))}


def m_history_delete(p: dict[str, Any]) -> dict[str, Any]:
    _store().delete(_doc_id(_active()), p["id"])
    return {"ok": True}


def _current_state(p: Any) -> dict[str, Any]:
    _remember_context(p)
    ds = _active()
    return {"payload": {"df": ds.df, "variables": ds.variables}, "syntax": _CONTEXT["syntax"], "output": _CONTEXT["output"]}


def m_history_diff(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    b = p.get("b")
    current = _current_state(p) if b in (None, "current") else None
    return _store().diff(_doc_id(ds), p["a"], None if b in (None, "current") else b, current=current)


def m_history_restore(p: dict[str, Any]) -> dict[str, Any]:
    """Go back to a version. The current state is saved first, so a restore can be undone."""
    ds = _active()
    _remember_context(p)
    doc = _doc_id(ds)
    state = _store().load(doc, p["id"])  # fail before touching anything if it cannot be read
    _auto_snapshot("restore", "Before restoring an earlier version", force=True)
    _push_undo()
    pl = state["payload"]
    ds.df = pl["df"].reset_index(drop=True)
    ds.variables = pl["variables"]
    ds.weight_var = pl.get("weight_var")
    ds.filter_var = pl.get("filter_var")
    ds.split_vars = pl.get("split_vars") or []
    _CONTEXT.update(syntax=state["syntax"], output=state["output"])
    return {"summary": _dataset_summary(ds), "syntax": state["syntax"], "output": state["output"]}


def m_history_recover(_p: Any) -> dict[str, Any]:
    """After an unclean exit: the newest saved version of any document, if there is one."""
    found = _store().newest()
    if found is None:
        return {"found": False}
    doc, v = found
    return {"found": True, "docId": doc, "version": v}


def m_history_open_version(p: dict[str, Any]) -> dict[str, Any]:
    """Open a version as a new dataset, leaving whatever is open untouched."""
    state = _store().load(p["docId"], p["id"])
    pl = state["payload"]
    ds = Dataset(pl["df"].reset_index(drop=True), pl["variables"], name=REGISTRY.next_name(), source_path=pl.get("source_path"))
    ds.weight_var = pl.get("weight_var")
    ds.filter_var = pl.get("filter_var")
    ds.split_vars = pl.get("split_vars") or []
    REGISTRY.add(ds, activate=True)
    _CONTEXT.update(syntax=state["syntax"], output=state["output"])
    return {"summary": _dataset_summary(ds), "syntax": state["syntax"], "output": state["output"]}


METHODS = {
    "history.recover": m_history_recover,
    "history.openVersion": m_history_open_version,
    "history.list": m_history_list,
    "history.create": m_history_create,
    "history.rename": m_history_rename,
    "history.delete": m_history_delete,
    "history.diff": m_history_diff,
    "history.restore": m_history_restore,
    "ping": m_ping,
    "syntax.execute": m_syntax_execute,
    "dataset.new": m_dataset_new,
    "dataset.open": m_dataset_open,
    "dataset.importText": m_dataset_import_text,
    "dataset.openDatabase": m_dataset_open_database,
    "dataset.save": m_dataset_save,
    "dataset.getRows": m_dataset_get_rows,
    "dataset.setCell": m_dataset_set_cell,
    "dataset.setVariableMeta": m_dataset_set_variable_meta,
    "dataset.insertVariable": m_dataset_insert_variable,
    "dataset.deleteVariable": m_dataset_delete_variable,
    "dataset.insertCase": m_dataset_insert_case,
    "dataset.deleteCase": m_dataset_delete_case,
    "dataset.undo": m_dataset_undo,
    "dataset.redo": m_dataset_redo,
    "dataset.find": m_dataset_find,
    "script.run": m_script_run,
    "output.exportSpv": m_output_export_spv,
    "output.openSpv": m_output_open_spv,
    "variables.list": m_variables_list,
    "output.exportExcel": m_output_export_excel,
}


def dispatch(req: dict[str, Any]) -> dict[str, Any]:
    rid = req.get("id")
    method = req.get("method")
    params = req.get("params")
    resp: dict[str, Any] = {"jsonrpc": "2.0", "id": rid}
    fn = METHODS.get(method) if isinstance(method, str) else None
    if fn is None:
        resp["error"] = {"code": -32601, "message": f"Method not found: {method}"}
        return resp
    try:
        resp["result"] = fn(params)
    except Exception as exc:  # noqa: BLE001 — report any failure as a JSON-RPC error
        resp["error"] = {"code": -32603, "message": f"{type(exc).__name__}: {exc}"}
    return resp


def _json_safe(obj: Any) -> Any:
    """Replace non-finite floats (inf/nan, e.g. LO/HI missing bounds) with None
    so the emitted line is valid JSON that Node's JSON.parse accepts."""
    import math

    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    return obj


def main() -> None:
    print("[sidecar] ready", file=sys.stderr, flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"[sidecar] bad JSON: {exc}\n")
            sys.stderr.flush()
            continue
        if not isinstance(req, dict):
            continue
        resp = _json_safe(dispatch(req))
        sys.stdout.write(json.dumps(resp, allow_nan=False) + "\n")
        sys.stdout.flush()


# Optional: syntax.execute keeps working when this file is imported directly
# (kept for the Phase 0 test that imports syntax_execute).
syntax_execute = m_syntax_execute


if __name__ == "__main__":
    main()

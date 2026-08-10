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
from .io.files import import_text, open_file, save_file
from .procedures.registry import build_registry
from .syntax.registry import Context, execute_syntax

REGISTRY = DatasetRegistry()
PROC_REGISTRY = build_registry()


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
_MAX_HISTORY = 25


def _snapshot_active() -> Any:
    ds = REGISTRY.active
    return ds.snapshot() if ds is not None else None


def _push_undo() -> None:
    snap = _snapshot_active()
    if snap is None:
        return
    _UNDO.append(snap)
    if len(_UNDO) > _MAX_HISTORY:
        _UNDO.pop(0)
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
            if len(_UNDO) > _MAX_HISTORY:
                _UNDO.pop(0)
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
    return _dataset_summary(ds)


def m_dataset_import_text(p: dict[str, Any]) -> dict[str, Any]:
    ds = import_text(p["path"], p.get("options", {}), name=REGISTRY.next_name())
    REGISTRY.add(ds, activate=True)
    return _dataset_summary(ds)


def m_dataset_save(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    path = p.get("path") or ds.source_path
    if not path:
        raise RuntimeError("No path to save to.")
    save_file(ds, path)
    ds.source_path = path
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


METHODS = {
    "ping": m_ping,
    "syntax.execute": m_syntax_execute,
    "dataset.new": m_dataset_new,
    "dataset.open": m_dataset_open,
    "dataset.importText": m_dataset_import_text,
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

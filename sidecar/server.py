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
from .io.files import open_file, save_file

_TITLE_RE = re.compile(
    r"""^\s*TITLE\s+(?P<q>['"])(?P<text>.*?)(?P=q)\s*\.?\s*$""",
    re.IGNORECASE | re.DOTALL,
)

REGISTRY = DatasetRegistry()


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
    fmt = Format.parse(d["format"]) if d.get("format") else Format("F", 8, 2)
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
    }


def _active() -> Dataset:
    ds = REGISTRY.active
    if ds is None:
        raise RuntimeError("No active dataset.")
    return ds


# ---- methods ----------------------------------------------------------
def m_ping(_p: Any) -> dict[str, Any]:
    return {"ok": True}


def m_syntax_execute(p: Any) -> list[dict[str, Any]]:
    text = str(p.get("text", "")) if isinstance(p, dict) else str(p or "")
    stripped = text.strip()
    m = _TITLE_RE.match(stripped)
    if m:
        return [{"type": "Title", "text": m.group("text")}]
    return [{"type": "Error", "text": f"Unrecognized command: {stripped or '(empty)'}"}]


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
    ds.set_cell(int(p["row"]), int(p["col"]), str(p.get("value", "")))
    return {"ok": True}


def m_dataset_set_variable_meta(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    ds.set_variable_meta(int(p["index"]), _meta_from_json(p["meta"]))
    return _dataset_summary(ds)


def m_dataset_insert_variable(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    if p.get("meta"):
        meta = _meta_from_json(p["meta"])
        ds.insert_variable(int(p.get("index", ds.n_vars)), meta)
    else:
        ds.append_empty_variable()
    return _dataset_summary(ds)


def m_dataset_delete_variable(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    ds.delete_variable(int(p["index"]))
    return _dataset_summary(ds)


def m_dataset_insert_case(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    ds.insert_case(int(p.get("index", ds.n_rows)))
    return {"ok": True, "nRows": ds.n_rows}


def m_dataset_delete_case(p: dict[str, Any]) -> dict[str, Any]:
    ds = _active()
    ds.delete_case(int(p["index"]))
    return {"ok": True, "nRows": ds.n_rows}


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
    "dataset.save": m_dataset_save,
    "dataset.getRows": m_dataset_get_rows,
    "dataset.setCell": m_dataset_set_cell,
    "dataset.setVariableMeta": m_dataset_set_variable_meta,
    "dataset.insertVariable": m_dataset_insert_variable,
    "dataset.deleteVariable": m_dataset_delete_variable,
    "dataset.insertCase": m_dataset_insert_case,
    "dataset.deleteCase": m_dataset_delete_case,
    "variables.list": m_variables_list,
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

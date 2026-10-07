"""Version history for a working document (data + variables + syntax text + output).

Local only, like Google Docs "version history" but never uploaded. A snapshot is one
`.vsnap` ZIP per version under `<root>/<doc-id>/`, plus an `index.json`. Snapshots are
written and read only by this app on this machine, so the data is stored as a pickle.

Spec: docs/specs/input/technical-brief.md.
"""
from __future__ import annotations

import difflib
import gzip
import hashlib
import io
import json
import os
import pickle
import re
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

SCHEMA = 1
# Kinds that retention may thin out. Everything else (and anything named) is kept forever.
PRUNABLE = {"auto", "pre-op"}
HOUR, DAY = 3600.0, 86400.0
DEFAULT_CAP_BYTES = 1 << 30  # 1 GB per document


class HistoryError(ValueError):
    pass


def doc_id_for(path: Optional[str]) -> str:
    """Stable id for a saved file (name + path hash); callers use a uuid for unsaved data."""
    if not path:
        return f"untitled-{uuid.uuid4().hex[:10]}"
    base = re.sub(r"[^A-Za-z0-9._-]", "_", Path(path).stem)[:40] or "doc"
    return f"{base}-{hashlib.sha1(os.path.abspath(path).encode()).hexdigest()[:8]}"


def _safe(doc_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", doc_id):
        raise HistoryError("invalid document id")
    return doc_id


def state_hash(ds: Any, syntax: str, output: list[dict[str, Any]]) -> str:
    h = hashlib.sha256()
    h.update(pd.util.hash_pandas_object(ds.df, index=False).values.tobytes())
    h.update(repr([ds.df.columns.tolist(), [repr(v) for v in ds.variables]]).encode())
    h.update(repr((getattr(ds, "weight_var", None), getattr(ds, "filter_var", None),
                   getattr(ds, "split_vars", None))).encode())
    h.update(syntax.encode())
    h.update(json.dumps(output, sort_keys=True, default=str).encode())
    return h.hexdigest()


class HistoryStore:
    def __init__(self, root: str | os.PathLike[str], cap_bytes: int = DEFAULT_CAP_BYTES) -> None:
        self.root = Path(root)
        self.cap = cap_bytes

    # ---- paths / index --------------------------------------------------
    def _dir(self, doc_id: str) -> Path:
        return self.root / _safe(doc_id)

    def _index(self, doc_id: str) -> list[dict[str, Any]]:
        p = self._dir(doc_id) / "index.json"
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text())
        except (OSError, ValueError):
            return self._rebuild_index(doc_id)

    def _rebuild_index(self, doc_id: str) -> list[dict[str, Any]]:
        """A damaged index must not lose history: rebuild it from the snapshot files."""
        out: list[dict[str, Any]] = []
        for f in sorted(self._dir(doc_id).glob("*.vsnap")):
            try:
                with zipfile.ZipFile(f) as z:
                    out.append(json.loads(z.read("meta.json")))
                    meta = out[-1]
                    meta["bytes"] = f.stat().st_size
            except (OSError, ValueError, KeyError, zipfile.BadZipFile):
                continue
        out.sort(key=lambda v: v["time"])
        self._write_index(doc_id, out)
        return out

    def _write_index(self, doc_id: str, index: list[dict[str, Any]]) -> None:
        d = self._dir(doc_id)
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / "index.json.tmp"
        tmp.write_text(json.dumps(index))
        os.replace(tmp, d / "index.json")

    # ---- create ---------------------------------------------------------
    def create(self, doc_id: str, ds: Any, syntax: str = "", output: Optional[list[dict[str, Any]]] = None,
               kind: str = "auto", name: Optional[str] = None, force: bool = False,
               now: Optional[float] = None) -> Optional[dict[str, Any]]:
        """Snapshot the state. Returns the new version, or None if nothing changed since
        the latest version (autosave and pre-op never store a duplicate)."""
        output = output or []
        digest = state_hash(ds, syntax, output)
        index = self._index(doc_id)
        if not force and kind in PRUNABLE and index and index[-1].get("hash") == digest:
            return None
        t = time.time() if now is None else now
        vid = f"{int(t * 1000):013d}-{digest[:6]}"
        version = {
            "id": vid, "time": t, "kind": kind, "name": name or "", "hash": digest,
            "rows": int(ds.n_rows), "vars": int(ds.n_vars), "outputItems": len(output), "bytes": 0,
        }
        d = self._dir(doc_id)
        d.mkdir(parents=True, exist_ok=True)
        buf = io.BytesIO()
        payload = {
            "schema": SCHEMA, "df": ds.df, "variables": ds.variables, "name": ds.name,
            "source_path": ds.source_path, "weight_var": getattr(ds, "weight_var", None),
            "filter_var": getattr(ds, "filter_var", None), "split_vars": getattr(ds, "split_vars", []),
        }
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("data.pkl.gz", gzip.compress(pickle.dumps(payload, protocol=pickle.HIGHEST_PROTOCOL), 3))
            z.writestr("syntax.txt", syntax)
            z.writestr("output.json", json.dumps(output, default=str))
            version["bytes"] = 0
            z.writestr("meta.json", json.dumps(version))
        data = buf.getvalue()
        version["bytes"] = len(data)
        tmp = d / f"{vid}.vsnap.tmp"
        tmp.write_bytes(data)
        os.replace(tmp, d / f"{vid}.vsnap")
        index.append(version)
        self._write_index(doc_id, index)
        self.prune(doc_id, now=t)
        return version

    # ---- list / name / delete ------------------------------------------------
    def list(self, doc_id: str) -> list[dict[str, Any]]:
        return list(reversed(self._index(doc_id)))  # newest first

    def rename(self, doc_id: str, vid: str, name: str) -> dict[str, Any]:
        index = self._index(doc_id)
        for v in index:
            if v["id"] == vid:
                v["name"] = name.strip()
                self._write_index(doc_id, index)
                return v
        raise HistoryError("version not found")

    def delete(self, doc_id: str, vid: str) -> None:
        index = [v for v in self._index(doc_id) if v["id"] != vid]
        self._write_index(doc_id, index)
        (self._dir(doc_id) / f"{vid}.vsnap").unlink(missing_ok=True)

    def adopt(self, old_id: str, new_id: str) -> None:
        """An unsaved document was saved to a file: move its history under the file's id."""
        src, dst = self._dir(old_id), self._dir(new_id)
        if not src.exists() or old_id == new_id:
            return
        dst.mkdir(parents=True, exist_ok=True)
        merged = self._index(new_id) + self._index(old_id)
        for f in src.glob("*.vsnap"):
            os.replace(f, dst / f.name)
        merged.sort(key=lambda v: v["time"])
        self._write_index(new_id, merged)
        for f in src.iterdir():
            f.unlink()
        src.rmdir()

    # ---- load ----------------------------------------------------------------
    def load(self, doc_id: str, vid: str) -> dict[str, Any]:
        f = self._dir(doc_id) / f"{vid}.vsnap"
        if not f.exists():
            raise HistoryError("version not found")
        try:
            with zipfile.ZipFile(f) as z:
                payload = pickle.loads(gzip.decompress(z.read("data.pkl.gz")))  # noqa: S301 - our own file
                syntax = z.read("syntax.txt").decode()
                output = json.loads(z.read("output.json"))
        except Exception as exc:  # noqa: BLE001
            raise HistoryError(f"This version could not be read ({type(exc).__name__}).") from exc
        if payload.get("schema") != SCHEMA:
            raise HistoryError("This version was saved by an incompatible version of Vari.")
        return {"payload": payload, "syntax": syntax, "output": output}

    # ---- retention -----------------------------------------------------------
    def prune(self, doc_id: str, now: Optional[float] = None) -> None:
        t = time.time() if now is None else now
        index = self._index(doc_id)
        keep: list[dict[str, Any]] = []
        seen: set[tuple[str, int]] = set()
        for v in reversed(index):  # newest first, so the latest of each bucket wins
            if v["kind"] not in PRUNABLE or v.get("name"):
                keep.append(v)
                continue
            age = t - v["time"]
            if age <= HOUR:
                keep.append(v)
            elif age <= DAY:
                bucket = ("h", int(v["time"] // HOUR))
            elif age <= 30 * DAY:
                bucket = ("d", int(v["time"] // DAY))
            else:
                continue  # older than 30 days: dropped
            if age > HOUR:
                if bucket in seen:
                    continue
                seen.add(bucket)
                keep.append(v)
        keep.sort(key=lambda v: v["time"])
        # Size cap: drop the oldest prunable versions until under the cap.
        total = sum(v["bytes"] for v in keep)
        for v in list(keep):
            if total <= self.cap:
                break
            if v["kind"] in PRUNABLE and not v.get("name"):
                keep.remove(v)
                total -= v["bytes"]
        kept = {v["id"] for v in keep}
        for v in index:
            if v["id"] not in kept:
                (self._dir(doc_id) / f"{v['id']}.vsnap").unlink(missing_ok=True)
        if len(keep) != len(index):
            self._write_index(doc_id, keep)

    # ---- diff ----------------------------------------------------------------
    def diff(self, doc_id: str, a: str, b: Optional[str], current: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Differences going from version `a` to version `b` (or to the `current` state)."""
        sa = self.load(doc_id, a)
        if b is None:
            if current is None:
                raise HistoryError("nothing to compare with")
            sb = current
        else:
            sb = self.load(doc_id, b)
        return diff_states(sa, sb)


def diff_states(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Compare two states shaped like HistoryStore.load()'s result."""
    pa, pb = a["payload"], b["payload"]
    va = {v.name: v for v in pa["variables"]}
    vb = {v.name: v for v in pb["variables"]}
    added = [n for n in vb if n not in va]
    removed = [n for n in va if n not in vb]
    changed_meta: list[dict[str, Any]] = []
    for n in va.keys() & vb.keys():
        for attr in ("label", "measure", "align", "role", "columns"):
            x, y = getattr(va[n], attr), getattr(vb[n], attr)
            if x != y:
                changed_meta.append({"variable": n, "field": attr, "from": x, "to": y})
        if va[n].print_format != vb[n].print_format:
            changed_meta.append({"variable": n, "field": "format", "from": va[n].print_format.to_spss(),
                                 "to": vb[n].print_format.to_spss()})
        if va[n].value_labels != vb[n].value_labels:
            changed_meta.append({"variable": n, "field": "value labels", "from": len(va[n].value_labels),
                                 "to": len(vb[n].value_labels)})
        if repr(va[n].missing) != repr(vb[n].missing):
            changed_meta.append({"variable": n, "field": "missing values", "from": "", "to": ""})
    dfa, dfb = pa["df"], pb["df"]
    cells = {"changed": 0, "examples": []}
    common = [n for n in dfa.columns if n in dfb.columns]
    if len(dfa) == len(dfb) and common:
        for n in common:
            x, y = dfa[n], dfb[n]
            if x.dtype == object or y.dtype == object:
                diff = (x.astype(str) != y.astype(str)).to_numpy()
            else:
                xa, ya = x.to_numpy(dtype=float), y.to_numpy(dtype=float)
                diff = ~((xa == ya) | (np.isnan(xa) & np.isnan(ya)))
            idx = np.flatnonzero(diff)
            cells["changed"] += int(idx.size)
            for i in idx[: max(0, 5 - len(cells["examples"]))]:
                cells["examples"].append({"case": int(i) + 1, "variable": n, "from": _show(x.iloc[i]), "to": _show(y.iloc[i])})
    sx = a["syntax"].splitlines()
    sy = b["syntax"].splitlines()
    syntax_diff = [ln for ln in difflib.unified_diff(sx, sy, "before", "after", lineterm="", n=1)][:80]
    return {
        "rows": {"from": len(dfa), "to": len(dfb)},
        "variables": {"added": added, "removed": removed, "changed": changed_meta},
        "cells": cells,
        "syntaxDiff": syntax_diff,
        "outputItems": {"from": len(a["output"]), "to": len(b["output"])},
        "identical": not (added or removed or changed_meta or cells["changed"] or syntax_diff
                          or len(dfa) != len(dfb) or len(a["output"]) != len(b["output"])),
    }


def _show(v: Any) -> Any:
    if isinstance(v, float) and v != v:
        return None
    return v.item() if hasattr(v, "item") else v

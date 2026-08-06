"""Data-menu structural commands: AGGREGATE, FLIP (Transpose), ADD FILES,
MATCH FILES (HLD 6 Data menu)."""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from ..data.dataset import Dataset
from ..data.format import Format
from ..data.variable import VariableMeta
from ..io.files import open_file
from ..syntax.lexer import expand_varlist, split_subcommands, unquote
from ..syntax.registry import Context, Procedure

_AGG = {
    "MEAN": "mean", "SUM": "sum", "SD": "std", "MIN": "min", "MAX": "max",
    "MEDIAN": "median", "FIRST": "first", "LAST": "last", "N": "count", "NU": "nunique",
}


def _active(ctx: Context) -> Any:
    ds = ctx.active
    if ds is None:
        raise RuntimeError("No active dataset.")
    return ds


def _numeric_meta(name: str) -> VariableMeta:
    return VariableMeta(name=name, print_format=Format("F", 8, 2))


class Aggregate(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        allnames = [v.name for v in ds.variables]
        mb = re.search(r"/\s*BREAK\s*=\s*([^/]*)", rest, re.IGNORECASE)
        breaks = expand_varlist(mb.group(1), allnames) if mb else []
        aggs: list[tuple[str, str, str]] = []  # (newvar, func, srcvar) — case-preserved
        for m in re.finditer(r"/\s*([A-Za-z@#$][\w@#$.]*)\s*=\s*(\w+)\s*\(([^)]*)\)", rest):
            if m.group(1).upper() in ("BREAK", "OUTFILE"):
                continue
            aggs.append((m.group(1), m.group(2).upper(), m.group(3).strip()))
        for m in re.finditer(r"/\s*([A-Za-z@#$][\w@#$.]*)\s*=\s*(N|NU)\b(?!\s*\()", rest):
            aggs.append((m.group(1), m.group(2).upper(), breaks[0] if breaks else ""))
        if not breaks or not aggs:
            return [{"type": "Error", "text": "AGGREGATE needs /BREAK and aggregate functions."}]

        grouped = ds.df.groupby(breaks, sort=True)
        out_cols: dict[str, Any] = {}
        for b in breaks:
            out_cols[b] = [k if not isinstance(k, tuple) else k[breaks.index(b)] for k in grouped.groups.keys()]
        for newvar, func, src in aggs:
            agg = _AGG.get(func, "mean")
            if func in ("N", "NU") and not src:
                out_cols[newvar] = grouped.size().to_numpy() if func == "N" else grouped.nunique().iloc[:, 0].to_numpy()
            else:
                out_cols[newvar] = grouped[src].agg(agg).to_numpy()
        newdf = pd.DataFrame(out_cols)
        variables = [ds.variables[ds._index_of(b)].copy() for b in breaks] + [_numeric_meta(nv) for nv, _, _ in aggs]
        new = Dataset(newdf, variables, name=ctx.ds_registry.next_name())
        ctx.ds_registry.add(new, activate=True)
        ctx.mark_changed()
        return []


class Flip(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        subs = split_subcommands(rest)
        variables = None
        newnames = None
        for name, body in subs:
            up = name.upper()
            if up in ("", "VARIABLES"):
                variables = expand_varlist(re.sub(r"^\s*VARIABLES\s*=?\s*", "", body, flags=re.IGNORECASE),
                                           [v.name for v in ds.variables])
            elif up == "NEWNAMES":
                newnames = expand_varlist(body, [v.name for v in ds.variables])[0]
        if variables is None:
            variables = [v.name for v in ds.variables]
        sub = ds.df[variables]
        transposed = sub.T
        if newnames:
            cols = [str(x) for x in ds.df[newnames].tolist()]
        else:
            cols = [f"var{i + 1}" for i in range(transposed.shape[1])]
        transposed.columns = _unique(cols)
        transposed.insert(0, "CASE_LBL", variables)
        metas = [VariableMeta(name="CASE_LBL", print_format=Format("A", 8), measure="nominal", align="left")]
        metas += [_numeric_meta(c) for c in transposed.columns[1:]]
        new = Dataset(transposed.reset_index(drop=True), metas, name=ctx.ds_registry.next_name())
        ctx.ds_registry.add(new, activate=True)
        ctx.mark_changed()
        return []


class AddFiles(Procedure):
    """ADD FILES — append cases from another file to the active dataset."""

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        frames = [ds.df]
        for path in _file_paths(rest):
            frames.append(open_file(path).df)
        ds.df = pd.concat(frames, ignore_index=True)
        ctx.mark_changed()
        return []


class MatchFiles(Procedure):
    """MATCH FILES ... /BY key — merge variables from another file by key."""

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        m = re.search(r"/BY\s+(.+)$", rest, re.IGNORECASE)
        keys = expand_varlist(m.group(1), [v.name for v in ds.variables]) if m else []
        others = [open_file(p) for p in _file_paths(rest)]
        merged = ds.df
        added: list[VariableMeta] = []
        for od in others:
            if keys:
                merged = merged.merge(od.df, on=keys, how="left", suffixes=("", "_y"))
            else:
                merged = pd.concat([merged, od.df], axis=1)
            for v in od.variables:
                if v.name not in [x.name for x in ds.variables] and v.name in merged.columns:
                    added.append(v.copy())
        merged = merged.loc[:, ~merged.columns.duplicated()]
        ds.variables = [v for v in ds.variables if v.name in merged.columns] + \
                       [v for v in added if v.name in merged.columns and v.name not in [x.name for x in ds.variables]]
        # keep column order consistent with variables
        ds.df = merged[[v.name for v in ds.variables]]
        ctx.mark_changed()
        return []


class AddCmd(Procedure):
    """Routes ADD FILES vs ADD VALUE LABELS."""

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        if re.match(r"\s*FILES", rest, re.IGNORECASE):
            return AddFiles().execute(rest, ctx)
        from .metadata import ValueLabels

        return ValueLabels(add=True).execute(rest, ctx)


def _file_paths(rest: str) -> list[str]:
    paths = []
    for m in re.finditer(r"FILE\s*=\s*(\*|'[^']*'|\"[^\"]*\")", rest, re.IGNORECASE):
        tok = m.group(1)
        if tok != "*":
            paths.append(unquote(tok) or tok)
    return paths


def _unique(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for n in names:
        if n in seen:
            seen[n] += 1
            out.append(f"{n}_{seen[n]}")
        else:
            seen[n] = 0
            out.append(n)
    return out

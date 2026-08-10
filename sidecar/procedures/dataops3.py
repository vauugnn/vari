"""Restructure (VARSTOCASES wide->long, CASESTOVARS long->wide) and Visual
Binning (VBIN). VARSTOCASES/CASESTOVARS build a new active dataset; VBIN adds a
binned variable to the active one."""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from ..data.dataset import Dataset
from ..data.format import Format
from ..data.variable import VariableMeta
from ..syntax.lexer import expand_varlist, split_subcommands
from ..syntax.registry import Context, Procedure


def _active(ctx: Context) -> Any:
    ds = ctx.active
    if ds is None:
        raise RuntimeError("No active dataset.")
    return ds


def _numeric_meta(name: str) -> VariableMeta:
    return VariableMeta(name=name, print_format=Format("F", 8, 2))


class VarsToCases(Procedure):
    """VARSTOCASES /MAKE newvar FROM v1 v2 ... [/INDEX=idx] — wide to long."""

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        subs = split_subcommands(rest)
        allnames = [v.name for v in ds.variables]
        make = "trans1"
        sources: list[str] = []
        index = "Index1"
        for name, body in subs:
            up = name.upper()
            if up == "MAKE":
                m = re.match(r"\s*(\w+)\s+FROM\s+(.+)", body, re.IGNORECASE)
                if m:
                    make = m.group(1)
                    sources = expand_varlist(m.group(2), allnames)
            elif up == "INDEX":
                index = re.match(r"\s*(\w+)", body).group(1) if re.match(r"\s*(\w+)", body) else index
        if not sources:
            return [{"type": "Error", "text": "VARSTOCASES needs /MAKE newvar FROM var list."}]
        keep = [n for n in allnames if n not in sources]
        long = ds.df.melt(id_vars=keep, value_vars=sources, var_name=index, value_name=make)
        # index becomes 1..k in the order given
        order = {v: i + 1 for i, v in enumerate(sources)}
        long[index] = long[index].map(order).astype(float)
        metas = [_meta_for(ds, n) for n in keep] + [_numeric_meta(index), _numeric_meta(make)]
        new = Dataset(long.reset_index(drop=True), metas, name=ctx.ds_registry.next_name())
        ctx.ds_registry.add(new, activate=True)
        ctx.mark_changed()
        return []


class CasesToVars(Procedure):
    """CASESTOVARS /ID=id /INDEX=idx — long to wide."""

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        subs = split_subcommands(rest)
        allnames = [v.name for v in ds.variables]
        idv = idxv = None
        for name, body in subs:
            up = name.upper()
            if up == "ID":
                idv = expand_varlist(body, allnames)[0]
            elif up == "INDEX":
                idxv = expand_varlist(body, allnames)[0]
        if idv is None or idxv is None:
            return [{"type": "Error", "text": "CASESTOVARS needs /ID=id /INDEX=index."}]
        value_cols = [n for n in allnames if n not in (idv, idxv)]
        wide = ds.df.pivot_table(index=idv, columns=idxv, values=value_cols, aggfunc="first")
        wide.columns = [f"{a}.{int(b) if float(b).is_integer() else b}" for a, b in wide.columns]
        wide = wide.reset_index()
        metas = [_meta_for(ds, idv)] + [_numeric_meta(c) for c in wide.columns[1:]]
        new = Dataset(wide, metas, name=ctx.ds_registry.next_name())
        ctx.ds_registry.add(new, activate=True)
        ctx.mark_changed()
        return []


class VisualBin(Procedure):
    """VBIN var INTO newvar /BINS n [/METHOD EQUAL|RANK] — bin a scale variable."""

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        from .transforms import _set_column

        ds = _active(ctx)
        subs = split_subcommands(rest)
        allnames = [v.name for v in ds.variables]
        src = target = None
        nbins = 4
        method = "EQUAL"
        for name, body in subs:
            up = name.upper()
            if up in ("", "VARIABLES"):
                m = re.match(r"\s*(\w+)\s+INTO\s+(\w+)", body, re.IGNORECASE)
                if m:
                    src, target = m.group(1), m.group(2)
                else:
                    got = expand_varlist(body, allnames)
                    if got:
                        src = got[0]
            elif up == "BINS":
                mm = re.search(r"\d+", body)
                if mm:
                    nbins = int(mm.group())
            elif up == "METHOD":
                method = body.strip().upper() or "EQUAL"
        if src is None:
            return [{"type": "Error", "text": "VBIN needs 'var INTO newvar /BINS n'."}]
        if target is None:
            target = f"{src}_bin"[:60]
        x = ds.df[src].to_numpy(float)
        valid = ~np.isnan(x)
        out = np.full(len(x), np.nan)
        if method == "RANK":
            ranks = pd.Series(x[valid]).rank(method="average").to_numpy()
            out[valid] = np.ceil(ranks / len(ranks) * nbins)
        else:
            edges = np.linspace(np.nanmin(x), np.nanmax(x), nbins + 1)
            out[valid] = np.clip(np.digitize(x[valid], edges[1:-1]) + 1, 1, nbins)
        _set_column(ds, target, out)
        ctx.mark_changed()
        return []


def _meta_for(ds: Any, name: str) -> VariableMeta:
    idx = ds._index_of(name)
    return ds.variables[idx].copy()

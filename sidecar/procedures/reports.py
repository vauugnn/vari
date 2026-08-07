"""SUMMARIZE (Case Summaries) and CODEBOOK — Reports menu, Base."""
from __future__ import annotations

import re
from typing import Any

import numpy as np

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure
from . import stats
from .base import numeric_valid, value_label

_F2 = Format("F", 8, 2)
_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)


class Summarize(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = ""
        for name, b in subs:
            if name in ("", "TABLES", "VARIABLES"):
                body += " " + re.sub(r"^\s*TABLES\s*=?\s*", "", b, flags=re.IGNORECASE)
        allnames = [v.name for v in ds.variables]
        m = re.search(r"(.+?)\bBY\b(.+)", body, re.IGNORECASE)
        if m:
            deps = expand_varlist(m.group(1), allnames)
            factor = expand_varlist(m.group(2), allnames)[0]
        else:
            deps = expand_varlist(body, allnames)
            factor = None

        if factor is None:
            rows = ["Total"]
            groups = {"Total": None}
        else:
            fmask = missing_mask(ds.df[factor], ds.variables[ds._index_of(factor)]).to_numpy()
            levels = sorted(set(ds.df[factor].to_numpy(float)[~fmask]))
            rows = [value_label(ds, factor, lv) for lv in levels] + ["Total"]
            groups = {value_label(ds, factor, lv): lv for lv in levels}
            groups["Total"] = None

        col_cats = []
        for d in deps:
            col_cats += [f"{d}|Mean", f"{d}|N", f"{d}|Std. Deviation"]
        t = PivotTable("Case Summaries", [Dimension(factor or "", rows)], [Dimension("", col_cats)],
                       corner=factor or "")
        for ri, (lbl, lv) in enumerate(groups.items()):
            for di, d in enumerate(deps):
                x = self._values(ds, d, factor, lv)
                t.set([ri], [di * 3 + 0], _F2.render(stats.mean(x)) if stats.n_valid(x) else ".")
                t.set([ri], [di * 3 + 1], _F0.render(stats.n_valid(x)))
                t.set([ri], [di * 3 + 2], _F3.render(stats.std(x)) if stats.n_valid(x) > 1 else ".")
        return [{"type": "Title", "text": "Summarize"}, t.to_json()]

    def _values(self, ds, dep, factor, lv):
        dmask = missing_mask(ds.df[dep], ds.variables[ds._index_of(dep)]).to_numpy()
        x = ds.df[dep].to_numpy(float)
        if factor is None or lv is None:
            return x[~dmask]
        fv = ds.df[factor].to_numpy(float)
        return x[~dmask & (fv == lv)]


class Codebook(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for n, b in subs)
        names = expand_varlist(body, [v.name for v in ds.variables]) or [v.name for v in ds.variables]
        out: list[dict[str, Any]] = [{"type": "Title", "text": "Codebook"}]
        for nm in names:
            meta = ds.variables[ds._index_of(nm)]
            series = ds.df[nm]
            miss = missing_mask(series, meta).to_numpy()
            props = [
                ("Label", meta.label or "(none)"),
                ("Type", meta.type_label),
                ("Format", meta.print_format.to_spss()),
                ("Measurement Level", meta.measure.capitalize()),
                ("Valid", str(int((~miss).sum()))),
                ("Missing", str(int(miss.sum()))),
            ]
            for val, lab in list(meta.value_labels.items())[:20]:
                props.append((f"Value {val}", str(lab)))
            t = PivotTable(f"{meta.label or nm}", [Dimension("", [p[0] for p in props])],
                           [Dimension("", ["Value"])], corner=nm)
            for i, (_, v) in enumerate(props):
                t.set([i], [0], v, "text")
            out.append(t.to_json())
        return out

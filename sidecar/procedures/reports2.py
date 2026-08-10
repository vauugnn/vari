"""Reports and Tables: OLAP Cubes (OLAP), Custom Tables (CTABLES), and
Multiple Response frequencies (MULTRESPONSE)."""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure
from .base import value_label

_F2 = Format("F", 8, 2)
_F0 = Format("F", 8, 0)


def _clean(ds: Any, names: list[str]) -> pd.DataFrame:
    frame = {}
    for nm in names:
        s = ds.df[nm]
        frame[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
    return pd.DataFrame(frame).dropna()


class Olap(DataProcedure):
    """OLAP dep BY factor[ factor...] — cell means/N/sum broken down by factors."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        m = re.search(r"(.+?)\bBY\b(.+)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "OLAP needs 'summary BY factors'."}]
        dep = expand_varlist(m.group(1), allnames)[0]
        factors = expand_varlist(m.group(2), allnames)
        data = _clean(ds, [dep] + factors)
        grouped = data.groupby(factors)[dep].agg(["count", "mean", "std", "sum"])
        rows = []
        for idx in grouped.index:
            key = idx if isinstance(idx, tuple) else (idx,)
            rows.append(" / ".join(value_label(ds, f, k) for f, k in zip(factors, key)))
        rows.append("Total")
        t = PivotTable(f"OLAP Cubes: {dep}", [Dimension(" * ".join(factors), rows)],
                       [Dimension("", ["N", "Mean", "Std. Deviation", "Sum"])])
        for i, (_, r) in enumerate(grouped.iterrows()):
            t.set([i], [0], _F0.render(int(r["count"])))
            t.set([i], [1], _F2.render(float(r["mean"])))
            t.set([i], [2], _F2.render(float(r["std"])) if r["count"] > 1 else "")
            t.set([i], [3], _F2.render(float(r["sum"])))
        last = len(rows) - 1
        t.set([last], [0], _F0.render(int(data[dep].count())))
        t.set([last], [1], _F2.render(float(data[dep].mean())))
        t.set([last], [2], _F2.render(float(data[dep].std())))
        t.set([last], [3], _F2.render(float(data[dep].sum())))
        return [{"type": "Title", "text": "OLAP Cubes"}, t.to_json()]


class Ctables(DataProcedure):
    """CTABLES /TABLE row BY col [/STATISTICS COUNT|ROWPCT|COLPCT] — a custom
    cross-tabulation. Minimal but real: counts with optional percentages."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        allnames = [v.name for v in ds.variables]
        row = col = None
        stat = "COUNT"
        for name, b in subs:
            u = name.upper()
            if u in ("TABLE", "VARIABLES", ""):
                mm = re.search(r"(\w+)\s+BY\s+(\w+)", b, re.IGNORECASE)
                if mm:
                    row, col = mm.group(1), mm.group(2)
                elif expand_varlist(b, allnames):
                    row = expand_varlist(b, allnames)[0]
            elif u == "STATISTICS":
                stat = b.strip().upper() or "COUNT"
        if row is None:
            return [{"type": "Error", "text": "CTABLES needs '/TABLE row [BY col]'."}]
        cols = [row] + ([col] if col else [])
        data = _clean(ds, cols)
        if col:
            tab = pd.crosstab(data[row], data[col])
            if "ROWPCT" in stat:
                tab = (tab.div(tab.sum(1), axis=0) * 100).round(1)
            elif "COLPCT" in stat:
                tab = (tab.div(tab.sum(0), axis=1) * 100).round(1)
            rlabels = [value_label(ds, row, x) for x in tab.index]
            clabels = [value_label(ds, col, x) for x in tab.columns]
            t = PivotTable("Custom Table", [Dimension(row, rlabels)], [Dimension(col, clabels)])
            fmt = _F2 if "PCT" in stat else _F0
            for i in range(len(rlabels)):
                for j in range(len(clabels)):
                    t.set([i], [j], fmt.render(float(tab.iloc[i, j])))
        else:
            counts = data[row].value_counts().sort_index()
            rlabels = [value_label(ds, row, x) for x in counts.index]
            t = PivotTable("Custom Table", [Dimension(row, rlabels)], [Dimension("", ["Count"])])
            for i, v in enumerate(counts):
                t.set([i], [0], _F0.render(int(v)))
        return [{"type": "Title", "text": "Custom Tables"}, t.to_json()]


class MultResponse(DataProcedure):
    """MULTRESPONSE /FREQUENCIES var list [/VALUE=n] — multiple-dichotomy set
    frequencies (each variable is a 0/1 indicator; VALUE marks 'counted')."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        allnames = [v.name for v in ds.variables]
        names: list[str] = []
        counted = 1.0
        for name, b in subs:
            u = name.upper()
            if u in ("FREQUENCIES", "VARIABLES", ""):
                names += [g for g in expand_varlist(b, allnames) if g in allnames]
            elif u == "VALUE":
                m = re.search(r"-?\d+(\.\d+)?", b)
                if m:
                    counted = float(m.group())
        names = list(dict.fromkeys(names))
        if not names:
            return [{"type": "Error", "text": "MULTRESPONSE needs /FREQUENCIES var list."}]
        data = _clean(ds, names)
        rows = list(names) + ["Total responses"]
        t = PivotTable("Multiple Response Frequencies", [Dimension("", rows)],
                       [Dimension("", ["Count", "Percent of Responses", "Percent of Cases"])])
        counts = [int((data[v] == counted).sum()) for v in names]
        total = sum(counts)
        ncases = len(data)
        for i, v in enumerate(names):
            t.set([i], [0], _F0.render(counts[i]))
            t.set([i], [1], _F2.render(100.0 * counts[i] / total) if total else "")
            t.set([i], [2], _F2.render(100.0 * counts[i] / ncases) if ncases else "")
        t.set([len(names)], [0], _F0.render(total))
        t.set([len(names)], [1], _F2.render(100.0))
        return [{"type": "Title", "text": "Multiple Response"}, t.to_json()]

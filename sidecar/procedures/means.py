"""MEANS — group means breakdown, optional ANOVA table (HLD 6)."""
from __future__ import annotations

import re
from typing import Any

import numpy as np
from scipy import stats as sps

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure
from .base import strip_leading_zero, value_label

_F2 = Format("F", 8, 2)
_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)

_CELL_LABELS = {"MEAN": "Mean", "COUNT": "N", "STDDEV": "Std. Deviation",
                "MEDIAN": "Median", "MIN": "Minimum", "MAX": "Maximum", "SUM": "Sum"}


class Means(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = ""
        cells = ["MEAN", "COUNT", "STDDEV"]
        want_anova = False
        for name, b in subs:
            if name in ("", "TABLES"):
                body += " " + re.sub(r"^\s*TABLES\s*=?\s*", "", b, flags=re.IGNORECASE)
            elif name == "CELLS":
                up = b.upper().split()
                cells = [c for c in ["MEAN", "COUNT", "STDDEV", "MEDIAN", "MIN", "MAX", "SUM"] if c in up] or cells
            elif name == "STATISTICS":
                if "ANOVA" in b.upper():
                    want_anova = True

        m = re.search(r"(.+?)\bBY\b(.+)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "MEANS needs 'dependent BY factor'."}]
        allnames = [v.name for v in ds.variables]
        dep = expand_varlist(m.group(1), allnames)[0]
        factor = expand_varlist(m.group(2), allnames)[0]

        groups, labels = self._groups(ds, dep, factor)
        out: list[dict[str, Any]] = [{"type": "Title", "text": "Means"}]
        rows = labels + ["Total"]
        allv = np.concatenate(groups) if groups else np.array([])
        rep = PivotTable(f"{dep}  *  {factor}", [Dimension(factor, rows)],
                         [Dimension("", [_CELL_LABELS[c] for c in cells])], corner=factor)
        for i, g in enumerate(groups + [allv]):
            for j, c in enumerate(cells):
                rep.set([i], [j], _cell(c, g))
        out.append(rep.to_json())

        if want_anova and len(groups) >= 2:
            out.append(self._anova(dep, groups))
        return out

    def _groups(self, ds, dep, factor):
        dmask = missing_mask(ds.df[dep], ds.variables[ds._index_of(dep)]).to_numpy()
        fmask = missing_mask(ds.df[factor], ds.variables[ds._index_of(factor)]).to_numpy()
        valid = ~(dmask | fmask)
        dv = ds.df[dep].to_numpy(float)
        fv = ds.df[factor].to_numpy(float)
        levels = sorted(set(fv[valid]))
        return [dv[valid & (fv == lv)] for lv in levels], [value_label(ds, factor, lv) for lv in levels]

    def _anova(self, dep, groups):
        k = len(groups)
        n = sum(g.size for g in groups)
        grand = np.concatenate(groups).mean()
        ssb = sum(g.size * (g.mean() - grand) ** 2 for g in groups)
        ssw = sum((g.size - 1) * g.var(ddof=1) for g in groups if g.size > 1)
        dfb, dfw = k - 1, n - k
        msb, msw = ssb / dfb, ssw / dfw
        f = msb / msw if msw else float("nan")
        p = float(sps.f.sf(f, dfb, dfw)) if msw else float("nan")
        t = PivotTable(f"{dep}", [Dimension("", ["Between Groups", "Within Groups", "Total"])],
                       [Dimension("", ["Sum of Squares", "df", "Mean Square", "F", "Sig."])], caption="ANOVA Table")
        t.set([0], [0], _F3.render(ssb)); t.set([0], [1], _F0.render(dfb)); t.set([0], [2], _F3.render(msb))
        t.set([0], [3], _F3.render(f)); t.set([0], [4], strip_leading_zero(_F3.render(p)))
        t.set([1], [0], _F3.render(ssw)); t.set([1], [1], _F0.render(dfw)); t.set([1], [2], _F3.render(msw))
        t.set([2], [0], _F3.render(ssb + ssw)); t.set([2], [1], _F0.render(n - 1))
        return t.to_json()


def _cell(kind: str, g: np.ndarray) -> str:
    if g.size == 0:
        return "."
    if kind == "MEAN":
        return _F2.render(float(g.mean()))
    if kind == "COUNT":
        return _F0.render(g.size)
    if kind == "STDDEV":
        return _F3.render(float(g.std(ddof=1))) if g.size > 1 else "."
    if kind == "MEDIAN":
        return _F2.render(float(np.median(g)))
    if kind == "MIN":
        return _F2.render(float(g.min()))
    if kind == "MAX":
        return _F2.render(float(g.max()))
    if kind == "SUM":
        return _F2.render(float(g.sum()))
    return ""

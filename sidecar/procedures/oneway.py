"""ONEWAY — one-way ANOVA (HLD 6/9).

Emits the ANOVA table always; optional Descriptives, Test of Homogeneity of
Variances (Levene, centered on the mean), and post-hoc Multiple Comparisons
(LSD, Bonferroni, Sidak, Scheffe, Tukey, Games-Howell).
"""
from __future__ import annotations

import math
import re
from typing import Any

import numpy as np
from scipy import stats as sps

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.registry import DataProcedure
from .base import strip_leading_zero, value_label

_F2 = Format("F", 8, 2)
_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)

_POSTHOC = {
    "LSD": "LSD",
    "BONFERRONI": "Bonferroni",
    "SIDAK": "Sidak",
    "SCHEFFE": "Scheffe",
    "TUKEY": "Tukey HSD",
    "GH": "Games-Howell",
    "GAMESHOWELL": "Games-Howell",
}


class Oneway(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = ""
        want_desc = want_homog = False
        posthoc: list[str] = []
        for name, b in subs:
            if name in ("", "VARIABLES"):
                body += " " + b
            elif name == "STATISTICS":
                up = b.upper()
                want_desc = "DESCRIPTIVES" in up
                want_homog = "HOMOGENEITY" in up
            elif name == "POSTHOC":
                for kw in b.upper().replace("(", " ").replace(")", " ").split():
                    key = _POSTHOC.get(kw)
                    if key and key not in posthoc:
                        posthoc.append(key)

        m = re.search(r"(.+?)\bBY\b(.+)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "ONEWAY needs 'dependent BY factor'."}]
        from ..syntax.lexer import expand_varlist

        allnames = [v.name for v in ds.variables]
        deps = expand_varlist(m.group(1), allnames)
        factor = expand_varlist(m.group(2), allnames)[0]

        out: list[dict[str, Any]] = [{"type": "Title", "text": "Oneway"}]
        for dep in deps:
            groups, labels = self._groups(ds, dep, factor)
            if len(groups) < 2:
                continue
            if want_desc:
                out.append(self._descriptives(dep, groups, labels))
            if want_homog:
                out.append(self._homogeneity(dep, groups))
            out.append(self._anova(dep, groups))
            for method in posthoc:
                out.append(self._posthoc(dep, factor, groups, labels, method))
        return out

    def _groups(self, ds: Any, dep: str, factor: str) -> tuple[list[np.ndarray], list[str]]:
        dmask = missing_mask(ds.df[dep], ds.variables[ds._index_of(dep)]).to_numpy()
        fmask = missing_mask(ds.df[factor], ds.variables[ds._index_of(factor)]).to_numpy()
        valid = ~(dmask | fmask)
        dv = ds.df[dep].to_numpy(dtype=float)
        fv = ds.df[factor].to_numpy(dtype=float)
        levels = sorted(set(fv[valid]))
        groups = [dv[valid & (fv == lv)] for lv in levels]
        labels = [value_label(ds, factor, lv) for lv in levels]
        return groups, labels

    def _descriptives(self, dep: str, groups: list[np.ndarray], labels: list[str]) -> dict[str, Any]:
        rows = labels + ["Total"]
        t = PivotTable(dep, [Dimension("", rows)],
                       [Dimension("", ["N", "Mean", "Std. Deviation", "Std. Error", "Minimum", "Maximum"])])
        allv = np.concatenate(groups)
        for i, g in enumerate(groups + [allv]):
            n = g.size
            sd = g.std(ddof=1) if n > 1 else float("nan")
            se = sd / math.sqrt(n) if n > 1 else float("nan")
            t.set([i], [0], _F0.render(n))
            t.set([i], [1], _F2.render(float(g.mean())))
            t.set([i], [2], _F3.render(float(sd)) if n > 1 else ".")
            t.set([i], [3], _F3.render(float(se)) if n > 1 else ".")
            t.set([i], [4], _F2.render(float(g.min())))
            t.set([i], [5], _F2.render(float(g.max())))
        return t.to_json()

    def _homogeneity(self, dep: str, groups: list[np.ndarray]) -> dict[str, Any]:
        lev = sps.levene(*groups, center="mean")
        k = len(groups)
        n = sum(g.size for g in groups)
        t = PivotTable("Test of Homogeneity of Variances", [Dimension("", [dep])],
                       [Dimension("", ["Levene Statistic", "df1", "df2", "Sig."])])
        t.set([0], [0], _F3.render(float(lev.statistic)))
        t.set([0], [1], _F0.render(k - 1))
        t.set([0], [2], _F0.render(n - k))
        t.set([0], [3], strip_leading_zero(_F3.render(float(lev.pvalue))))
        return t.to_json()

    def _anova(self, dep: str, groups: list[np.ndarray]) -> dict[str, Any]:
        k = len(groups)
        n = sum(g.size for g in groups)
        grand = np.concatenate(groups).mean()
        ssb = sum(g.size * (g.mean() - grand) ** 2 for g in groups)
        ssw = sum(((g.size - 1) * g.var(ddof=1)) for g in groups if g.size > 1)
        dfb, dfw = k - 1, n - k
        msb, msw = ssb / dfb, ssw / dfw
        f = msb / msw if msw > 0 else float("nan")
        p = float(sps.f.sf(f, dfb, dfw)) if msw > 0 else float("nan")
        t = PivotTable(dep, [Dimension("", ["Between Groups", "Within Groups", "Total"])],
                       [Dimension("", ["Sum of Squares", "df", "Mean Square", "F", "Sig."])], caption="ANOVA")
        t.set([0], [0], _F3.render(ssb))
        t.set([0], [1], _F0.render(dfb))
        t.set([0], [2], _F3.render(msb))
        t.set([0], [3], _F3.render(f))
        t.set([0], [4], strip_leading_zero(_F3.render(p)))
        t.set([1], [0], _F3.render(ssw))
        t.set([1], [1], _F0.render(dfw))
        t.set([1], [2], _F3.render(msw))
        t.set([2], [0], _F3.render(ssb + ssw))
        t.set([2], [1], _F0.render(n - 1))
        return t.to_json()

    def _posthoc(self, dep: str, factor: str, groups: list[np.ndarray], labels: list[str], method: str) -> dict[str, Any]:
        k = len(groups)
        n = sum(g.size for g in groups)
        msw = sum((g.size - 1) * g.var(ddof=1) for g in groups if g.size > 1) / (n - k)
        m = k * (k - 1) // 2  # number of pairwise comparisons
        pairs = [(i, j) for i in range(k) for j in range(k) if i != j]
        rows = [f"{labels[i]}|{labels[j]}" for i, j in pairs]
        t = PivotTable(
            f"{dep} ({method})",
            [Dimension("", rows)],
            [Dimension("", ["Mean Difference (I-J)", "Std. Error", "Sig.", "95% CI Lower", "95% CI Upper"])],
            caption="Multiple Comparisons",
        )
        for r, (i, j) in enumerate(pairs):
            gi, gj = groups[i], groups[j]
            diff = float(gi.mean() - gj.mean())
            if method == "Games-Howell":
                se = math.sqrt(gi.var(ddof=1) / gi.size + gj.var(ddof=1) / gj.size)
            else:
                se = math.sqrt(msw * (1 / gi.size + 1 / gj.size))
            sig, lo, hi = self._pvalue_ci(method, diff, se, gi, gj, msw, k, n, m)
            t.set([r], [0], _F2.render(diff))
            t.set([r], [1], _F3.render(se))
            t.set([r], [2], strip_leading_zero(_F3.render(sig)))
            t.set([r], [3], _F2.render(lo))
            t.set([r], [4], _F2.render(hi))
        return t.to_json()

    def _pvalue_ci(self, method, diff, se, gi, gj, msw, k, n, m):
        dfw = n - k
        if method in ("LSD", "Bonferroni", "Sidak"):
            tval = diff / se
            p = float(2 * sps.t.sf(abs(tval), dfw))
            if method == "Bonferroni":
                p = min(1.0, p * m)
                crit = sps.t.ppf(1 - 0.025 / m, dfw)
            elif method == "Sidak":
                p = 1 - (1 - p) ** m
                crit = sps.t.ppf(1 - (1 - 0.95 ** (1 / m)) / 2, dfw)
            else:
                crit = sps.t.ppf(0.975, dfw)
            return p, diff - crit * se, diff + crit * se
        if method == "Scheffe":
            fstat = (diff / se) ** 2 / (k - 1)
            p = float(sps.f.sf(fstat, k - 1, dfw))
            crit = math.sqrt((k - 1) * sps.f.ppf(0.95, k - 1, dfw))
            return p, diff - crit * se, diff + crit * se
        if method == "Tukey HSD":
            q = abs(diff) / (se / math.sqrt(2))
            p = float(sps.studentized_range.sf(q, k, dfw))
            qcrit = sps.studentized_range.ppf(0.95, k, dfw)
            half = qcrit * se / math.sqrt(2)
            return p, diff - half, diff + half
        if method == "Games-Howell":
            df = (gi.var(ddof=1) / gi.size + gj.var(ddof=1) / gj.size) ** 2 / (
                (gi.var(ddof=1) / gi.size) ** 2 / (gi.size - 1) + (gj.var(ddof=1) / gj.size) ** 2 / (gj.size - 1)
            )
            q = abs(diff) / (se / math.sqrt(2))
            p = float(sps.studentized_range.sf(q, k, df))
            qcrit = sps.studentized_range.ppf(0.95, k, df)
            half = qcrit * se / math.sqrt(2)
            return p, diff - half, diff + half
        return float("nan"), float("nan"), float("nan")

"""NPAR TESTS — legacy nonparametric tests (HLD 6/9).

Implements Mann-Whitney U, Kruskal-Wallis H, and Wilcoxon signed-rank. Each
emits a Ranks table and a Test Statistics table. Asymptotic significances use
tie corrections, no continuity correction (SPSS default).
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
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure
from .base import strip_leading_zero, value_label

_F2 = Format("F", 8, 2)
_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)


class NparTests(DataProcedure):
    command = "NPAR TESTS"

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = [{"type": "Title", "text": "NPar Tests"}]
        handled = False
        for name, body in subs:
            key = name.upper()
            if key in ("M-W", "MANN-WHITNEY"):
                out += self._mann_whitney(ds, body)
                handled = True
            elif key in ("K-W", "KRUSKAL-WALLIS"):
                out += self._kruskal(ds, body)
                handled = True
            elif key == "WILCOXON":
                out += self._wilcoxon(ds, body)
                handled = True
        if not handled:
            return [{"type": "Error", "text": "NPAR TESTS: supported subcommands are /M-W, /K-W, /WILCOXON."}]
        return out

    def _by_groups(self, ds, body):
        m = re.search(r"(.+?)\bBY\b\s*(\w+)\s*\(([^)]*)\)", body, re.IGNORECASE)
        if not m:
            raise ValueError("Expected 'var BY group(values)'.")
        allnames = [v.name for v in ds.variables]
        testvars = expand_varlist(m.group(1), allnames)
        gvar = m.group(2)
        vals = [float(x) for x in re.split(r"[,\s]+", m.group(3).strip()) if x]
        return testvars, gvar, vals

    def _valid_pair(self, ds, var, gvar):
        vm = missing_mask(ds.df[var], ds.variables[ds._index_of(var)]).to_numpy()
        gm = missing_mask(ds.df[gvar], ds.variables[ds._index_of(gvar)]).to_numpy()
        keep = ~(vm | gm)
        return ds.df[var].to_numpy(float)[keep], ds.df[gvar].to_numpy(float)[keep]

    def _mann_whitney(self, ds, body):
        testvars, gvar, vals = self._by_groups(ds, body)
        g1, g2 = vals[0], vals[1]
        out = []
        for var in testvars:
            x, g = self._valid_pair(ds, var, gvar)
            a, b = x[g == g1], x[g == g2]
            ranks = sps.rankdata(np.concatenate([a, b]))
            ra, rb = ranks[: a.size], ranks[a.size :]
            n1, n2 = a.size, b.size
            u = sps.mannwhitneyu(a, b, alternative="two-sided", method="asymptotic", use_continuity=False)
            U = float(min(u.statistic, n1 * n2 - u.statistic))
            w = float(ra.sum())
            z = self._mw_z(np.concatenate([a, b]), ra.sum(), n1, n2)
            p = float(u.pvalue)

            ranks_t = PivotTable(var, [Dimension(gvar, [value_label(ds, gvar, g1), value_label(ds, gvar, g2), "Total"])],
                                 [Dimension("", ["N", "Mean Rank", "Sum of Ranks"])], corner="Ranks")
            ranks_t.set([0], [0], _F0.render(n1)); ranks_t.set([0], [1], _F2.render(float(ra.mean()))); ranks_t.set([0], [2], _F2.render(float(ra.sum())))
            ranks_t.set([1], [0], _F0.render(n2)); ranks_t.set([1], [1], _F2.render(float(rb.mean()))); ranks_t.set([1], [2], _F2.render(float(rb.sum())))
            ranks_t.set([2], [0], _F0.render(n1 + n2))
            out.append(ranks_t.to_json())

            ts = PivotTable("Test Statistics", [Dimension("", ["Mann-Whitney U", "Wilcoxon W", "Z", "Asymp. Sig. (2-tailed)"])],
                            [Dimension("", [var])])
            ts.set([0], [0], _F3.render(U)); ts.set([1], [0], _F3.render(w))
            ts.set([2], [0], _F3.render(z)); ts.set([3], [0], strip_leading_zero(_F3.render(p)))
            out.append(ts.to_json())
        return out

    def _mw_z(self, combined, sum_ranks_a, n1, n2):
        n = n1 + n2
        mean_r = n1 * (n + 1) / 2
        _, counts = np.unique(combined, return_counts=True)
        tie = (counts**3 - counts).sum()
        var = n1 * n2 / 12 * ((n + 1) - tie / (n * (n - 1)))
        return float((sum_ranks_a - mean_r) / math.sqrt(var)) if var > 0 else float("nan")

    def _kruskal(self, ds, body):
        testvars, gvar, vals = self._by_groups(ds, body)
        lo, hi = int(vals[0]), int(vals[1])
        out = []
        for var in testvars:
            x, g = self._valid_pair(ds, var, gvar)
            levels = [lv for lv in sorted(set(g)) if lo <= lv <= hi]
            groups = [x[g == lv] for lv in levels]
            h, p = sps.kruskal(*groups)
            ranks = sps.rankdata(x)
            ranks_t = PivotTable(var, [Dimension(gvar, [value_label(ds, gvar, lv) for lv in levels] + ["Total"])],
                                 [Dimension("", ["N", "Mean Rank"])], corner="Ranks")
            for i, lv in enumerate(levels):
                sub = ranks[g == lv]
                ranks_t.set([i], [0], _F0.render(sub.size)); ranks_t.set([i], [1], _F2.render(float(sub.mean())))
            ranks_t.set([len(levels)], [0], _F0.render(x.size))
            out.append(ranks_t.to_json())
            ts = PivotTable("Test Statistics", [Dimension("", ["Kruskal-Wallis H", "df", "Asymp. Sig."])],
                            [Dimension("", [var])])
            ts.set([0], [0], _F3.render(float(h))); ts.set([1], [0], _F0.render(len(levels) - 1))
            ts.set([2], [0], strip_leading_zero(_F3.render(float(p))))
            out.append(ts.to_json())
        return out

    def _wilcoxon(self, ds, body):
        toks = re.split(r"\bWITH\b", body, flags=re.IGNORECASE)
        allnames = [v.name for v in ds.variables]
        left = expand_varlist(toks[0], allnames)
        right = expand_varlist(toks[1], allnames) if len(toks) > 1 else []
        out = []
        for a_name, b_name in zip(left, right):
            am = missing_mask(ds.df[a_name], ds.variables[ds._index_of(a_name)]).to_numpy()
            bm = missing_mask(ds.df[b_name], ds.variables[ds._index_of(b_name)]).to_numpy()
            keep = ~(am | bm)
            a = ds.df[a_name].to_numpy(float)[keep]
            b = ds.df[b_name].to_numpy(float)[keep]
            res = sps.wilcoxon(a, b, correction=False, mode="approx")
            z = float((res.statistic - self._wil_mean(a, b)) / self._wil_sd(a, b)) if a.size else float("nan")
            ts = PivotTable("Test Statistics", [Dimension("", ["Z", "Asymp. Sig. (2-tailed)"])],
                            [Dimension("", [f"{b_name} - {a_name}"])])
            ts.set([0], [0], _F3.render(z)); ts.set([1], [0], strip_leading_zero(_F3.render(float(res.pvalue))))
            out.append(ts.to_json())
        return out

    def _wil_mean(self, a, b):
        d = a - b
        d = d[d != 0]
        n = d.size
        return n * (n + 1) / 4

    def _wil_sd(self, a, b):
        d = a - b
        d = d[d != 0]
        n = d.size
        return math.sqrt(n * (n + 1) * (2 * n + 1) / 24) if n else float("nan")

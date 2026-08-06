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
            elif key == "CHISQUARE":
                out += self._chisquare(ds, body)
                handled = True
            elif key == "FRIEDMAN":
                out += self._friedman(ds, body)
                handled = True
            elif key == "BINOMIAL":
                out += self._binomial(ds, name, body)
                handled = True
            elif key == "RUNS":
                out += self._runs(ds, name, body)
                handled = True
            elif key == "K-S":
                out += self._ks_one(ds, body)
                handled = True
            elif key == "SIGN":
                out += self._sign(ds, body)
                handled = True
            elif key == "MCNEMAR":
                out += self._mcnemar(ds, body)
                handled = True
            elif key == "COCHRAN":
                out += self._cochran(ds, body)
                handled = True
            elif key == "KENDALL":
                out += self._kendall_w(ds, body)
                handled = True
        if not handled:
            return [{"type": "Error", "text": "NPAR TESTS: /M-W /K-W /WILCOXON /CHISQUARE /FRIEDMAN /BINOMIAL /RUNS /K-S /SIGN /MCNEMAR /COCHRAN /KENDALL."}]
        return out

    def _binomial(self, ds, subname, body):
        m = re.match(r"\(([\d.]+)\)", body)
        test_p = float(m.group(1)) if m else 0.5
        body = re.sub(r"^\([\d.]+\)\s*=?\s*", "", body)
        out = []
        for var in expand_varlist(body, [v.name for v in ds.variables]):
            x = ds.df[var].to_numpy(float)
            x = x[~missing_mask(ds.df[var], ds.variables[ds._index_of(var)]).to_numpy()]
            x = x[~np.isnan(x)]
            uniq = np.unique(x)
            g1 = (x == uniq[0]).sum()
            n = x.size
            res = sps.binomtest(int(g1), n, test_p)
            t = PivotTable(var, [Dimension("", ["Group 1", "Group 2", "Total"])],
                           [Dimension("", ["Category", "N", "Observed Prop.", "Test Prop.", "Asymp. Sig. (2-tailed)"])], corner="")
            t.set([0], [0], value_label(ds, var, uniq[0]), "text"); t.set([0], [1], _F0.render(int(g1)))
            t.set([0], [2], strip_leading_zero(_F3.render(g1 / n))); t.set([0], [3], strip_leading_zero(_F3.render(test_p)))
            t.set([0], [4], strip_leading_zero(_F3.render(float(res.pvalue))))
            t.set([1], [0], "others" if len(uniq) > 2 else value_label(ds, var, uniq[-1]), "text")
            t.set([1], [1], _F0.render(int(n - g1))); t.set([1], [2], strip_leading_zero(_F3.render((n - g1) / n)))
            t.set([2], [1], _F0.render(int(n)))
            out.append(t.to_json())
        return out

    def _runs(self, ds, subname, body):
        body = re.sub(r"^\([A-Za-z]+\)\s*=?\s*", "", body)
        out = []
        for var in expand_varlist(body, [v.name for v in ds.variables]):
            x = ds.df[var].to_numpy(float)
            x = x[~missing_mask(ds.df[var], ds.variables[ds._index_of(var)]).to_numpy()]
            x = x[~np.isnan(x)]
            cut = float(np.median(x))
            signs = x >= cut
            n1 = int(signs.sum()); n2 = int((~signs).sum())
            runs = 1 + int((signs[1:] != signs[:-1]).sum()) if x.size else 0
            n = n1 + n2
            mean = 2 * n1 * n2 / n + 1 if n else float("nan")
            var_r = (2 * n1 * n2 * (2 * n1 * n2 - n)) / (n * n * (n - 1)) if n > 1 else float("nan")
            z = (runs - mean) / math.sqrt(var_r) if var_r > 0 else float("nan")
            p = float(2 * sps.norm.sf(abs(z))) if z == z else float("nan")
            t = PivotTable("Runs Test", [Dimension("", ["Test Value (Median)", "Cases < Test Value", "Cases >= Test Value",
                                                        "Total Cases", "Number of Runs", "Z", "Asymp. Sig. (2-tailed)"])],
                           [Dimension("", [var])])
            for i, val in enumerate([_F3.render(cut), _F0.render(n2), _F0.render(n1), _F0.render(n),
                                     _F0.render(runs), _F3.render(z), strip_leading_zero(_F3.render(p))]):
                t.set([i], [0], val)
            out.append(t.to_json())
        return out

    def _ks_one(self, ds, body):
        body = re.sub(r"^\([A-Za-z]+\)\s*=?\s*", "", body)
        out = []
        for var in expand_varlist(body, [v.name for v in ds.variables]):
            x = ds.df[var].to_numpy(float)
            x = x[~missing_mask(ds.df[var], ds.variables[ds._index_of(var)]).to_numpy()]
            x = x[~np.isnan(x)]
            mean, sd = float(x.mean()), float(x.std(ddof=0))
            d, p = sps.kstest(x, "norm", args=(mean, sd))
            t = PivotTable("One-Sample Kolmogorov-Smirnov Test",
                           [Dimension("", ["N", "Normal Mean", "Normal Std. Dev.", "Kolmogorov-Smirnov Z", "Asymp. Sig. (2-tailed)"])],
                           [Dimension("", [var])])
            zval = d * math.sqrt(x.size)
            for i, val in enumerate([_F0.render(x.size), _F3.render(mean), _F3.render(sd), _F3.render(zval),
                                     strip_leading_zero(_F3.render(float(p)))]):
                t.set([i], [0], val)
            out.append(t.to_json())
        return out

    def _pairs(self, ds, body):
        toks = re.split(r"\bWITH\b", body, flags=re.IGNORECASE)
        allnames = [v.name for v in ds.variables]
        left = expand_varlist(toks[0], allnames)
        right = expand_varlist(toks[1], allnames) if len(toks) > 1 else []
        return list(zip(left, right))

    def _clean_pair(self, ds, a_name, b_name):
        am = missing_mask(ds.df[a_name], ds.variables[ds._index_of(a_name)]).to_numpy()
        bm = missing_mask(ds.df[b_name], ds.variables[ds._index_of(b_name)]).to_numpy()
        keep = ~(am | bm)
        return ds.df[a_name].to_numpy(float)[keep], ds.df[b_name].to_numpy(float)[keep]

    def _sign(self, ds, body):
        out = []
        for a_name, b_name in self._pairs(ds, body):
            a, b = self._clean_pair(ds, a_name, b_name)
            d = b - a
            pos = int((d > 0).sum()); neg = int((d < 0).sum())
            nn = pos + neg
            p = float(sps.binomtest(min(pos, neg), nn, 0.5).pvalue) if nn else float("nan")
            t = PivotTable("Test Statistics", [Dimension("", ["Negative Differences", "Positive Differences", "Ties", "Exact Sig. (2-tailed)"])],
                           [Dimension("", [f"{b_name} - {a_name}"])])
            t.set([0], [0], _F0.render(neg)); t.set([1], [0], _F0.render(pos))
            t.set([2], [0], _F0.render(len(d) - nn)); t.set([3], [0], strip_leading_zero(_F3.render(p)))
            out.append(t.to_json())
        return out

    def _mcnemar(self, ds, body):
        out = []
        for a_name, b_name in self._pairs(ds, body):
            a, b = self._clean_pair(ds, a_name, b_name)
            import pandas as pd

            ct = pd.crosstab(a, b).reindex(index=[0, 1], columns=[0, 1]).fillna(0).to_numpy() if set(np.unique(np.concatenate([a, b]))) <= {0.0, 1.0} else pd.crosstab(a, b).to_numpy()
            b_, c_ = (ct[0, 1], ct[1, 0]) if ct.shape == (2, 2) else (0, 0)
            stat = (abs(b_ - c_) - 1) ** 2 / (b_ + c_) if (b_ + c_) else float("nan")
            p = float(sps.chi2.sf(stat, 1)) if stat == stat else float("nan")
            t = PivotTable("Test Statistics", [Dimension("", ["N", "Chi-Square", "Asymp. Sig."])],
                           [Dimension("", [f"{a_name} & {b_name}"])])
            t.set([0], [0], _F0.render(len(a))); t.set([1], [0], _F3.render(stat) if stat == stat else ".")
            t.set([2], [0], strip_leading_zero(_F3.render(p)) if p == p else ".")
            out.append(t.to_json())
        return out

    def _related_matrix(self, ds, body):
        names = expand_varlist(body, [v.name for v in ds.variables])
        import pandas as pd

        cols = {nm: ds.df[nm].where(~missing_mask(ds.df[nm], ds.variables[ds._index_of(nm)]).to_numpy()) for nm in names}
        data = pd.DataFrame(cols).dropna()
        return names, data.to_numpy(float)

    def _cochran(self, ds, body):
        names, m = self._related_matrix(ds, body)
        k = m.shape[1]
        col = m.sum(axis=0)
        row = m.sum(axis=1)
        grand = m.sum()
        num = (k - 1) * (k * (col**2).sum() - grand**2)
        den = k * grand - (row**2).sum()
        q = num / den if den else float("nan")
        p = float(sps.chi2.sf(q, k - 1)) if q == q else float("nan")
        t = PivotTable("Test Statistics", [Dimension("", ["N", "Cochran's Q", "df", "Asymp. Sig."])],
                       [Dimension("", ["Value"])])
        t.set([0], [0], _F0.render(m.shape[0])); t.set([1], [0], _F3.render(float(q)) if q == q else ".")
        t.set([2], [0], _F0.render(k - 1)); t.set([3], [0], strip_leading_zero(_F3.render(p)) if p == p else ".")
        return [t.to_json()]

    def _kendall_w(self, ds, body):
        names, m = self._related_matrix(ds, body)
        n, k = m.shape
        ranks = sps.rankdata(m, axis=1)
        rank_sums = ranks.sum(axis=0)
        s = ((rank_sums - rank_sums.mean()) ** 2).sum()
        w = 12 * s / (n * n * (k**3 - k)) if (k**3 - k) else float("nan")
        chi = n * (k - 1) * w
        p = float(sps.chi2.sf(chi, k - 1)) if chi == chi else float("nan")
        rt = PivotTable("Ranks", [Dimension("", list(names))], [Dimension("", ["Mean Rank"])])
        for i in range(k):
            rt.set([i], [0], _F2.render(float(ranks[:, i].mean())))
        ts = PivotTable("Test Statistics", [Dimension("", ["N", "Kendall's W", "Chi-Square", "df", "Asymp. Sig."])],
                        [Dimension("", ["Value"])])
        for i, val in enumerate([_F0.render(n), _F3.render(float(w)), _F3.render(float(chi)), _F0.render(k - 1),
                                 strip_leading_zero(_F3.render(p))]):
            ts.set([i], [0], val)
        return [rt.to_json(), ts.to_json()]

    def _chisquare(self, ds, body):
        allnames = [v.name for v in ds.variables]
        names = expand_varlist(body, allnames)
        out = []
        for var in names:
            x = ds.df[var].to_numpy(float)
            x = x[~missing_mask(ds.df[var], ds.variables[ds._index_of(var)]).to_numpy()]
            vals, counts = np.unique(x[~np.isnan(x)], return_counts=True)
            expected = np.full(len(counts), counts.sum() / len(counts))
            chi = float(((counts - expected) ** 2 / expected).sum())
            dfree = len(counts) - 1
            p = float(sps.chi2.sf(chi, dfree))
            freq = PivotTable(var, [Dimension("", [value_label(ds, var, v) for v in vals] + ["Total"])],
                              [Dimension("", ["Observed N", "Expected N", "Residual"])], corner="")
            for i, (o, e) in enumerate(zip(counts, expected)):
                freq.set([i], [0], _F0.render(int(o))); freq.set([i], [1], _F2.render(float(e)))
                freq.set([i], [2], _F2.render(float(o - e)))
            freq.set([len(counts)], [0], _F0.render(int(counts.sum())))
            out.append(freq.to_json())
            ts = PivotTable("Test Statistics", [Dimension("", ["Chi-Square", "df", "Asymp. Sig."])],
                            [Dimension("", [var])])
            ts.set([0], [0], _F3.render(chi)); ts.set([1], [0], _F0.render(dfree))
            ts.set([2], [0], strip_leading_zero(_F3.render(p)))
            out.append(ts.to_json())
        return out

    def _friedman(self, ds, body):
        allnames = [v.name for v in ds.variables]
        names = expand_varlist(body, allnames)
        cols = {}
        for nm in names:
            s = ds.df[nm]
            cols[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
        import pandas as pd

        data = pd.DataFrame(cols).dropna()
        arrs = [data[nm].to_numpy(float) for nm in names]
        stat, p = sps.friedmanchisquare(*arrs)
        ranks = sps.rankdata(data.to_numpy(float), axis=1)
        rt = PivotTable("Ranks", [Dimension("", list(names))], [Dimension("", ["Mean Rank"])])
        for i in range(len(names)):
            rt.set([i], [0], _F2.render(float(ranks[:, i].mean())))
        ts = PivotTable("Test Statistics", [Dimension("", ["N", "Chi-Square", "df", "Asymp. Sig."])],
                        [Dimension("", ["Friedman"])])
        ts.set([0], [0], _F0.render(len(data))); ts.set([1], [0], _F3.render(float(stat)))
        ts.set([2], [0], _F0.render(len(names) - 1)); ts.set([3], [0], strip_leading_zero(_F3.render(float(p))))
        return [rt.to_json(), ts.to_json()]

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

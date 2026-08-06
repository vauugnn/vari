"""T-TEST — one-sample, independent-samples, paired (HLD 6/9).

SPSS parity points: Levene's test is centered on the MEAN; the independent
test reports BOTH equal-variances-assumed and Welch-Satterthwaite rows.
"""
from __future__ import annotations

import math
import re
from typing import Any, Optional

import numpy as np
from scipy import stats as sps

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import Context, Procedure
from .base import numeric_valid, value_label

_F2 = Format("F", 8, 2)
_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)


def _r(fmt: Format, v: Optional[float]) -> str:
    return fmt.render(v) if v is not None and v == v else "."


class TTest(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = ctx.active
        if ds is None:
            raise RuntimeError("There is no active dataset.")
        testval = re.search(r"TESTVAL\s*=?\s*(-?[\d.]+)", rest, re.IGNORECASE)
        groups = re.search(r"GROUPS\s*=?\s*(\w+)\s*\(([^)]*)\)", rest, re.IGNORECASE)
        pairs = re.search(r"PAIRS\s*=?\s*([^/]*)", rest, re.IGNORECASE)
        varm = re.search(r"VARIABLES\s*=?\s*([^/]*)", rest, re.IGNORECASE)
        allnames = [v.name for v in ds.variables]

        if pairs:
            return self._paired(ds, pairs.group(1), allnames)
        if groups:
            g = groups.group(1)
            gv = [float(x) for x in re.split(r"[,\s]+", groups.group(2).strip()) if x]
            varlist = expand_varlist(varm.group(1) if varm else "", allnames)
            return self._independent(ds, varlist, g, gv, allnames)
        if testval:
            varlist = expand_varlist(varm.group(1) if varm else "", allnames)
            return self._one_sample(ds, varlist, float(testval.group(1)))
        return [{"type": "Error", "text": "T-TEST needs /TESTVAL, GROUPS, or /PAIRS."}]

    # ---- one sample ---------------------------------------------------
    def _one_sample(self, ds: Any, names: list[str], testval: float) -> list[dict[str, Any]]:
        if not names:
            return [{"type": "Error", "text": "T-TEST /TESTVAL requires /VARIABLES."}]
        stt = PivotTable("One-Sample Statistics", [Dimension("", names)],
                         [Dimension("", ["N", "Mean", "Std. Deviation", "Std. Error Mean"])])
        test = PivotTable(
            "One-Sample Test",
            [Dimension("", names)],
            [Dimension("", ["t", "df", "Sig. (2-tailed)", "Mean Difference", "95% CI Lower", "95% CI Upper"])],
            caption=f"Test Value = {Format('F', 8, 0).render(testval) if testval == int(testval) else testval}",
        )
        for i, nm in enumerate(names):
            x = numeric_valid(ds, nm)
            n = x.size
            mean = float(x.mean()) if n else float("nan")
            sd = float(x.std(ddof=1)) if n > 1 else float("nan")
            se = sd / math.sqrt(n) if n > 1 else float("nan")
            stt.set([i], [0], _F0.render(n), "num")
            stt.set([i], [1], _r(_F2, mean), "num")
            stt.set([i], [2], _r(_F3, sd), "num")
            stt.set([i], [3], _r(_F3, se), "num")
            if n > 1 and se > 0:
                tval = (mean - testval) / se
                df = n - 1
                p = float(2 * sps.t.sf(abs(tval), df))
                diff = mean - testval
                crit = sps.t.ppf(0.975, df)
                lo, hi = diff - crit * se, diff + crit * se
                test.set([i], [0], _F3.render(tval), "num")
                test.set([i], [1], _F0.render(df), "num")
                test.set([i], [2], _F3.render(p), "num")
                test.set([i], [3], _F2.render(diff), "num")
                test.set([i], [4], _F2.render(lo), "num")
                test.set([i], [5], _F2.render(hi), "num")
        return [{"type": "Title", "text": "T-Test"}, stt.to_json(), test.to_json()]

    # ---- independent samples -----------------------------------------
    def _independent(self, ds: Any, names: list[str], gvar: str, gvals: list[float],
                     allnames: list[str]) -> list[dict[str, Any]]:
        if len(gvals) < 2 or not names:
            return [{"type": "Error", "text": "T-TEST GROUPS needs two values and /VARIABLES."}]
        g1, g2 = gvals[0], gvals[1]
        glabels = [value_label(ds, gvar, g1), value_label(ds, gvar, g2)]

        gstat = PivotTable(
            "Group Statistics",
            [Dimension("", names), Dimension(gvar, glabels)],
            [Dimension("", ["N", "Mean", "Std. Deviation", "Std. Error Mean"])],
        )
        test = PivotTable(
            "Independent Samples Test",
            [Dimension("", names), Dimension("", ["Equal variances assumed", "Equal variances not assumed"])],
            [Dimension("", ["Levene F", "Levene Sig.", "t", "df", "Sig. (2-tailed)", "Mean Difference", "Std. Error Difference"])],
        )
        gidx = ds._index_of(gvar)
        gmeta = ds.variables[gidx]
        for i, nm in enumerate(names):
            meta = ds.variables[ds._index_of(nm)]
            xmask = missing_mask(ds.df[nm], meta)
            gmask = missing_mask(ds.df[gvar], gmeta)
            valid = ~(xmask.to_numpy() | gmask.to_numpy())
            xv = ds.df[nm].to_numpy(dtype=float)
            gvv = ds.df[gvar].to_numpy(dtype=float)
            a = xv[valid & (gvv == g1)]
            b = xv[valid & (gvv == g2)]
            for k, arr in enumerate((a, b)):
                gstat.set([i, k], [0], _F0.render(arr.size), "num")
                gstat.set([i, k], [1], _r(_F2, float(arr.mean()) if arr.size else None), "num")
                gstat.set([i, k], [2], _r(_F3, float(arr.std(ddof=1)) if arr.size > 1 else None), "num")
                gstat.set([i, k], [3], _r(_F3, float(arr.std(ddof=1) / math.sqrt(arr.size)) if arr.size > 1 else None), "num")
            if a.size > 1 and b.size > 1:
                lev = sps.levene(a, b, center="mean")  # SPSS centers on the mean
                teq = sps.ttest_ind(a, b, equal_var=True)
                twe = sps.ttest_ind(a, b, equal_var=False)
                diff = float(a.mean() - b.mean())
                se_eq = _pooled_se(a, b)
                se_we = math.sqrt(a.var(ddof=1) / a.size + b.var(ddof=1) / b.size)
                df_we = _welch_df(a, b)
                # equal variances assumed
                test.set([i, 0], [0], _F3.render(float(lev.statistic)), "num")
                test.set([i, 0], [1], _F3.render(float(lev.pvalue)), "num")
                test.set([i, 0], [2], _F3.render(float(teq.statistic)), "num")
                test.set([i, 0], [3], _F0.render(a.size + b.size - 2), "num")
                test.set([i, 0], [4], _F3.render(float(teq.pvalue)), "num")
                test.set([i, 0], [5], _F2.render(diff), "num")
                test.set([i, 0], [6], _F3.render(se_eq), "num")
                # equal variances not assumed (Welch)
                test.set([i, 1], [0], "", "num")
                test.set([i, 1], [1], "", "num")
                test.set([i, 1], [2], _F3.render(float(twe.statistic)), "num")
                test.set([i, 1], [3], _F3.render(df_we), "num")
                test.set([i, 1], [4], _F3.render(float(twe.pvalue)), "num")
                test.set([i, 1], [5], _F2.render(diff), "num")
                test.set([i, 1], [6], _F3.render(se_we), "num")
        return [{"type": "Title", "text": "T-Test"}, gstat.to_json(), test.to_json()]

    # ---- paired samples ----------------------------------------------
    def _paired(self, ds: Any, body: str, allnames: list[str]) -> list[dict[str, Any]]:
        toks = body.replace(" WITH ", " ").replace(" with ", " ").split()
        names = expand_varlist(" ".join(toks), allnames)
        if len(names) < 2:
            return [{"type": "Error", "text": "T-TEST /PAIRS needs pairs of variables."}]
        pairs = [(names[i], names[i + 1]) for i in range(0, len(names) - 1, 2)]
        labels = [f"Pair {i + 1}" for i in range(len(pairs))]
        test = PivotTable(
            "Paired Samples Test",
            [Dimension("", labels)],
            [Dimension("", ["Mean", "Std. Deviation", "Std. Error Mean", "t", "df", "Sig. (2-tailed)"])],
        )
        for i, (a, b) in enumerate(pairs):
            ma = missing_mask(ds.df[a], ds.variables[ds._index_of(a)]).to_numpy()
            mb = missing_mask(ds.df[b], ds.variables[ds._index_of(b)]).to_numpy()
            valid = ~(ma | mb)
            av = ds.df[a].to_numpy(dtype=float)[valid]
            bv = ds.df[b].to_numpy(dtype=float)[valid]
            d = av - bv
            n = d.size
            if n > 1:
                mean = float(d.mean())
                sd = float(d.std(ddof=1))
                se = sd / math.sqrt(n)
                res = sps.ttest_rel(av, bv)
                test.set([i], [0], _F2.render(mean), "num")
                test.set([i], [1], _F3.render(sd), "num")
                test.set([i], [2], _F3.render(se), "num")
                test.set([i], [3], _F3.render(float(res.statistic)), "num")
                test.set([i], [4], _F0.render(n - 1), "num")
                test.set([i], [5], _F3.render(float(res.pvalue)), "num")
        return [{"type": "Title", "text": "T-Test"}, test.to_json()]


def _pooled_se(a: np.ndarray, b: np.ndarray) -> float:
    n1, n2 = a.size, b.size
    sp2 = ((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1)) / (n1 + n2 - 2)
    return math.sqrt(sp2 * (1 / n1 + 1 / n2))


def _welch_df(a: np.ndarray, b: np.ndarray) -> float:
    v1, v2 = a.var(ddof=1) / a.size, b.var(ddof=1) / b.size
    return (v1 + v2) ** 2 / (v1**2 / (a.size - 1) + v2**2 / (b.size - 1))

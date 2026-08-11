"""EXAMINE (Explore) — descriptives with CI, normality tests, boxplot (HLD 6)."""
from __future__ import annotations

import math
import re
from typing import Any

import numpy as np
from scipy import stats as sps

from ..data.format import Format
from ..data.missing import missing_mask
from ..output import charts as ch
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure
from . import stats
from .base import numeric_valid, value_label

_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)


class Examine(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = ""
        want_box = True
        for name, b in subs:
            if name in ("", "VARIABLES"):
                body += " " + re.sub(r"^\s*VARIABLES\s*=?\s*", "", b, flags=re.IGNORECASE)
            elif name == "PLOT":
                # An explicit /PLOT selects exactly what is listed.
                want_box = "BOXPLOT" in b.upper() or "ALL" in b.upper()

        m = re.search(r"(.+?)\bBY\b(.+)", body, re.IGNORECASE)
        allnames = [v.name for v in ds.variables]
        if m:
            deps = expand_varlist(m.group(1), allnames)
            factor = expand_varlist(m.group(2), allnames)[0]
        else:
            deps = expand_varlist(body, allnames)
            factor = None

        out: list[dict[str, Any]] = [{"type": "Title", "text": "Explore"}]
        for dep in deps:
            groups, labels = self._groups(ds, dep, factor)
            out.append(self._descriptives(ds, dep, factor, groups, labels))
            out.append(self._normality(dep, factor, groups, labels))
            if want_box:
                out.append(ch.boxplot(groups, labels, title=f"Boxplot: {ds.variables[ds._index_of(dep)].label or dep}",
                                      ylabel=dep))
        return out

    def _groups(self, ds, dep, factor):
        if factor is None:
            return [numeric_valid(ds, dep)], [ds.variables[ds._index_of(dep)].label or dep]
        dmask = missing_mask(ds.df[dep], ds.variables[ds._index_of(dep)]).to_numpy()
        fmask = missing_mask(ds.df[factor], ds.variables[ds._index_of(factor)]).to_numpy()
        valid = ~(dmask | fmask)
        dv = ds.df[dep].to_numpy(float)
        fv = ds.df[factor].to_numpy(float)
        levels = sorted(set(fv[valid]))
        return [dv[valid & (fv == lv)] for lv in levels], [value_label(ds, factor, lv) for lv in levels]

    def _descriptives(self, ds, dep, factor, groups, labels):
        rowcats = ["Mean", "95% CI Lower Bound", "95% CI Upper Bound", "5% Trimmed Mean", "Median",
                   "Variance", "Std. Deviation", "Minimum", "Maximum", "Range",
                   "Interquartile Range", "Skewness", "Kurtosis"]
        t = PivotTable(f"{dep}", [Dimension(factor or "", labels), Dimension("", rowcats)],
                       [Dimension("", ["Statistic"])], corner="")
        for gi, g in enumerate(groups):
            v = stats.valid_values(g)
            n = v.size
            mean = float(v.mean()) if n else float("nan")
            sd = float(v.std(ddof=1)) if n > 1 else float("nan")
            se = sd / math.sqrt(n) if n > 1 else float("nan")
            crit = sps.t.ppf(0.975, n - 1) if n > 1 else float("nan")
            trimmed = float(sps.trim_mean(v, 0.05)) if n else float("nan")
            q1, q3 = (np.percentile(v, [25, 75]) if n else (float("nan"), float("nan")))
            vals = [mean, mean - crit * se, mean + crit * se, trimmed, float(np.median(v)) if n else float("nan"),
                    sd * sd, sd, float(v.min()) if n else float("nan"), float(v.max()) if n else float("nan"),
                    (float(v.max() - v.min()) if n else float("nan")), float(q3 - q1),
                    stats.skewness(v), stats.kurtosis(v)]
            for ri, val in enumerate(vals):
                t.set([gi, ri], [0], _F3.render(val) if val is not None and val == val else ".")
        return t.to_json()

    def _normality(self, dep, factor, groups, labels):
        t = PivotTable(
            "Tests of Normality",
            [Dimension(factor or "", labels)],
            [Dimension("", ["KS Statistic", "KS df", "KS Sig.", "SW Statistic", "SW df", "SW Sig."])],
        )
        for gi, g in enumerate(groups):
            v = stats.valid_values(g)
            n = v.size
            ks_stat = ks_p = sw_stat = sw_p = float("nan")
            if n >= 3 and v.std(ddof=1) > 0:
                try:
                    from statsmodels.stats.diagnostic import lilliefors

                    ks_stat, ks_p = lilliefors(v, dist="norm")
                except Exception:
                    ks_stat, ks_p = sps.kstest((v - v.mean()) / v.std(ddof=1), "norm")[:2]
                sw_stat, sw_p = sps.shapiro(v)
            from .base import strip_leading_zero

            t.set([gi], [0], _F3.render(float(ks_stat)) if ks_stat == ks_stat else ".")
            t.set([gi], [1], _F0.render(n))
            t.set([gi], [2], strip_leading_zero(_F3.render(float(ks_p))) if ks_p == ks_p else ".")
            t.set([gi], [3], _F3.render(float(sw_stat)) if sw_stat == sw_stat else ".")
            t.set([gi], [4], _F0.render(n))
            t.set([gi], [5], strip_leading_zero(_F3.render(float(sw_p))) if sw_p == sw_p else ".")
        return t.to_json()

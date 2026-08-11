"""REGRESSION — linear regression, ENTER method (HLD 6/9).

Model Summary, ANOVA, and Coefficients (B, Std. Error, Beta, t, Sig.).
Listwise deletion (SPSS default). Uses statsmodels OLS for parity.
"""
from __future__ import annotations

import math
import re
from typing import Any

import numpy as np
import pandas as pd

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure
from .base import strip_leading_zero

_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)


class Regression(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        dep = None
        preds: list[str] = []
        want_ci = False
        want_desc = False
        allnames = [v.name for v in ds.variables]
        for name, b in subs:
            if name == "DEPENDENT":
                dep = expand_varlist(b, allnames)[0]
            elif name == "METHOD":
                body = re.sub(r"^\s*ENTER\s*", "", b, flags=re.IGNORECASE)
                preds += expand_varlist(body, allnames)
            elif name == "STATISTICS":
                up = b.upper()
                want_ci = "CI" in up
                want_desc = "DESCRIPTIVES" in up or "DESCRIPTIVE" in up
        if dep is None or not preds:
            return [{"type": "Error", "text": "REGRESSION needs /DEPENDENT and /METHOD=ENTER predictors."}]

        import statsmodels.api as sm

        cols = [dep] + preds
        frame = {}
        for nm in cols:
            s = ds.df[nm]
            frame[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
        data = pd.DataFrame(frame).dropna()
        y = data[dep].to_numpy(float)
        X = data[preds].to_numpy(float)
        Xc = sm.add_constant(X)
        model = sm.OLS(y, Xc).fit()

        n = len(y)
        k = len(preds)
        r2 = float(model.rsquared)
        out: list[dict[str, Any]] = [{"type": "Title", "text": "Regression"}]

        if want_desc:
            dt = PivotTable("Descriptive Statistics", [Dimension("", [dep] + preds)],
                            [Dimension("", ["Mean", "Std. Deviation", "N"])])
            for i, nm in enumerate([dep] + preds):
                col = data[nm].to_numpy(float)
                dt.set([i], [0], _F3.render(float(col.mean())))
                dt.set([i], [1], _F3.render(float(col.std(ddof=1))))
                dt.set([i], [2], _F0.render(len(col)))
            out.append(dt.to_json())

        ms = PivotTable("Model Summary", [Dimension("", ["1"])],
                        [Dimension("", ["R", "R Square", "Adjusted R Square", "Std. Error of the Estimate"])])
        ms.set([0], [0], strip_leading_zero(_F3.render(math.sqrt(r2))))
        ms.set([0], [1], strip_leading_zero(_F3.render(r2)))
        ms.set([0], [2], strip_leading_zero(_F3.render(float(model.rsquared_adj))))
        ms.set([0], [3], _F3.render(float(math.sqrt(model.mse_resid))))
        out.append(ms.to_json())

        an = PivotTable("ANOVA", [Dimension("", ["Regression", "Residual", "Total"])],
                        [Dimension("", ["Sum of Squares", "df", "Mean Square", "F", "Sig."])])
        ssr, sse = float(model.ess), float(model.ssr)
        an.set([0], [0], _F3.render(ssr))
        an.set([0], [1], _F0.render(k))
        an.set([0], [2], _F3.render(ssr / k))
        an.set([0], [3], _F3.render(float(model.fvalue)))
        an.set([0], [4], strip_leading_zero(_F3.render(float(model.f_pvalue))))
        an.set([1], [0], _F3.render(sse))
        an.set([1], [1], _F0.render(n - k - 1))
        an.set([1], [2], _F3.render(sse / (n - k - 1)))
        an.set([2], [0], _F3.render(ssr + sse))
        an.set([2], [1], _F0.render(n - 1))
        out.append(an.to_json())

        # Coefficients with standardized Beta.
        sd_y = y.std(ddof=1)
        cols = ["B", "Std. Error", "Beta", "t", "Sig."]
        if want_ci:
            cols += ["95% CI Lower", "95% CI Upper"]
        co = PivotTable(
            "Coefficients",
            [Dimension("", ["(Constant)"] + preds)],
            [Dimension("", cols)],
        )
        params, bse, tvals, pvals = model.params, model.bse, model.tvalues, model.pvalues
        ci = model.conf_int(0.05) if want_ci else None
        co.set([0], [0], _F3.render(float(params[0])))
        co.set([0], [1], _F3.render(float(bse[0])))
        co.set([0], [2], "")
        co.set([0], [3], _F3.render(float(tvals[0])))
        co.set([0], [4], strip_leading_zero(_F3.render(float(pvals[0]))))
        if want_ci:
            co.set([0], [5], _F3.render(float(ci[0][0])))
            co.set([0], [6], _F3.render(float(ci[0][1])))
        for i, nm in enumerate(preds, start=1):
            beta = float(params[i]) * X[:, i - 1].std(ddof=1) / sd_y if sd_y else float("nan")
            co.set([i], [0], _F3.render(float(params[i])))
            co.set([i], [1], _F3.render(float(bse[i])))
            co.set([i], [2], strip_leading_zero(_F3.render(beta)))
            co.set([i], [3], _F3.render(float(tvals[i])))
            co.set([i], [4], strip_leading_zero(_F3.render(float(pvals[i]))))
            if want_ci:
                co.set([i], [5], _F3.render(float(ci[i][0])))
                co.set([i], [6], _F3.render(float(ci[i][1])))
        out.append(co.to_json())
        return out

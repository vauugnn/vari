"""Remaining Regression procedures: Probit, Partial Least Squares, 2-Stage
Least Squares; plus GLM Variance Components and Repeated Measures.

Kept library-light: 2SLS is an explicit two-stage OLS (statsmodels), so no
extra dependency. Probit uses statsmodels Probit; PLS uses sklearn; Variance
Components uses statsmodels MixedLM; Repeated Measures uses statsmodels AnovaRM.
"""
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
from .base import strip_leading_zero

_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)


def _clean(ds: Any, names: list[str]) -> pd.DataFrame:
    frame = {}
    for nm in names:
        s = ds.df[nm]
        frame[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
    return pd.DataFrame(frame).dropna()


def _coef_table(title, caption, names, b, se, stat, statname, p):
    rows = ["(Constant)"] + names
    t = PivotTable(title, [Dimension("", rows)],
                   [Dimension("", ["B", "Std. Error", statname, "Sig."])], caption=caption)
    for i in range(len(rows)):
        t.set([i], [0], _F3.render(float(b[i])))
        t.set([i], [1], _F3.render(float(se[i])))
        t.set([i], [2], _F3.render(float(stat[i])))
        t.set([i], [3], strip_leading_zero(_F3.render(float(p[i]))))
    return t


class Probit(DataProcedure):
    """PROBIT y WITH x1 x2 — binary probit regression."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        m = re.search(r"(.+?)\bWITH\b(.+)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "PROBIT needs 'y WITH predictors'."}]
        dep = expand_varlist(m.group(1), allnames)[0]
        preds = expand_varlist(m.group(2), allnames)
        data = _clean(ds, [dep] + preds)
        import statsmodels.api as sm

        X = sm.add_constant(data[preds].to_numpy(float))
        y = data[dep].to_numpy(float)
        model = sm.Probit(y, X).fit(disp=0)
        t = _coef_table("Parameter Estimates", f"Dependent Variable: {dep}", preds,
                        model.params, model.bse, model.tvalues, "Z", model.pvalues)
        return [{"type": "Title", "text": "Probit Regression"}, t.to_json()]


class Pls(DataProcedure):
    """PLS dep WITH preds [/COMPONENTS n] — partial least squares regression."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        m = re.search(r"(.+?)\bWITH\b(.+)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "PLS needs 'dep WITH predictors'."}]
        dep = expand_varlist(m.group(1), allnames)[0]
        preds = expand_varlist(m.group(2), allnames)
        ncomp = 2
        for name, b in subs:
            if name.upper() == "COMPONENTS":
                ncomp = int(re.search(r"\d+", b).group()) if re.search(r"\d+", b) else 2
        ncomp = min(ncomp, len(preds))
        data = _clean(ds, [dep] + preds)
        from sklearn.cross_decomposition import PLSRegression

        X = data[preds].to_numpy(float)
        y = data[dep].to_numpy(float)
        pls = PLSRegression(n_components=ncomp, scale=True)
        pls.fit(X, y)
        r2 = float(pls.score(X, y))
        coefs = np.asarray(pls.coef_).ravel()
        rows = list(preds)
        t = PivotTable("Parameters", [Dimension("", rows)], [Dimension("", ["Coefficient"])],
                       caption=f"Dependent Variable: {dep}   (R Squared = {r2:.3f}, {ncomp} components)")
        for i, _ in enumerate(rows):
            t.set([i], [0], _F3.render(float(coefs[i])))
        return [{"type": "Title", "text": "Partial Least Squares Regression"}, t.to_json()]


class Tsls(DataProcedure):
    """2SLS dep WITH regressors /INSTRUMENTS instruments — two-stage least squares."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        allnames = [v.name for v in ds.variables]
        main = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        m = re.search(r"(.+?)\bWITH\b(.+)", main, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "2SLS needs 'dep WITH regressors /INSTRUMENTS ...'."}]
        dep = expand_varlist(m.group(1), allnames)[0]
        regressors = expand_varlist(m.group(2), allnames)
        insts: list[str] = []
        for name, b in subs:
            if name.upper() == "INSTRUMENTS":
                insts = expand_varlist(b, allnames)
        if not insts:
            return [{"type": "Error", "text": "2SLS needs /INSTRUMENTS."}]
        data = _clean(ds, list({dep, *regressors, *insts}))

        import statsmodels.api as sm

        # Exogenous regressors are those also listed as instruments; endogenous
        # are the rest. Stage 1: fit each endogenous on all instruments+exog.
        exog = [r for r in regressors if r in insts]
        endog = [r for r in regressors if r not in insts]
        Z = sm.add_constant(data[insts + [e for e in exog if e not in insts]].to_numpy(float))
        fitted = {}
        for e in endog:
            fitted[e] = sm.OLS(data[e].to_numpy(float), Z).fit().fittedvalues
        # Stage 2: dep ~ [exog + fitted endogenous]
        cols = []
        names = []
        for r in regressors:
            names.append(r)
            cols.append(fitted[r] if r in endog else data[r].to_numpy(float))
        X2 = sm.add_constant(np.column_stack(cols))
        y = data[dep].to_numpy(float)
        res = sm.OLS(y, X2).fit()
        t = _coef_table("Coefficients", f"Dependent Variable: {dep}", names,
                        res.params, res.bse, res.tvalues, "t", res.pvalues)
        return [{"type": "Title", "text": "Two-Stage Least Squares"}, t.to_json()]


class Varcomp(DataProcedure):
    """VARCOMP dep BY factor /RANDOM=factor — variance component estimates."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        m = re.search(r"(.+?)\bBY\b(.+)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "VARCOMP needs 'dep BY factor'."}]
        dep = expand_varlist(m.group(1), allnames)[0]
        factor = expand_varlist(m.group(2), allnames)[0]
        data = _clean(ds, [dep, factor])

        import statsmodels.formula.api as smf

        md = smf.mixedlm(f"Q('{dep}') ~ 1", data, groups=data[factor])
        res = md.fit()
        between = float(res.cov_re.iloc[0, 0])
        resid = float(res.scale)
        rows = [f"{factor}", "Error"]
        t = PivotTable("Variance Estimates", [Dimension("Component", rows)],
                       [Dimension("", ["Estimate"])], caption=f"Dependent Variable: {dep}")
        t.set([0], [0], _F3.render(between))
        t.set([1], [0], _F3.render(resid))
        return [{"type": "Title", "text": "Variance Components"}, t.to_json()]


class GlmRepeated(DataProcedure):
    """GLMRM y1 y2 y3 [/WSFACTOR name k] — one within-subject factor
    (repeated measures ANOVA)."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        levels = expand_varlist(body, allnames)
        wsname = "factor1"
        for name, b in subs:
            if name.upper() == "WSFACTOR":
                mm = re.match(r"\s*(\w+)", b)
                if mm:
                    wsname = mm.group(1)
        if len(levels) < 2:
            return [{"type": "Error", "text": "Repeated Measures needs 2+ level variables."}]
        data = _clean(ds, levels).reset_index(drop=True)
        # Wide -> long with a synthetic subject id.
        data["_subj"] = np.arange(len(data))
        long = data.melt(id_vars="_subj", value_vars=levels, var_name=wsname, value_name="_y")

        from statsmodels.stats.anova import AnovaRM

        res = AnovaRM(long, "_y", "_subj", within=[wsname]).fit()
        tab = res.anova_table
        f = float(tab.loc[wsname, "F Value"])
        df1 = float(tab.loc[wsname, "Num DF"])
        df2 = float(tab.loc[wsname, "Den DF"])
        p = float(tab.loc[wsname, "Pr > F"])
        t = PivotTable(
            "Tests of Within-Subjects Effects",
            [Dimension("Source", [wsname, "Error"])],
            [Dimension("", ["F", "df1", "df2", "Sig."])],
            caption="Sphericity Assumed",
        )
        t.set([0], [0], _F3.render(f))
        t.set([0], [1], _F3.render(df1))
        t.set([0], [2], _F3.render(df2))
        t.set([0], [3], strip_leading_zero(_F3.render(p)))
        return [{"type": "Title", "text": "General Linear Model — Repeated Measures"}, t.to_json()]

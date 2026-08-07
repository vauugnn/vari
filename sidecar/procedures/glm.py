"""UNIANOVA — GLM Univariate: factorial ANOVA with Type III sums of squares
(SPSS default, HLD 6 Tier 2 / HLD 9)."""
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
from .base import strip_leading_zero, value_label

_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)


class Unianova(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = ""
        for name, b in subs:
            if name in ("", "VARIABLES"):
                body += " " + b
        allnames = [v.name for v in ds.variables]
        m = re.search(r"(.+?)\bBY\b(.+)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "UNIANOVA needs 'dependent BY factors'."}]
        dep = expand_varlist(m.group(1), allnames)[0]
        rhs = m.group(2)
        cov: list[str] = []
        mw = re.search(r"(.+?)\bWITH\b(.+)", rhs, re.IGNORECASE)
        if mw:
            factors = expand_varlist(mw.group(1), allnames)
            cov = expand_varlist(mw.group(2), allnames)
        else:
            factors = expand_varlist(rhs, allnames)

        cols = [dep] + factors + cov
        frame = {}
        for nm in cols:
            s = ds.df[nm]
            frame[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
        data = pd.DataFrame(frame).dropna()

        import statsmodels.api as sm
        import statsmodels.formula.api as smf
        from statsmodels.stats.anova import anova_lm

        terms = [f"C(Q('{f}'), Sum)" for f in factors]
        design = " * ".join(terms) if terms else "1"
        if cov:
            design += " + " + " + ".join(f"Q('{c}')" for c in cov)
        formula = f"Q('{dep}') ~ {design}"
        model = smf.ols(formula, data=data).fit()
        at = anova_lm(model, typ=3)

        # Assemble the SPSS "Tests of Between-Subjects Effects" table.
        n = len(data)
        resid_ss = float(at.loc["Residual", "sum_sq"])
        resid_df = int(at.loc["Residual", "df"])
        term_rows = [ix for ix in at.index if ix not in ("Intercept", "Residual")]
        model_ss = sum(float(at.loc[ix, "sum_sq"]) for ix in term_rows)
        model_df = sum(int(at.loc[ix, "df"]) for ix in term_rows)
        inter_ss = float(at.loc["Intercept", "sum_sq"])
        inter_df = int(at.loc["Intercept", "df"])
        corrected_total = model_ss + resid_ss
        mse = resid_ss / resid_df if resid_df else float("nan")

        def label_of(ix: str) -> str:
            found = re.findall(r"Q\('([^']+)'\)", ix)
            return " * ".join(found) if found else ix

        rows = ["Corrected Model", "Intercept"] + [label_of(ix) for ix in term_rows] + ["Error", "Total", "Corrected Total"]
        t = PivotTable(
            "Tests of Between-Subjects Effects",
            [Dimension("Source", rows)],
            [Dimension("", ["Type III Sum of Squares", "df", "Mean Square", "F", "Sig."])],
            caption=f"Dependent Variable: {dep}",
        )

        def put(i, ss, df, f=None, sig=None):
            t.set([i], [0], _F3.render(ss))
            t.set([i], [1], _F0.render(df))
            t.set([i], [2], _F3.render(ss / df) if df else "")
            t.set([i], [3], _F3.render(f) if f is not None else "")
            t.set([i], [4], strip_leading_zero(_F3.render(sig)) if sig is not None else "")

        from scipy import stats as sps

        put(0, model_ss, model_df, (model_ss / model_df) / mse if mse else None,
            float(sps.f.sf((model_ss / model_df) / mse, model_df, resid_df)) if mse else None)
        put(1, inter_ss, inter_df, (inter_ss / inter_df) / mse if mse else None,
            float(sps.f.sf((inter_ss / inter_df) / mse, inter_df, resid_df)) if mse else None)
        for k, ix in enumerate(term_rows, start=2):
            ss = float(at.loc[ix, "sum_sq"]); df = int(at.loc[ix, "df"])
            f = float(at.loc[ix, "F"]); sig = float(at.loc[ix, "PR(>F)"])
            put(k, ss, df, f, sig)
        base = 2 + len(term_rows)
        put(base, resid_ss, resid_df)
        # Total (uncorrected) = sum of squares of y
        y = data[dep].to_numpy(float)
        t.set([base + 1], [0], _F3.render(float((y**2).sum())))
        t.set([base + 1], [1], _F0.render(n))
        t.set([base + 2], [0], _F3.render(corrected_total))
        t.set([base + 2], [1], _F0.render(n - 1))

        r2 = model_ss / corrected_total if corrected_total else float("nan")
        t.caption = f"Dependent Variable: {dep}   (R Squared = {r2:.3f})"

        out: list[dict[str, Any]] = [{"type": "Title", "text": "Univariate Analysis of Variance"}]
        out.append(self._factors_table(ds, factors, data))
        out.append(t.to_json())
        return out

    def _factors_table(self, ds, factors, data):
        rows = []
        for f in factors:
            for lv in sorted(data[f].unique()):
                rows.append(f"{f}|{value_label(ds, f, lv)}")
        t = PivotTable("Between-Subjects Factors", [Dimension("", rows)], [Dimension("", ["N"])])
        i = 0
        for f in factors:
            for lv in sorted(data[f].unique()):
                t.set([i], [0], _F0.render(int((data[f] == lv).sum())))
                i += 1
        return t.to_json()

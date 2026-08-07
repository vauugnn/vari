"""CURVEFIT — Curve Estimation (linear/quadratic/cubic/log/exponential), Base."""
from __future__ import annotations

import re
from typing import Any

import numpy as np

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure
from .base import strip_leading_zero

_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)

_MODELS = {
    "LINEAR": "Linear", "QUADRATIC": "Quadratic", "CUBIC": "Cubic",
    "LOGARITHMIC": "Logarithmic", "EXPONENTIAL": "Exponential",
}


class CurveFit(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = ""
        models: list[str] = []
        for name, b in subs:
            if name in ("", "VARIABLES"):
                body += " " + re.sub(r"^\s*VARIABLES\s*=?\s*", "", b, flags=re.IGNORECASE)
            elif name == "MODEL":
                for kw in b.upper().split():
                    if kw in _MODELS:
                        models.append(kw)
        if not models:
            models = ["LINEAR"]
        allnames = [v.name for v in ds.variables]
        m = re.search(r"(.+?)\bWITH\b(.+)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "CURVEFIT needs 'y WITH x'."}]
        dep = expand_varlist(m.group(1), allnames)[0]
        indep = expand_varlist(m.group(2), allnames)[0]

        import pandas as pd

        cols = {c: ds.df[c].where(~missing_mask(ds.df[c], ds.variables[ds._index_of(c)]).to_numpy()) for c in (dep, indep)}
        data = pd.DataFrame(cols).dropna()
        y = data[dep].to_numpy(float)
        x = data[indep].to_numpy(float)

        import statsmodels.api as sm
        from scipy import stats as sps

        rows = [_MODELS[mm] for mm in models]
        t = PivotTable(f"{dep}", [Dimension("Equation", rows)],
                       [Dimension("", ["R Square", "F", "df1", "df2", "Sig.", "Constant", "b1", "b2", "b3"])],
                       corner="Equation", caption="Model Summary and Parameter Estimates")
        for i, mm in enumerate(models):
            yy, X, ncoef = _design(mm, x, y)
            if X is None:
                continue
            model = sm.OLS(yy, X).fit()
            params = list(model.params)
            const = params[0]
            if mm == "EXPONENTIAL":
                const = float(np.exp(const))
            t.set([i], [0], _F3.render(float(model.rsquared)))
            t.set([i], [1], _F3.render(float(model.fvalue)))
            t.set([i], [2], _F0.render(int(model.df_model)))
            t.set([i], [3], _F0.render(int(model.df_resid)))
            t.set([i], [4], strip_leading_zero(_F3.render(float(model.f_pvalue))))
            t.set([i], [5], _F3.render(const))
            for j in range(1, 4):
                t.set([i], [5 + j], _F3.render(float(params[j])) if j < len(params) else "")
        return [{"type": "Title", "text": "Curve Fit"}, t.to_json()]


def _design(model: str, x: np.ndarray, y: np.ndarray):
    import statsmodels.api as sm

    if model == "LINEAR":
        return y, sm.add_constant(x), 1
    if model == "QUADRATIC":
        return y, sm.add_constant(np.column_stack([x, x**2])), 2
    if model == "CUBIC":
        return y, sm.add_constant(np.column_stack([x, x**2, x**3])), 3
    if model == "LOGARITHMIC":
        if (x <= 0).any():
            return y, None, 0
        return y, sm.add_constant(np.log(x)), 1
    if model == "EXPONENTIAL":
        if (y <= 0).any():
            return y, None, 0
        return np.log(y), sm.add_constant(x), 1
    return y, None, 0

"""Binary Logistic (LOGISTIC REGRESSION), Ordinal (PLUM), Multinomial (NOMREG)
regression — HLD 6 Tier 2. Uses statsmodels."""
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


def _frame(ds, names):
    cols = {}
    for nm in names:
        s = ds.df[nm]
        cols[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
    return pd.DataFrame(cols).dropna()


def _parse_dep_preds(ds, rest):
    allnames = [v.name for v in ds.variables]
    rest = re.sub(r"^\s*VARIABLES\s*=?\s*", " ", rest, flags=re.IGNORECASE)
    mw = re.search(r"\bWITH\b(.+)", rest, re.IGNORECASE)
    mm = re.search(r"/\s*METHOD\s*=?\s*\w*\s*(.+)", rest, re.IGNORECASE)
    head = rest.split("/")[0]
    head = re.split(r"\bWITH\b", head, flags=re.IGNORECASE)[0]
    dep = expand_varlist(head, allnames)[0]
    if mw:
        preds = expand_varlist(mw.group(1).split("/")[0], allnames)
    elif mm:
        preds = expand_varlist(mm.group(1), allnames)
    else:
        preds = []
    return dep, preds


class LogisticRegression(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        rest = " ".join(f"{n} {b}" if n else b for n, b in subs)
        rest = re.sub(r"^\s*REGRESSION\s*", " ", rest, flags=re.IGNORECASE)
        dep, preds = _parse_dep_preds(ds, rest)
        if not preds:
            return [{"type": "Error", "text": "LOGISTIC REGRESSION needs predictors (WITH / METHOD=ENTER)."}]
        data = _frame(ds, [dep] + preds)
        import statsmodels.api as sm

        y = data[dep].to_numpy(float)
        # recode dep to 0/1 by its two sorted levels
        levels = sorted(np.unique(y))
        y01 = (y == levels[-1]).astype(float)
        X = sm.add_constant(data[preds].to_numpy(float))
        model = sm.Logit(y01, X).fit(disp=0)
        null = sm.Logit(y01, np.ones((len(y01), 1))).fit(disp=0)

        n = len(y01)
        ll, ll0 = model.llf, null.llf
        cs = 1 - math.exp((ll0 - ll) * 2 / n)
        nag = cs / (1 - math.exp(2 * ll0 / n))
        out: list[dict[str, Any]] = [{"type": "Title", "text": "Logistic Regression"}]

        ms = PivotTable("Model Summary", [Dimension("", ["1"])],
                        [Dimension("", ["-2 Log likelihood", "Cox & Snell R Square", "Nagelkerke R Square"])])
        ms.set([0], [0], _F3.render(-2 * ll)); ms.set([0], [1], _F3.render(cs)); ms.set([0], [2], _F3.render(nag))
        out.append(ms.to_json())

        rows = preds + ["Constant"]
        t = PivotTable("Variables in the Equation", [Dimension("", rows)],
                       [Dimension("", ["B", "S.E.", "Wald", "df", "Sig.", "Exp(B)"])])
        params, bse = model.params, model.bse
        idx = list(range(1, len(preds) + 1)) + [0]  # predictors then const
        for r, pi in enumerate(idx):
            b = float(params[pi]); se = float(bse[pi]); wald = (b / se) ** 2
            from scipy import stats as sps

            sig = float(sps.chi2.sf(wald, 1))
            t.set([r], [0], _F3.render(b)); t.set([r], [1], _F3.render(se)); t.set([r], [2], _F3.render(wald))
            t.set([r], [3], _F0.render(1)); t.set([r], [4], strip_leading_zero(_F3.render(sig)))
            t.set([r], [5], _F3.render(math.exp(b)))
        out.append(t.to_json())
        return out


class Nomreg(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        rest = " ".join(f"{n} {b}" if n else b for n, b in subs)
        dep, preds = _parse_dep_preds(ds, rest.replace("BY", "WITH"))
        if not preds:
            return [{"type": "Error", "text": "NOMREG needs predictors."}]
        data = _frame(ds, [dep] + preds)
        import statsmodels.api as sm

        X = sm.add_constant(data[preds].to_numpy(float))
        model = sm.MNLogit(data[dep].to_numpy(float), X).fit(disp=0)
        params = np.asarray(model.params)
        bse = np.asarray(model.bse)
        rows = []
        for e in range(params.shape[1]):
            for name in ["Constant"] + preds:
                rows.append(f"Eq{e + 1}|{name}")
        t = PivotTable("Parameter Estimates", [Dimension("", rows)], [Dimension("", ["B", "Std. Error", "Sig."])])
        i = 0
        from scipy import stats as sps

        for e in range(params.shape[1]):
            for pi in range(params.shape[0]):
                b = float(params[pi, e]); se = float(bse[pi, e])
                z = b / se if se else float("nan")
                t.set([i], [0], _F3.render(b)); t.set([i], [1], _F3.render(se))
                t.set([i], [2], strip_leading_zero(_F3.render(float(2 * sps.norm.sf(abs(z))))))
                i += 1
        return [{"type": "Title", "text": "Multinomial Logistic Regression"}, t.to_json()]


class Plum(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        rest = " ".join(f"{n} {b}" if n else b for n, b in subs)
        dep, preds = _parse_dep_preds(ds, rest.replace(" BY ", " WITH ").replace(" by ", " WITH "))
        if not preds:
            return [{"type": "Error", "text": "PLUM needs predictors."}]
        data = _frame(ds, [dep] + preds)
        from statsmodels.miscmodels.ordinal_model import OrderedModel

        model = OrderedModel(data[dep].to_numpy(float), data[preds].to_numpy(float), distr="logit").fit(method="bfgs", disp=0)
        rows = preds + [f"Threshold {i + 1}" for i in range(len(model.params) - len(preds))]
        t = PivotTable("Parameter Estimates", [Dimension("", rows)],
                       [Dimension("", ["Estimate", "Std. Error", "Wald", "Sig."])])
        from scipy import stats as sps

        for r in range(len(model.params)):
            b = float(model.params[r]); se = float(model.bse[r]); wald = (b / se) ** 2
            t.set([r], [0], _F3.render(b)); t.set([r], [1], _F3.render(se)); t.set([r], [2], _F3.render(wald))
            t.set([r], [3], strip_leading_zero(_F3.render(float(sps.chi2.sf(wald, 1)))))
        return [{"type": "Title", "text": "Ordinal Regression"}, t.to_json()]

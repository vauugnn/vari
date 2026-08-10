"""GLM Multivariate (MANOVA), PROXIMITIES (Distances), and Canonical Correlation.

MANOVA reports SPSS's four multivariate tests (Pillai's Trace, Wilks' Lambda,
Hotelling's Trace, Roy's Largest Root) per effect. PROXIMITIES builds a
case-by-case or variable-by-variable distance matrix. CANCORR reports canonical
correlations and Wilks' lambda dimension-reduction tests.
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


class Manova(DataProcedure):
    """GLM dep1 dep2 [...] BY factor[ factor...] — multivariate ANOVA."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        m = re.search(r"(.+?)\bBY\b(.+)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "GLM needs 'dep1 dep2 BY factor'."}]
        deps = expand_varlist(m.group(1), allnames)
        factors = expand_varlist(m.group(2), allnames)
        if len(deps) < 2:
            return [{"type": "Error", "text": "GLM multivariate needs 2+ dependent variables."}]
        data = _clean(ds, deps + factors)

        from statsmodels.multivariate.manova import MANOVA

        lhs = " + ".join(f"Q('{d}')" for d in deps)
        rhs = " + ".join(f"C(Q('{f}'))" for f in factors)
        res = MANOVA.from_formula(f"{lhs} ~ {rhs}", data=data).mv_test()

        stat_names = ["Pillai's Trace", "Wilks' Lambda", "Hotelling's Trace", "Roy's Largest Root"]
        # statsmodels labels rows: "Pillai's trace","Wilks' lambda","Hotelling-Lawley trace","Roy's greatest root"
        sm_keys = ["Pillai's trace", "Wilks' lambda", "Hotelling-Lawley trace", "Roy's greatest root"]

        effects = [k for k in res.results.keys() if k != "Intercept"]
        rows: list[str] = []
        for eff in ["Intercept"] + effects:
            for sn in stat_names:
                rows.append(f"{eff}|{sn}")
        t = PivotTable(
            "Multivariate Tests",
            [Dimension("Effect", rows)],
            [Dimension("", ["Value", "F", "Hypothesis df", "Error df", "Sig."])],
        )
        i = 0
        for eff in ["Intercept"] + effects:
            tbl = res.results[eff]["stat"]
            for sn, key in zip(stat_names, sm_keys):
                r = tbl.loc[key]
                t.set([i], [0], _F3.render(float(r["Value"])))
                t.set([i], [1], _F3.render(float(r["F Value"])))
                t.set([i], [2], _F3.render(float(r["Num DF"])))
                t.set([i], [3], _F3.render(float(r["Den DF"])))
                t.set([i], [4], strip_leading_zero(_F3.render(float(r["Pr > F"]))))
                i += 1

        return [{"type": "Title", "text": "General Linear Model"}, t.to_json()]


class Proximities(DataProcedure):
    """PROXIMITIES var list [/MEASURE=EUCLID|SEUCLID|BLOCK|CHEBYCHEV|COSINE]
    [/VIEW=CASE|VARIABLE] — distance matrix (Data ▸ ... / Analyze ▸ Distances)."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        names = expand_varlist(body, allnames)
        measure = "EUCLID"
        view = "CASE"
        for name, b in subs:
            if name.upper() == "MEASURE":
                measure = b.strip().upper() or "EUCLID"
            elif name.upper() == "VIEW":
                view = b.strip().upper() or "CASE"
        if len(names) < 1:
            return [{"type": "Error", "text": "PROXIMITIES needs variables."}]
        data = _clean(ds, names)
        X = data.to_numpy(float)

        from scipy.spatial.distance import pdist, squareform

        metric = {
            "EUCLID": "euclidean",
            "SEUCLID": "sqeuclidean",
            "BLOCK": "cityblock",
            "CHEBYCHEV": "chebyshev",
            "COSINE": "cosine",
        }.get(measure, "euclidean")

        if view == "VARIABLE":
            M = squareform(pdist(X.T, metric=metric))
            labels = names
        else:
            M = squareform(pdist(X, metric=metric))
            labels = [str(k + 1) for k in range(M.shape[0])]
            if len(labels) > 40:  # keep the table readable
                labels = labels[:40]
                M = M[:40, :40]

        cap = {"euclidean": "Euclidean Distance", "sqeuclidean": "Squared Euclidean Distance",
               "cityblock": "Block", "chebyshev": "Chebychev", "cosine": "Cosine"}[metric]
        t = PivotTable(
            "Proximity Matrix",
            [Dimension("Case" if view == "CASE" else "Variable", list(labels))],
            [Dimension(cap, list(labels))],
        )
        for r in range(len(labels)):
            for c in range(len(labels)):
                t.set([r], [c], _F3.render(float(M[r, c])))
        return [{"type": "Title", "text": "Proximities"}, t.to_json()]


class CanCorr(DataProcedure):
    """CANCORR set1 WITH set2 — canonical correlation analysis."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        m = re.search(r"(.+?)\bWITH\b(.+)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "CANCORR needs 'set1 WITH set2'."}]
        set1 = expand_varlist(m.group(1), allnames)
        set2 = expand_varlist(m.group(2), allnames)
        data = _clean(ds, set1 + set2)
        X = data[set1].to_numpy(float)
        Y = data[set2].to_numpy(float)
        k = min(len(set1), len(set2))

        from sklearn.cross_decomposition import CCA

        cca = CCA(n_components=k, scale=True)
        Xc, Yc = cca.fit_transform(X, Y)
        corrs = [float(np.corrcoef(Xc[:, j], Yc[:, j])[0, 1]) for j in range(k)]

        # Wilks' lambda dimension-reduction test (Bartlett's chi-square).
        from scipy import stats as sps

        n = len(data)
        p, q = len(set1), len(set2)
        rows = [f"{j + 1}" for j in range(k)]
        t = PivotTable(
            "Canonical Correlations",
            [Dimension("Function", rows)],
            [Dimension("", ["Canonical Correlation", "Wilks' Lambda", "Chi-Square", "df", "Sig."])],
        )
        r2 = np.array([c**2 for c in corrs])
        for j in range(k):
            lam = float(np.prod(1 - r2[j:]))
            df = (p - j) * (q - j)
            chi = -(n - 1 - (p + q + 1) / 2) * np.log(lam)
            sig = float(sps.chi2.sf(chi, df))
            t.set([j], [0], _F3.render(abs(corrs[j])))
            t.set([j], [1], _F3.render(lam))
            t.set([j], [2], _F3.render(float(chi)))
            t.set([j], [3], _F0.render(df))
            t.set([j], [4], strip_leading_zero(_F3.render(sig)))
        return [{"type": "Title", "text": "Canonical Correlation Analysis"}, t.to_json()]

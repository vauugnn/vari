"""Dimension Reduction: Correspondence Analysis (CORRESPONDENCE) and
Multidimensional Scaling (PROXSCAL / ALSCAL / PREFSCAL)."""
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


class Correspondence(DataProcedure):
    """CORRESPONDENCE TABLE=row BY col — simple correspondence analysis (SVD)."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(re.sub(r"^\s*TABLE\s*=\s*", "", b, flags=re.IGNORECASE)
                        for name, b in subs if name in ("", "VARIABLES", "TABLE"))
        allnames = [v.name for v in ds.variables]
        m = re.search(r"(\w+)\s+BY\s+(\w+)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "CORRESPONDENCE needs 'TABLE=row BY col'."}]
        row, col = m.group(1), m.group(2)
        data = _clean(ds, [row, col])
        ct = pd.crosstab(data[row], data[col]).to_numpy(float)
        N = ct.sum()
        P = ct / N
        r = P.sum(1)
        c = P.sum(0)
        Dr = np.diag(1 / np.sqrt(r))
        Dc = np.diag(1 / np.sqrt(c))
        S = Dr @ (P - np.outer(r, c)) @ Dc
        U, sv, _ = np.linalg.svd(S, full_matrices=False)
        sv = sv[sv > 1e-9]
        inertia = sv ** 2
        total = inertia.sum()
        rows = [f"{i + 1}" for i in range(len(sv))]
        t = PivotTable("Summary", [Dimension("Dimension", rows)],
                       [Dimension("", ["Singular Value", "Inertia", "Proportion", "Cumulative"])],
                       caption=f"Total inertia = {total:.4f}")
        cum = 0.0
        for i in range(len(sv)):
            prop = inertia[i] / total if total else 0.0
            cum += prop
            t.set([i], [0], _F3.render(float(sv[i])))
            t.set([i], [1], _F3.render(float(inertia[i])))
            t.set([i], [2], _F3.render(float(prop)))
            t.set([i], [3], _F3.render(float(cum)))
        return [{"type": "Title", "text": "Correspondence Analysis"}, t.to_json()]


class Mds(DataProcedure):
    """PROXSCAL / ALSCAL / PREFSCAL var list [/DIMENSIONS n] — MDS on the
    Euclidean distances among cases; reports stress and fit."""

    metric = True

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        names = expand_varlist(body, allnames)
        dims = 2
        for name, b in subs:
            if name.upper() in ("DIMENSIONS", "CRITERIA"):
                mm = re.search(r"\d+", b)
                if mm:
                    dims = int(mm.group())
        data = _clean(ds, names)
        X = data.to_numpy(float)
        # Limit to a manageable number of objects.
        if len(X) > 60:
            X = X[:60]
        from scipy.spatial.distance import pdist, squareform
        from sklearn.manifold import MDS as SKMDS

        D = squareform(pdist(X, metric="euclidean"))
        mds = SKMDS(n_components=dims, dissimilarity="precomputed",
                    metric=self.metric, normalized_stress="auto", random_state=0)
        coords = mds.fit_transform(D)
        raw_stress = float(mds.stress_)
        # Kruskal's Stress-1.
        dhat = squareform(pdist(coords))
        denom = (D ** 2).sum()
        stress1 = float(np.sqrt(((D - dhat) ** 2).sum() / denom)) if denom else 0.0
        t = PivotTable("Stress and Fit Measures", [Dimension("", ["Raw Stress", "Stress-I", "Dimensions", "Objects"])],
                       [Dimension("", ["Value"])])
        t.set([0], [0], _F3.render(raw_stress))
        t.set([1], [0], _F3.render(stress1))
        t.set([2], [0], _F0.render(dims))
        t.set([3], [0], _F0.render(len(X)))
        return [{"type": "Title", "text": "Multidimensional Scaling"}, t.to_json()]


class Alscal(Mds):
    metric = False  # ALSCAL/PREFSCAL default to ordinal (non-metric) scaling.

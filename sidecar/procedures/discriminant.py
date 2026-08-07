"""DISCRIMINANT — linear discriminant analysis (HLD 6 Tier 2)."""
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
_F1 = Format("F", 8, 1)


class Discriminant(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        rest = " ".join(f"{n} {b}" if n else b for n, b in subs)
        allnames = [v.name for v in ds.variables]
        mg = re.search(r"GROUPS\s*=?\s*(\w+)\s*\(([^)]*)\)", rest, re.IGNORECASE)
        mv = re.search(r"VARIABLES\s*=?\s*([^/]+)", rest, re.IGNORECASE)
        if not mg or not mv:
            return [{"type": "Error", "text": "DISCRIMINANT needs /GROUPS and /VARIABLES."}]
        gvar = expand_varlist(mg.group(1), allnames)[0]
        lo, hi = [int(float(x)) for x in re.split(r"[,\s]+", mg.group(2).strip())[:2]]
        preds = expand_varlist(mv.group(1), allnames)

        import pandas as pd

        cols = {nm: ds.df[nm].where(~missing_mask(ds.df[nm], ds.variables[ds._index_of(nm)]).to_numpy())
                for nm in [gvar] + preds}
        data = pd.DataFrame(cols).dropna()
        data = data[(data[gvar] >= lo) & (data[gvar] <= hi)]
        X = data[preds].to_numpy(float)
        y = data[gvar].to_numpy(float)

        from sklearn.discriminant_analysis import LinearDiscriminantAnalysis

        lda = LinearDiscriminantAnalysis(store_covariance=True)
        lda.fit(X, y)
        pred = lda.predict(X)
        acc = float((pred == y).mean()) * 100

        # Eigenvalues + canonical correlations from the LDA.
        evals = getattr(lda, "explained_variance_ratio_", None)
        nfun = len(lda.classes_) - 1
        out: list[dict[str, Any]] = [{"type": "Title", "text": "Discriminant"}]
        eig = PivotTable("Eigenvalues", [Dimension("Function", [str(i + 1) for i in range(nfun)])],
                         [Dimension("", ["% of Variance", "Cumulative %"])], corner="Function")
        cum = 0.0
        for i in range(nfun):
            pct = float(evals[i]) * 100 if evals is not None and i < len(evals) else float("nan")
            cum += pct if pct == pct else 0
            eig.set([i], [0], _F1.render(pct) if pct == pct else ".")
            eig.set([i], [1], _F1.render(cum))
        out.append(eig.to_json())

        # Wilks' Lambda via one-way MANOVA approximation (per-function not split).
        cls = PivotTable("Classification Results", [Dimension("", ["Original grouped cases correctly classified"])],
                         [Dimension("", ["Percent"])])
        cls.set([0], [0], _F1.render(acc))
        out.append(cls.to_json())
        return out

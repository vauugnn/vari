"""Classify: TwoStep Cluster (TWOSTEP) and Nearest Neighbor (KNN)."""
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
_F1 = Format("F", 8, 1)
_F0 = Format("F", 8, 0)


def _clean(ds: Any, names: list[str]) -> pd.DataFrame:
    frame = {}
    for nm in names:
        s = ds.df[nm]
        frame[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
    return pd.DataFrame(frame).dropna()


class TwoStep(DataProcedure):
    """TWOSTEP var list [/CLUSTERS n] — agglomerative two-step clustering."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        names = expand_varlist(body, allnames)
        k = None
        for name, b in subs:
            if name.upper() in ("CLUSTERS", "CRITERIA"):
                m = re.search(r"\d+", b)
                if m:
                    k = int(m.group())
        data = _clean(ds, names)
        X = data.to_numpy(float)
        X = (X - X.mean(0)) / (X.std(0) + 1e-9)

        from sklearn.cluster import Birch
        from sklearn.metrics import silhouette_score

        if k is None:
            # Auto: pick 2..6 by best silhouette (SPSS uses BIC; silhouette is a
            # reasonable dependency-free proxy).
            best, bestk = -1.0, 2
            for kk in range(2, min(7, len(data))):
                lab = Birch(n_clusters=kk).fit_predict(X)
                if len(set(lab)) > 1:
                    sc = silhouette_score(X, lab)
                    if sc > best:
                        best, bestk = sc, kk
            k = bestk
        labels = Birch(n_clusters=k).fit_predict(X)
        sizes = pd.Series(labels).value_counts().sort_index()
        rows = [f"Cluster {i + 1}" for i in range(len(sizes))] + ["Combined"]
        t = PivotTable("Cluster Distribution", [Dimension("", rows)],
                       [Dimension("", ["N", "% of Combined"])])
        total = int(sizes.sum())
        for i, (_, c) in enumerate(sizes.items()):
            t.set([i], [0], _F0.render(int(c)))
            t.set([i], [1], _F1.render(100.0 * c / total))
        t.set([len(sizes)], [0], _F0.render(total))
        t.set([len(sizes)], [1], _F1.render(100.0))
        sc = float(silhouette_score(X, labels)) if len(set(labels)) > 1 else float("nan")
        return [{"type": "Title", "text": "TwoStep Cluster Analysis"},
                {"type": "Notes", "text": f"Number of clusters: {k}. Silhouette measure of cohesion: {sc:.3f}."},
                t.to_json()]


class NearestNeighbor(DataProcedure):
    """KNN target BY features [/K n] — k-nearest-neighbour classification."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        m = re.search(r"(.+?)\bBY\b(.+)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "KNN needs 'target BY features'."}]
        target = expand_varlist(m.group(1), allnames)[0]
        feats = expand_varlist(m.group(2), allnames)
        k = 3
        for name, b in subs:
            if name.upper() in ("K", "CRITERIA"):
                mm = re.search(r"\d+", b)
                if mm:
                    k = int(mm.group())
        data = _clean(ds, [target] + feats)
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.model_selection import cross_val_predict

        X = data[feats].to_numpy(float)
        X = (X - X.mean(0)) / (X.std(0) + 1e-9)
        y = data[target].to_numpy()
        knn = KNeighborsClassifier(n_neighbors=min(k, len(data) - 1))
        pred = cross_val_predict(knn, X, y, cv=min(5, len(np.unique(y))) or 2)
        acc = float((pred == y).mean())
        # Classification table.
        cats = sorted(np.unique(y))
        rows = [f"Observed {c}" for c in cats] + ["Overall %"]
        cols = [f"Predicted {c}" for c in cats] + ["Percent Correct"]
        t = PivotTable("Classification", [Dimension("", rows)], [Dimension("", cols)])
        for i, ct in enumerate(cats):
            row_mask = y == ct
            for j, cp in enumerate(cats):
                t.set([i], [j], _F0.render(int(((pred == cp) & row_mask).sum())))
            pc = 100.0 * ((pred == ct) & row_mask).sum() / max(row_mask.sum(), 1)
            t.set([i], [len(cats)], _F1.render(pc))
        t.set([len(cats)], [len(cats)], _F1.render(acc * 100))
        return [{"type": "Title", "text": "Nearest Neighbor Analysis"},
                {"type": "Notes", "text": f"k = {k}. Cross-validated accuracy: {acc:.3f}."},
                t.to_json()]

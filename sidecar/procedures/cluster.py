"""QUICK CLUSTER (K-Means) and CLUSTER (hierarchical) — HLD 6 Tier 2."""
from __future__ import annotations

import re
from typing import Any

import numpy as np

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure

_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)


def _matrix(ds, names):
    import pandas as pd

    cols = {nm: ds.df[nm].where(~missing_mask(ds.df[nm], ds.variables[ds._index_of(nm)]).to_numpy()) for nm in names}
    data = pd.DataFrame(cols).dropna()
    return data.to_numpy(float)


class QuickCluster(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        names_body = ""
        k = 2
        for n, b in subs:
            if n in ("", "VARIABLES"):
                names_body += " " + re.sub(r"^\s*CLUSTER\s+", " ", b, flags=re.IGNORECASE)
            elif n == "CRITERIA":
                mk = re.search(r"CLUSTERS?\s*\(?\s*(\d+)", b, re.IGNORECASE)
                if mk:
                    k = int(mk.group(1))
        names = expand_varlist(names_body, [v.name for v in ds.variables])
        if len(names) < 1:
            return [{"type": "Error", "text": "QUICK CLUSTER needs variables."}]
        X = _matrix(ds, names)
        from sklearn.cluster import KMeans

        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
        centers = km.cluster_centers_
        labels = km.labels_

        out: list[dict[str, Any]] = [{"type": "Title", "text": "Quick Cluster"}]
        cc = PivotTable("Final Cluster Centers", [Dimension("", list(names))],
                        [Dimension("Cluster", [str(i + 1) for i in range(k)])], corner="")
        for i in range(len(names)):
            for j in range(k):
                cc.set([i], [j], _F3.render(float(centers[j, i])))
        out.append(cc.to_json())

        nc = PivotTable("Number of Cases in each Cluster", [Dimension("Cluster", [str(i + 1) for i in range(k)] + ["Valid"])],
                        [Dimension("", ["N"])], corner="Cluster")
        for j in range(k):
            nc.set([j], [0], _F0.render(int((labels == j).sum())))
        nc.set([k], [0], _F0.render(len(labels)))
        out.append(nc.to_json())
        return out


class Cluster(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        names_body = ""
        method = "average"
        for n, b in subs:
            if n in ("", "VARIABLES"):
                names_body += " " + b
            elif n == "METHOD":
                up = b.upper()
                if "WARD" in up:
                    method = "ward"
                elif "SINGLE" in up:
                    method = "single"
                elif "COMPLETE" in up:
                    method = "complete"
        names = expand_varlist(names_body, [v.name for v in ds.variables])
        X = _matrix(ds, names)
        from scipy.cluster.hierarchy import linkage

        Z = linkage(X, method=method, metric="euclidean")
        n = X.shape[0]
        # Agglomeration schedule from the linkage matrix.
        rows = [str(s + 1) for s in range(len(Z))]
        t = PivotTable("Agglomeration Schedule", [Dimension("Stage", rows)],
                       [Dimension("", ["Cluster 1", "Cluster 2", "Coefficients"])], corner="Stage")

        def orig(idx):  # map linkage node id to a stage/case label
            return int(idx) + 1 if idx < n else int(idx) - n + 1

        for s in range(len(Z)):
            t.set([s], [0], _F0.render(orig(Z[s, 0])))
            t.set([s], [1], _F0.render(orig(Z[s, 1])))
            t.set([s], [2], _F3.render(float(Z[s, 2])))
        return [{"type": "Title", "text": "Cluster"}, t.to_json()]

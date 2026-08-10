"""Complex Samples: design-based descriptives (CSDESCRIPTIVES) and tabulation
(CSTABULATE). Taylor-linearised estimates for a single-stage design with weights
and optional strata/cluster — hand-rolled (no extra dependency)."""
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


def _design(subs, allnames):
    weight = cluster = None
    strata: list[str] = []
    for name, b in subs:
        u = name.upper()
        if u == "WEIGHT":
            weight = expand_varlist(b, allnames)[0]
        elif u == "STRATA":
            strata = expand_varlist(b, allnames)
        elif u == "CLUSTER":
            got = expand_varlist(b, allnames)
            cluster = got[0] if got else None
    return weight, strata, cluster


def _lin_mean(y, w, strata_ids, cluster_ids):
    """Weighted mean and Taylor-linearised SE (with-replacement clusters)."""
    W = w.sum()
    mean = float((w * y).sum() / W)
    resid = w * (y - mean)
    # Group residuals by (stratum, cluster). Without a design, each case is its
    # own PSU (conservative).
    keys = list(zip(strata_ids, cluster_ids))
    df = pd.DataFrame({"k_s": strata_ids, "k_c": cluster_ids, "e": resid})
    var = 0.0
    for s, grp in df.groupby("k_s"):
        clusters = grp.groupby("k_c")["e"].sum().to_numpy()
        m = len(clusters)
        if m > 1:
            var += m / (m - 1) * ((clusters - clusters.mean()) ** 2).sum()
        else:
            var += (clusters ** 2).sum()
    se = float(np.sqrt(var) / W)
    return mean, se


class CsDescriptives(DataProcedure):
    """CSDESCRIPTIVES /SUMMARY VARIABLES=vars /WEIGHT=w [/STRATA=s /CLUSTER=c]."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        allnames = [v.name for v in ds.variables]
        vars_: list[str] = []
        for name, b in subs:
            if name.upper() in ("SUMMARY", "VARIABLES", ""):
                mv = re.search(r"VARIABLES?\s*=?\s*(.+)", b, re.IGNORECASE)
                got = expand_varlist(mv.group(1) if mv else b, allnames)
                vars_ += [g for g in got if g in allnames]
        weight, strata, cluster = _design(subs, allnames)
        vars_ = [v for v in dict.fromkeys(vars_) if v not in (weight, cluster, *strata)]
        if not vars_ or weight is None:
            return [{"type": "Error", "text": "CSDESCRIPTIVES needs VARIABLES and /WEIGHT."}]
        need = vars_ + [weight] + strata + ([cluster] if cluster else [])
        data = _clean(ds, need)
        w = data[weight].to_numpy(float)
        strata_ids = data[strata[0]].to_numpy() if strata else np.ones(len(data))
        cluster_ids = data[cluster].to_numpy() if cluster else np.arange(len(data))

        t = PivotTable("Descriptive Statistics", [Dimension("", list(vars_))],
                       [Dimension("", ["Estimate (Mean)", "Std. Error", "95% CI Lower", "95% CI Upper"])])
        for i, v in enumerate(vars_):
            mean, se = _lin_mean(data[v].to_numpy(float), w, strata_ids, cluster_ids)
            t.set([i], [0], _F3.render(mean))
            t.set([i], [1], _F3.render(se))
            t.set([i], [2], _F3.render(mean - 1.96 * se))
            t.set([i], [3], _F3.render(mean + 1.96 * se))
        return [{"type": "Title", "text": "Complex Samples Descriptives"}, t.to_json()]


class CsTabulate(DataProcedure):
    """CSTABULATE /TABLES VARIABLES=row BY col /WEIGHT=w — weighted crosstab."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        allnames = [v.name for v in ds.variables]
        row = col = None
        for name, b in subs:
            if name.upper() in ("TABLES", "VARIABLES", ""):
                mv = re.search(r"VARIABLES?\s*=?\s*(.+)", b, re.IGNORECASE)
                spec = mv.group(1) if mv else b
                mm = re.search(r"(\w+)\s+BY\s+(\w+)", spec, re.IGNORECASE)
                if mm:
                    row, col = mm.group(1), mm.group(2)
        weight, _, _ = _design(subs, allnames)
        if row is None or col is None or weight is None:
            return [{"type": "Error", "text": "CSTABULATE needs 'VARIABLES=row BY col' and /WEIGHT."}]
        data = _clean(ds, [row, col, weight])
        pivot = data.pivot_table(index=row, columns=col, values=weight, aggfunc="sum", fill_value=0.0)
        rlabels = [str(x) for x in pivot.index]
        clabels = [str(x) for x in pivot.columns]
        t = PivotTable("Weighted Counts", [Dimension(row, rlabels)], [Dimension(col, clabels)])
        for i in range(len(rlabels)):
            for j in range(len(clabels)):
                t.set([i], [j], _F3.render(float(pivot.iloc[i, j])))
        return [{"type": "Title", "text": "Complex Samples Crosstabs"}, t.to_json()]

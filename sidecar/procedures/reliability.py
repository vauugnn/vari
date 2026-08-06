"""RELIABILITY — Cronbach's alpha + item-total statistics (HLD 6)."""
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


def cronbach_alpha(matrix: np.ndarray) -> float:
    k = matrix.shape[1]
    item_var = matrix.var(axis=0, ddof=1)
    total_var = matrix.sum(axis=1).var(ddof=1)
    if k < 2 or total_var == 0:
        return float("nan")
    return float(k / (k - 1) * (1 - item_var.sum() / total_var))


class Reliability(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = ""
        want_total = False
        for name, b in subs:
            if name in ("", "VARIABLES"):
                body += " " + re.sub(r"^\s*VARIABLES\s*=?\s*", "", b, flags=re.IGNORECASE)
            elif name == "SUMMARY":
                if "TOTAL" in b.upper() or "ALL" in b.upper():
                    want_total = True
        names = expand_varlist(body, [v.name for v in ds.variables])
        if len(names) < 2:
            return [{"type": "Error", "text": "RELIABILITY requires at least two items."}]

        # Listwise deletion across all items.
        cols = {}
        for nm in names:
            s = ds.df[nm]
            cols[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
        df = pd.DataFrame(cols).dropna()
        m = df.to_numpy(dtype=float)
        k = len(names)
        alpha = cronbach_alpha(m)

        # Standardized alpha from the mean inter-item correlation.
        corr = np.corrcoef(m, rowvar=False)
        off = corr[~np.eye(k, dtype=bool)]
        rbar = off.mean()
        std_alpha = k * rbar / (1 + (k - 1) * rbar) if (1 + (k - 1) * rbar) != 0 else float("nan")

        out: list[dict[str, Any]] = [{"type": "Title", "text": "Reliability"}]
        rs = PivotTable("Reliability Statistics", [Dimension("", [""])],
                        [Dimension("", ["Cronbach's Alpha", "Cronbach's Alpha Based on Standardized Items", "N of Items"])])
        rs.set([0], [0], strip_leading_zero(_F3.render(alpha)))
        rs.set([0], [1], strip_leading_zero(_F3.render(std_alpha)))
        rs.set([0], [2], _F0.render(k))
        out.append(rs.to_json())

        if want_total:
            out.append(self._item_total(names, m))
        return out

    def _item_total(self, names: list[str], m: np.ndarray) -> dict[str, Any]:
        k = m.shape[1]
        scale_total = m.sum(axis=1)
        t = PivotTable(
            "Item-Total Statistics",
            [Dimension("", list(names))],
            [Dimension("", ["Scale Mean if Item Deleted", "Scale Variance if Item Deleted",
                            "Corrected Item-Total Correlation", "Cronbach's Alpha if Item Deleted"])],
        )
        for i, nm in enumerate(names):
            rest = np.delete(m, i, axis=1)
            rest_total = rest.sum(axis=1)
            t.set([i], [0], _F3.render(float(rest_total.mean())))
            t.set([i], [1], _F3.render(float(rest_total.var(ddof=1))))
            citc = float(np.corrcoef(m[:, i], rest_total)[0, 1])
            t.set([i], [2], strip_leading_zero(_F3.render(citc)))
            t.set([i], [3], strip_leading_zero(_F3.render(cronbach_alpha(rest))))
        return t.to_json()

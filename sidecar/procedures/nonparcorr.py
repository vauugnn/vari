"""NONPAR CORR — Spearman's rho and Kendall's tau-b (HLD 6/9)."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd
from scipy import stats as sps

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure
from .base import strip_leading_zero

_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)


class NonparCorr(DataProcedure):
    command = "NONPAR CORR"

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = ""
        methods: list[str] = []
        for name, b in subs:
            if name in ("", "VARIABLES"):
                b = re.sub(r"^\s*CORR\b\s*", "", b, flags=re.IGNORECASE)
                body += " " + re.sub(r"^\s*VARIABLES\s*=?\s*", "", b, flags=re.IGNORECASE)
            elif name == "PRINT":
                up = b.upper()
                if "SPEARMAN" in up or "BOTH" in up:
                    methods.append("SPEARMAN")
                if "KENDALL" in up or "BOTH" in up:
                    methods.append("KENDALL")
        if not methods:
            methods = ["SPEARMAN"]
        names = expand_varlist(body, [v.name for v in ds.variables])
        if len(names) < 2:
            return [{"type": "Error", "text": "NONPAR CORR requires at least two variables."}]

        cols = {}
        for nm in names:
            s = ds.df[nm]
            cols[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
        mdf = pd.DataFrame(cols)

        out: list[dict[str, Any]] = [{"type": "Title", "text": "Nonparametric Correlations"}]
        for method in methods:
            out.append(self._matrix(mdf, names, method))
        return out

    def _matrix(self, mdf, names, method):
        stat_label = "Kendall's tau_b" if method == "KENDALL" else "Spearman's rho"
        t = PivotTable("Correlations",
                       [Dimension(stat_label, list(names)), Dimension("", ["Correlation Coefficient", "Sig. (2-tailed)", "N"])],
                       [Dimension("", list(names))])
        for i, a in enumerate(names):
            for j, b in enumerate(names):
                pair = mdf[[a, b]].dropna()
                n = len(pair)
                if a == b:
                    r, p = 1.0, None
                elif n > 2:
                    if method == "KENDALL":
                        r, p = sps.kendalltau(pair[a], pair[b])
                    else:
                        r, p = sps.spearmanr(pair[a], pair[b])
                    r, p = float(r), float(p)
                else:
                    r, p = float("nan"), None
                t.set([i, 0], [j], strip_leading_zero(_F3.render(r)) if r == r else ".")
                t.set([i, 1], [j], "" if p is None else strip_leading_zero(_F3.render(p)))
                t.set([i, 2], [j], _F0.render(n))
        return t.to_json()

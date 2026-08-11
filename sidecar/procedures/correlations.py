"""CORRELATIONS (Pearson, pairwise deletion — SPSS defaults, HLD 6/9)."""
from __future__ import annotations

import math
import re
from typing import Any

import numpy as np
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


class Correlations(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        varbody = ""
        for name, body in subs:
            if name in ("", "VARIABLES"):
                varbody += " " + re.sub(r"^\s*VARIABLES\s*=?\s*", "", body, flags=re.IGNORECASE)
        names = expand_varlist(varbody, [v.name for v in ds.variables])
        if len(names) < 2:
            return [{"type": "Error", "text": "CORRELATIONS requires at least two variables."}]

        # NaN where missing, so pandas does pairwise deletion for us.
        cols = {}
        for nm in names:
            meta = ds.variables[ds._index_of(nm)]
            s = ds.df[nm]
            cols[nm] = s.where(~missing_mask(s, meta))
        mdf = pd.DataFrame(cols)

        stat_cats = ["Pearson Correlation", "Sig. (2-tailed)", "N"]
        t = PivotTable(
            "Correlations",
            row_dims=[Dimension("", list(names)), Dimension("", stat_cats)],
            col_dims=[Dimension("", list(names))],
        )
        any_01 = False
        any_05 = False
        for i, a in enumerate(names):
            for j, b in enumerate(names):
                pair = mdf[[a, b]].dropna()
                n = len(pair)
                if a == b:
                    r, p = 1.0, None
                elif n > 2 and pair[a].std() > 0 and pair[b].std() > 0:
                    r = float(pair[a].corr(pair[b]))
                    tval = r * math.sqrt((n - 2) / max(1e-12, 1 - r * r))
                    p = float(2 * sps.t.sf(abs(tval), n - 2))
                else:
                    r, p = float("nan"), None
                # SPSS flags significant correlations with * (.05) and ** (.01).
                star = ""
                if p is not None and a != b:
                    if p < 0.01:
                        star, any_01 = "**", True
                    elif p < 0.05:
                        star, any_05 = "*", True
                cell = (strip_leading_zero(_F3.render(r)) + star) if r == r else "."
                t.set([i, 0], [j], cell, "num")
                t.set([i, 1], [j], "" if p is None else strip_leading_zero(_F3.render(p)), "num")
                t.set([i, 2], [j], _F0.render(n), "num")
        notes = []
        if any_01:
            notes.append("**. Correlation is significant at the 0.01 level (2-tailed).")
        if any_05:
            notes.append("*. Correlation is significant at the 0.05 level (2-tailed).")
        t.footnotes = notes
        return [t.to_json()]

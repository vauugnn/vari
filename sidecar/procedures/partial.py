"""PARTIAL CORR — partial correlations controlling for covariates (HLD 6)."""
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


class PartialCorr(DataProcedure):
    command = "PARTIAL CORR"

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = ""
        for name, b in subs:
            if name in ("", "VARIABLES"):
                b = re.sub(r"^\s*CORR\b\s*", "", b, flags=re.IGNORECASE)
                body += " " + re.sub(r"^\s*VARIABLES\s*=?\s*", "", b, flags=re.IGNORECASE)
        m = re.search(r"(.+?)\bBY\b(.+)", body, re.IGNORECASE)
        allnames = [v.name for v in ds.variables]
        if not m:
            return [{"type": "Error", "text": "PARTIAL CORR needs 'vars BY controls'."}]
        main = expand_varlist(m.group(1), allnames)
        controls = expand_varlist(m.group(2), allnames)
        if len(main) < 2:
            return [{"type": "Error", "text": "PARTIAL CORR needs at least two variables."}]

        cols = {}
        for nm in main + controls:
            s = ds.df[nm]
            cols[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
        data = pd.DataFrame(cols).dropna()

        stat_cats = ["Correlation", "Significance (2-tailed)", "df"]
        t = PivotTable(
            "Correlations",
            [Dimension("Control Variables: " + ", ".join(controls), list(main)), Dimension("", stat_cats)],
            [Dimension("", list(main))],
        )
        n = len(data)
        for i, a in enumerate(main):
            for j, b in enumerate(main):
                if a == b:
                    t.set([i, 0], [j], "1.000")
                    t.set([i, 1], [j], "")
                    t.set([i, 2], [j], _F0.render(0))
                    continue
                r = _partial_r(data, a, b, controls)
                df = n - 2 - len(controls)
                tval = r * math.sqrt(df / max(1e-12, 1 - r * r)) if df > 0 else float("nan")
                p = float(2 * sps.t.sf(abs(tval), df)) if df > 0 else float("nan")
                t.set([i, 0], [j], strip_leading_zero(_F3.render(r)))
                t.set([i, 1], [j], strip_leading_zero(_F3.render(p)))
                t.set([i, 2], [j], _F0.render(df))
        return [{"type": "Title", "text": "Partial Corr"}, t.to_json()]


def _partial_r(data: pd.DataFrame, a: str, b: str, controls: list[str]) -> float:
    """Partial correlation of a,b given controls = correlation of their residuals
    after regressing each on the controls (with intercept)."""
    C = np.column_stack([np.ones(len(data))] + [data[c].to_numpy(float) for c in controls])
    ya, yb = data[a].to_numpy(float), data[b].to_numpy(float)
    ra = ya - C @ np.linalg.lstsq(C, ya, rcond=None)[0]
    rb = yb - C @ np.linalg.lstsq(C, yb, rcond=None)[0]
    if ra.std() == 0 or rb.std() == 0:
        return float("nan")
    return float(np.corrcoef(ra, rb)[0, 1])

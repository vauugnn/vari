"""DESCRIPTIVES (HLD 6 Tier 1). Matches the SPSS Descriptive Statistics table:
columns N, Minimum, Maximum, Mean, Std. Deviation by default, plus a
Valid N (listwise) row.
"""
from __future__ import annotations

import re
from typing import Any

import numpy as np

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure
from . import stats
from .base import numeric_valid

_STAT_COLS = {
    "MEAN": ("Mean", stats.mean),
    "STDDEV": ("Std. Deviation", stats.std),
    "MINIMUM": ("Minimum", stats.minimum),
    "MAXIMUM": ("Maximum", stats.maximum),
    "VARIANCE": ("Variance", stats.variance),
    "RANGE": ("Range", stats.value_range),
    "SUM": ("Sum", stats.total),
    "SEMEAN": ("Std. Error Mean", stats.sem),
    "SKEWNESS": ("Skewness", stats.skewness),
    "KURTOSIS": ("Kurtosis", stats.kurtosis),
}
_DEFAULT = ["MINIMUM", "MAXIMUM", "MEAN", "STDDEV"]


class Descriptives(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        varbody = ""
        stat_keys: list[str] = []
        for name, body in subs:
            if name in ("", "VARIABLES"):
                varbody += " " + re.sub(r"^\s*VARIABLES\s*=?\s*", "", body, flags=re.IGNORECASE)
            elif name == "STATISTICS":
                for kw in body.upper().split():
                    if kw in ("DEFAULT",):
                        stat_keys += _DEFAULT
                    elif kw == "ALL":
                        stat_keys = list(_STAT_COLS)
                    elif kw in _STAT_COLS:
                        stat_keys.append(kw)
        names = expand_varlist(varbody, [v.name for v in ds.variables])
        if not names:
            return [{"type": "Error", "text": "DESCRIPTIVES requires a variable list."}]
        keys = stat_keys or _DEFAULT
        # SPSS column order: N, Minimum, Maximum, Mean, Std. Deviation, then others.
        ordered = [k for k in ["MINIMUM", "MAXIMUM", "MEAN", "STDDEV"] if k in keys]
        ordered += [k for k in keys if k not in ordered]

        col_labels = ["N"] + [_STAT_COLS[k][0] for k in ordered]
        row_labels = list(names) + ["Valid N (listwise)"]

        t = PivotTable("Descriptive Statistics", [Dimension("", row_labels)], [Dimension("", col_labels)])
        f0 = Format("F", 8, 0)
        for i, nm in enumerate(names):
            x = numeric_valid(ds, nm)
            t.set([i], [0], f0.render(stats.n_valid(x)), "num")
            for j, k in enumerate(ordered, start=1):
                fn = _STAT_COLS[k][1]
                val = fn(x)
                fmt = Format("F", 8, _decimals_for(ds, nm, k))
                t.set([i], [j], fmt.render(val) if val is not None else ".", "num")

        # Valid N (listwise): rows with no missing across all selected variables.
        listwise = np.zeros(ds.n_rows, dtype=bool)
        for nm in names:
            idx = ds._index_of(nm)
            listwise |= missing_mask(ds.df[nm], ds.variables[idx]).to_numpy()
        t.set([len(names)], [0], f0.render(int((~listwise).sum())), "num")
        for j in range(1, len(col_labels)):
            t.set([len(names)], [j], "", "text")
        return [t.to_json()]


def _decimals_for(ds: Any, name: str, key: str) -> int:
    dec = ds.variables[ds._index_of(name)].decimals
    if key in ("MINIMUM", "MAXIMUM", "SUM", "RANGE"):
        return dec
    return max(dec, 2)

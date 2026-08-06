"""GRAPH — legacy chart command (histogram, bar, pie, scatter, boxplot)."""
from __future__ import annotations

import re
from typing import Any

from ..data.missing import missing_mask
from ..output import charts as ch
from ..procedures import stats
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure
from .base import value_label
from .frequencies import _counts


class Graph(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = [{"type": "Title", "text": "Graph"}]
        allnames = [v.name for v in ds.variables]
        did = False
        for name, body in subs:
            key = name.upper().split("(")[0]
            body = re.sub(r"^\([^)]*\)\s*=?\s*", "", body)  # drop (SIMPLE)/(BIVAR)
            body = re.sub(r"^=\s*", "", body)
            if key == "HISTOGRAM":
                var = expand_varlist(body, allnames)[0]
                x = stats.valid_values(_num(ds, var))
                title = _label(ds, var)
                out.append(ch.histogram(x, title=f"Histogram: {title}", xlabel=title,
                                        mean=stats.mean(x), sd=stats.std(x), n=stats.n_valid(x)))
                did = True
            elif key in ("BAR", "PIE"):
                mby = re.search(r"\bBY\b\s*(\w+)", body, re.IGNORECASE)
                var = mby.group(1) if mby else expand_varlist(body, allnames)[0]
                var = expand_varlist(var, allnames)[0]
                labels, counts = _value_counts(ds, var)
                title = _label(ds, var)
                out.append(ch.bar_chart(labels, counts, title=f"Bar Chart: {title}", xlabel=title)
                           if key == "BAR" else ch.pie_chart(labels, counts, title=title))
                did = True
            elif key == "SCATTERPLOT":
                m = re.search(r"(\w+)\s+WITH\s+(\w+)", body, re.IGNORECASE)
                if m:
                    x, y = m.group(1), m.group(2)
                    xv, yv = _pair(ds, x, y)
                    out.append(ch.scatter(xv, yv, title=f"{_label(ds, y)} by {_label(ds, x)}",
                                          xlabel=_label(ds, x), ylabel=_label(ds, y)))
                    did = True
        if not did:
            return [{"type": "Error", "text": "GRAPH: use /HISTOGRAM, /BAR, /PIE, or /SCATTERPLOT."}]
        return out


def _num(ds, var):
    return ds.df[var].to_numpy(dtype=float)


def _label(ds, var):
    m = ds.variables[ds._index_of(var)]
    return m.label or var


def _value_counts(ds, var):
    meta = ds.variables[ds._index_of(var)]
    series = ds.df[var]
    valid = series[~missing_mask(series, meta).to_numpy()]
    pairs = _counts(valid.dropna())
    return [value_label(ds, var, v) for v, _ in pairs], [c for _, c in pairs]


def _pair(ds, x, y):
    import numpy as np

    xm = missing_mask(ds.df[x], ds.variables[ds._index_of(x)]).to_numpy()
    ym = missing_mask(ds.df[y], ds.variables[ds._index_of(y)]).to_numpy()
    keep = ~(xm | ym)
    return ds.df[x].to_numpy(float)[keep], ds.df[y].to_numpy(float)[keep]

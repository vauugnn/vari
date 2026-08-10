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
            elif key in ("LINE", "AREA", "ERRORBAR"):
                mby = re.search(r"\bBY\b\s*(\w+)", body, re.IGNORECASE)
                depm = re.search(r"\bMEAN\s*\(\s*(\w+)\s*\)", body, re.IGNORECASE)
                if mby and depm:
                    dep, grp = depm.group(1), mby.group(1)
                    labels, means, errs = _group_means(ds, dep, grp)
                    title = f"{_label(ds, dep)} by {_label(ds, grp)}"
                    if key == "LINE":
                        out.append(ch.line(list(range(len(means))), means, title=title, xlabel=_label(ds, grp), ylabel=_label(ds, dep)))
                    elif key == "AREA":
                        out.append(ch.area(labels, means, title=title, xlabel=_label(ds, grp), ylabel=_label(ds, dep)))
                    else:
                        out.append(ch.error_bar(labels, means, errs, title=title, xlabel=_label(ds, grp), ylabel=_label(ds, dep)))
                    did = True
            elif key == "SCATTERPLOT":
                m = re.search(r"(\w+)\s+WITH\s+(\w+)", body, re.IGNORECASE)
                if m:
                    x, y = m.group(1), m.group(2)
                    xv, yv = _pair(ds, x, y)
                    out.append(ch.scatter(xv, yv, title=f"{_label(ds, y)} by {_label(ds, x)}",
                                          xlabel=_label(ds, x), ylabel=_label(ds, y)))
                    did = True
            elif key == "BOXPLOT":
                mby = re.search(r"(\w+)\s+BY\s+(\w+)", body, re.IGNORECASE)
                if mby:
                    dep, grp = mby.group(1), mby.group(2)
                    groups, labels = _groups(ds, dep, grp)
                    out.append(ch.boxplot(groups, labels, title=f"{_label(ds, dep)} by {_label(ds, grp)}",
                                          ylabel=_label(ds, dep)))
                else:
                    names = expand_varlist(body, allnames)
                    groups = [stats.valid_values(_num(ds, v)) for v in names]
                    out.append(ch.boxplot(groups, [_label(ds, v) for v in names], title="Boxplot"))
                did = True
            elif key in ("HILO", "HIGHLOW"):
                names = expand_varlist(body.split(" BY ")[0], allnames)
                if len(names) >= 2:
                    cat_m = re.search(r"\bBY\b\s*(\w+)", body, re.IGNORECASE)
                    cats = ([value_label(ds, cat_m.group(1), v) for v in _num(ds, cat_m.group(1))]
                            if cat_m else [str(i + 1) for i in range(ds.n_rows)])
                    highs = _num(ds, names[0]).tolist()
                    lows = _num(ds, names[1]).tolist()
                    closes = _num(ds, names[2]).tolist() if len(names) >= 3 else None
                    out.append(ch.high_low(cats, highs, lows, closes,
                                           title="High-Low", ylabel=_label(ds, names[0])))
                    did = True
            elif key == "PYRAMID":
                m = re.search(r"(\w+)\s+BY\s+(\w+)", body, re.IGNORECASE)
                if m:
                    cat, split = m.group(1), m.group(2)
                    labels, left, right, side_labels = _pyramid(ds, cat, split)
                    out.append(ch.population_pyramid(labels, left, right, side_labels,
                                                     title=f"{_label(ds, cat)} by {_label(ds, split)}",
                                                     xlabel=_label(ds, cat)))
                    did = True
            elif key in ("BAR3D", "3DBAR", "3-DBAR"):
                m = re.search(r"(\w+)\s+BY\s+(\w+)", body, re.IGNORECASE)
                if m:
                    row, col = m.group(1), m.group(2)
                    rl, cl, grid = _crosscount(ds, row, col)
                    out.append(ch.bar3d(rl, cl, grid, title=f"{_label(ds, row)} by {_label(ds, col)}",
                                        xlabel=_label(ds, row)))
                    did = True
        if not did:
            return [{"type": "Error", "text": "GRAPH: use /HISTOGRAM, /BAR, /PIE, /SCATTERPLOT, /BOXPLOT, /HILO, /PYRAMID, or /BAR3D."}]
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


def _group_means(ds, dep, grp):
    import math

    dmask = missing_mask(ds.df[dep], ds.variables[ds._index_of(dep)]).to_numpy()
    gmask = missing_mask(ds.df[grp], ds.variables[ds._index_of(grp)]).to_numpy()
    keep = ~(dmask | gmask)
    dv = ds.df[dep].to_numpy(float)[keep]
    gv = ds.df[grp].to_numpy(float)[keep]
    labels, means, errs = [], [], []
    for lv in sorted(set(gv)):
        vals = dv[gv == lv]
        labels.append(value_label(ds, grp, lv))
        means.append(float(vals.mean()))
        errs.append(float(vals.std(ddof=1) / math.sqrt(len(vals))) if len(vals) > 1 else 0.0)
    return labels, means, errs


def _pair(ds, x, y):
    xm = missing_mask(ds.df[x], ds.variables[ds._index_of(x)]).to_numpy()
    ym = missing_mask(ds.df[y], ds.variables[ds._index_of(y)]).to_numpy()
    keep = ~(xm | ym)
    return ds.df[x].to_numpy(float)[keep], ds.df[y].to_numpy(float)[keep]


def _groups(ds, dep, grp):
    """Split dep's valid values into one list per level of grp."""
    dmask = missing_mask(ds.df[dep], ds.variables[ds._index_of(dep)]).to_numpy()
    gmask = missing_mask(ds.df[grp], ds.variables[ds._index_of(grp)]).to_numpy()
    keep = ~(dmask | gmask)
    dv = ds.df[dep].to_numpy(float)[keep]
    gv = ds.df[grp].to_numpy(float)[keep]
    groups, labels = [], []
    for lv in sorted(set(gv)):
        groups.append(dv[gv == lv].tolist())
        labels.append(value_label(ds, grp, lv))
    return groups, labels


def _pyramid(ds, cat, split):
    """Counts of cat per category, split into two sides by the first two split levels."""
    cmask = missing_mask(ds.df[cat], ds.variables[ds._index_of(cat)]).to_numpy()
    smask = missing_mask(ds.df[split], ds.variables[ds._index_of(split)]).to_numpy()
    keep = ~(cmask | smask)
    cv = ds.df[cat].to_numpy(float)[keep]
    sv = ds.df[split].to_numpy(float)[keep]
    cat_levels = sorted(set(cv))
    split_levels = sorted(set(sv))[:2]
    labels = [value_label(ds, cat, c) for c in cat_levels]
    left = [int(((cv == c) & (sv == split_levels[0])).sum()) for c in cat_levels]
    right = [int(((cv == c) & (sv == split_levels[1])).sum()) if len(split_levels) > 1 else 0
             for c in cat_levels]
    side_labels = [value_label(ds, split, s) for s in split_levels]
    if len(side_labels) < 2:
        side_labels.append("")
    return labels, left, right, side_labels


def _crosscount(ds, row, col):
    """2-D count grid of row x col levels (for a 3-D bar)."""
    rmask = missing_mask(ds.df[row], ds.variables[ds._index_of(row)]).to_numpy()
    cmask = missing_mask(ds.df[col], ds.variables[ds._index_of(col)]).to_numpy()
    keep = ~(rmask | cmask)
    rv = ds.df[row].to_numpy(float)[keep]
    cv = ds.df[col].to_numpy(float)[keep]
    rl = sorted(set(rv))
    cl = sorted(set(cv))
    grid = [[int(((rv == r) & (cv == c)).sum()) for c in cl] for r in rl]
    return [value_label(ds, row, r) for r in rl], [value_label(ds, col, c) for c in cl], grid

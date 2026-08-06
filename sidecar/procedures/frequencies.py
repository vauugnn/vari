"""FREQUENCIES (HLD 6 Tier 1). Produces a Statistics table (one column per
variable) and, per variable, a frequency table with Frequency / Percent /
Valid Percent / Cumulative Percent.
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
from .base import numeric_valid, value_label

_STAT_ROWS = {
    "MEAN": ("Mean", stats.mean, 3),
    "SEMEAN": ("Std. Error of Mean", stats.sem, 4),
    "MEDIAN": ("Median", stats.median, 2),
    "MODE": ("Mode", stats.mode, 0),
    "STDDEV": ("Std. Deviation", stats.std, 3),
    "VARIANCE": ("Variance", stats.variance, 3),
    "SKEWNESS": ("Skewness", stats.skewness, 3),
    "SESKEW": ("Std. Error of Skewness", stats.se_skewness, 3),
    "KURTOSIS": ("Kurtosis", stats.kurtosis, 3),
    "SEKURT": ("Std. Error of Kurtosis", stats.se_kurtosis, 3),
    "RANGE": ("Range", stats.value_range, 0),
    "MINIMUM": ("Minimum", stats.minimum, 0),
    "MAXIMUM": ("Maximum", stats.maximum, 0),
    "SUM": ("Sum", stats.total, 0),
}
_ALL = ["MEAN", "SEMEAN", "MEDIAN", "MODE", "STDDEV", "VARIANCE", "SKEWNESS", "SESKEW",
        "KURTOSIS", "SEKURT", "RANGE", "MINIMUM", "MAXIMUM", "SUM"]


class Frequencies(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        varbody = ""
        stat_keys: list[str] = []
        show_table = True
        charts: list[str] = []
        for name, body in subs:
            if name in ("", "VARIABLES"):
                varbody += " " + re.sub(r"^\s*VARIABLES\s*=?\s*", "", body, flags=re.IGNORECASE)
            elif name in ("HISTOGRAM", "BARCHART", "PIECHART"):
                charts.append(name)
            elif name == "STATISTICS":
                for kw in body.upper().split():
                    if kw == "ALL":
                        stat_keys = list(_ALL)
                    elif kw == "DEFAULT":
                        stat_keys += ["MEAN", "STDDEV", "MINIMUM", "MAXIMUM"]
                    elif kw in _STAT_ROWS:
                        stat_keys.append(kw)
            elif name == "FORMAT":
                if "NOTABLE" in body.upper():
                    show_table = False

        names = expand_varlist(varbody, [v.name for v in ds.variables])
        if not names:
            return [{"type": "Error", "text": "FREQUENCIES requires a variable list."}]

        out: list[dict[str, Any]] = [{"type": "Title", "text": "Frequencies"}]
        out.append(self._statistics_table(ds, names, stat_keys))
        if show_table:
            for nm in names:
                out.append(self._frequency_table(ds, nm))
        for nm in names:
            for ch in charts:
                out.append(self._chart(ds, nm, ch))
        return out

    def _chart(self, ds: Any, name: str, kind: str) -> dict[str, Any]:
        from ..output import charts as ch

        meta = ds.variables[ds._index_of(name)]
        title = meta.label or name
        if kind == "HISTOGRAM":
            x = numeric_valid(ds, name)
            return ch.histogram(x, title=f"Histogram: {title}", xlabel=title,
                                mean=stats.mean(x), sd=stats.std(x), n=stats.n_valid(x))
        # bar / pie use valid value counts with labels
        series = ds.df[name]
        valid = series[~missing_mask(series, meta).to_numpy()]
        pairs = _counts(valid.dropna())
        labels = [value_label(ds, name, v) for v, _ in pairs]
        counts = [c for _, c in pairs]
        if kind == "BARCHART":
            return ch.bar_chart(labels, counts, title=f"Bar Chart: {title}", xlabel=title)
        return ch.pie_chart(labels, counts, title=title)

    def _statistics_table(self, ds: Any, names: list[str], stat_keys: list[str]) -> dict[str, Any]:
        rows = ["Valid", "Missing"] + [_STAT_ROWS[k][0] for k in stat_keys]
        t = PivotTable("Statistics", [Dimension("N", rows)], [Dimension("", list(names))], corner="")
        f0 = Format("F", 8, 0)
        for j, nm in enumerate(names):
            series = ds.df[nm]
            meta = ds.variables[ds._index_of(nm)]
            miss = missing_mask(series, meta).to_numpy()
            t.set([0], [j], f0.render(int((~miss).sum())), "num")
            t.set([1], [j], f0.render(int(miss.sum())), "num")
            x = numeric_valid(ds, nm)
            for i, k in enumerate(stat_keys, start=2):
                _, fn, dec = _STAT_ROWS[k]
                val = fn(x)
                t.set([i], [j], Format("F", 8, dec).render(val) if val is not None else ".", "num")
        return t.to_json()

    def _frequency_table(self, ds: Any, name: str) -> dict[str, Any]:
        meta = ds.variables[ds._index_of(name)]
        series = ds.df[name]
        miss_mask = missing_mask(series, meta).to_numpy()
        total_n = len(series)
        valid_series = series[~miss_mask]
        valid_n = len(valid_series)

        # counts for valid values (sorted), then missing values (sorted)
        valid_counts = _counts(valid_series)
        missing_series = series[miss_mask]
        missing_counts = _counts(missing_series.dropna())
        sysmis_n = int(series.isna().sum())

        row_labels: list[str] = []
        rows_data: list[tuple[Any, Any, Any, Any]] = []
        cum = 0.0
        for val, cnt in valid_counts:
            pct = 100.0 * cnt / total_n if total_n else 0.0
            vpct = 100.0 * cnt / valid_n if valid_n else 0.0
            cum += vpct
            row_labels.append(value_label(ds, name, val))
            rows_data.append((cnt, pct, vpct, cum))
        # Valid subtotal
        row_labels.append("Total")
        rows_data.append((valid_n, 100.0 * valid_n / total_n if total_n else 0.0, 100.0, None))
        # Missing user values
        for val, cnt in missing_counts:
            pct = 100.0 * cnt / total_n if total_n else 0.0
            row_labels.append(value_label(ds, name, val))
            rows_data.append((cnt, pct, None, None))
        if sysmis_n:
            row_labels.append("System")
            rows_data.append((sysmis_n, 100.0 * sysmis_n / total_n if total_n else 0.0, None, None))
        # Grand total
        row_labels.append("Total")
        rows_data.append((total_n, 100.0, None, None))

        cols = ["Frequency", "Percent", "Valid Percent", "Cumulative Percent"]
        title = meta.label or name
        t = PivotTable(title, [Dimension("", row_labels)], [Dimension("", cols)])
        f0 = Format("F", 8, 0)
        f1 = Format("F", 8, 1)
        for i, (freq, pct, vpct, cumv) in enumerate(rows_data):
            t.set([i], [0], f0.render(freq), "num")
            t.set([i], [1], f1.render(pct), "num")
            t.set([i], [2], f1.render(vpct) if vpct is not None else "", "num")
            t.set([i], [3], f1.render(cumv) if cumv is not None else "", "num")
        return t.to_json()


def _counts(series: Any) -> list[tuple[Any, int]]:
    vc = series.value_counts(dropna=True)
    pairs = [(k, int(v)) for k, v in vc.items()]
    pairs.sort(key=lambda kv: _sortkey(kv[0]))
    return pairs


def _sortkey(v: Any) -> Any:
    try:
        return (0, float(v))
    except (TypeError, ValueError):
        return (1, str(v))

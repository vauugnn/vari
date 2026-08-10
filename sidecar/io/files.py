"""File I/O (HLD 11, PHASE-1 section 5).

pyreadstat for .sav/.por/.dta with full metadata. pandas/openpyxl for
.csv/.xlsx. The .sav path is the one that must round-trip metadata — variable
labels, value labels, missing definitions, formats, measure levels — and must
keep user-missing values as real values (read with user_missing=True).
"""
from __future__ import annotations

import os
from typing import Any

import numpy as np
import pandas as pd

from ..data.dataset import Dataset
from ..data.format import Format
from ..data.missing import MissingSpec
from ..data.variable import VariableMeta

_MEASURE_MAP = {"nominal": "nominal", "ordinal": "ordinal", "scale": "scale"}
_ALIGN_MAP = {"left": "left", "right": "right", "center": "center"}


def open_file(path: str, name: str = "DataSet1") -> Dataset:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".sav":
        return _open_sav(path, name)
    if ext == ".por":
        return _open_por(path, name)
    if ext == ".dta":
        return _open_dta(path, name)
    if ext in (".xlsx", ".xls"):
        return _open_excel(path, name)
    if ext in (".csv", ".txt", ".tsv"):
        return _open_csv(path, name)
    raise ValueError(f"Unsupported file type: {ext}")


def save_file(ds: Dataset, path: str) -> None:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".sav":
        _save_sav(ds, path)
    elif ext == ".csv":
        ds.df.to_csv(path, index=False)
    elif ext in (".xlsx",):
        ds.df.to_excel(path, index=False)
    else:
        raise ValueError(f"Unsupported save type: {ext}")


# ---- .sav ------------------------------------------------------------
def _open_sav(path: str, name: str) -> Dataset:
    import pyreadstat

    df, meta = pyreadstat.read_sav(path, user_missing=True, dates_as_pandas_datetime=True)
    variables = _variables_from_meta(df, meta)
    return Dataset(df, variables, name=name, source_path=path)


def _open_por(path: str, name: str) -> Dataset:
    import pyreadstat

    df, meta = pyreadstat.read_por(path, user_missing=True)
    return Dataset(df, _variables_from_meta(df, meta), name=name, source_path=path)


def _open_dta(path: str, name: str) -> Dataset:
    import pyreadstat

    df, meta = pyreadstat.read_dta(path)
    return Dataset(df, _variables_from_meta(df, meta), name=name, source_path=path)


def _variables_from_meta(df: pd.DataFrame, meta: Any) -> list[VariableMeta]:
    names = list(meta.column_names)
    labels = dict(zip(names, meta.column_labels or [None] * len(names)))
    value_labels = getattr(meta, "variable_value_labels", {}) or {}
    fmts = getattr(meta, "original_variable_types", {}) or {}
    measures = getattr(meta, "variable_measure", {}) or {}
    aligns = getattr(meta, "variable_alignment", {}) or {}
    disp = getattr(meta, "variable_display_width", {}) or {}
    ranges = getattr(meta, "missing_ranges", {}) or {}
    user_vals = getattr(meta, "missing_user_values", {}) or {}
    readstat_types = getattr(meta, "readstat_variable_types", {}) or {}

    out: list[VariableMeta] = []
    for nm in names:
        is_string = readstat_types.get(nm) == "string"
        fmt = _parse_format(fmts.get(nm), is_string, df[nm])
        out.append(
            VariableMeta(
                name=nm,
                print_format=fmt,
                label=labels.get(nm) or "",
                value_labels=dict(value_labels.get(nm, {})),
                missing=_missing_from_meta(nm, ranges, user_vals),
                columns=int(disp.get(nm) or fmt.width),
                align=_ALIGN_MAP.get(str(aligns.get(nm)), "right" if not is_string else "left"),
                measure=_MEASURE_MAP.get(str(measures.get(nm)), "nominal" if is_string else "scale"),
                role="input",
            )
        )
    return out


def _parse_format(spss_fmt: Any, is_string: bool, series: pd.Series) -> Format:
    if spss_fmt:
        try:
            return Format.parse(str(spss_fmt))
        except ValueError:
            pass
    if is_string:
        width = int(series.astype(str).str.len().max() or 8)
        return Format("A", max(width, 1))
    return Format("F", 8, 2)


def _missing_from_meta(nm: str, ranges: dict, user_vals: dict) -> MissingSpec:
    rlist = ranges.get(nm) or []
    discretes: list[Any] = list(user_vals.get(nm) or [])
    real_range = None
    for r in rlist:
        lo, hi = r.get("lo"), r.get("hi")
        if lo == hi:
            discretes.append(lo)
        else:
            real_range = (lo, hi)
    if real_range is not None:
        disc = discretes[0] if discretes else None
        return MissingSpec.range(real_range[0], real_range[1], disc)
    if discretes:
        return MissingSpec.discrete(discretes[:3])
    return MissingSpec.none()


def _save_sav(ds: Dataset, path: str) -> None:
    import pyreadstat

    names = [v.name for v in ds.variables]
    column_labels = [v.label or None for v in ds.variables]
    variable_value_labels = {v.name: v.value_labels for v in ds.variables if v.value_labels}
    variable_format = {v.name: v.print_format.to_spss() for v in ds.variables}
    variable_measure = {v.name: v.measure for v in ds.variables}
    variable_display_width = {v.name: int(v.columns) for v in ds.variables}
    missing_ranges = {}
    for v in ds.variables:
        rng = _missing_to_ranges(v.missing)
        if rng:
            missing_ranges[v.name] = rng

    # Note: pyreadstat.write_sav has no variable_alignment parameter, so column
    # alignment does not survive a .sav write. It is read back on open.
    pyreadstat.write_sav(
        ds.df,
        path,
        column_labels=column_labels,
        variable_value_labels=variable_value_labels,
        variable_format=variable_format,
        variable_measure=variable_measure,
        variable_display_width=variable_display_width,
        missing_ranges=missing_ranges or None,
    )


def _missing_to_ranges(spec: MissingSpec) -> list[dict[str, Any]]:
    if spec.kind == "none":
        return []
    if spec.kind == "discrete":
        return [{"lo": val, "hi": val} for val in spec.values]
    out = [{"lo": spec.lo, "hi": spec.hi}]
    for val in spec.values:
        out.append({"lo": val, "hi": val})
    return out


# ---- csv / excel -----------------------------------------------------
def _open_csv(path: str, name: str) -> Dataset:
    df = pd.read_csv(path)
    return Dataset(df, _variables_from_dataframe(df), name=name, source_path=path)


def open_database(conn: str, query: str, name: str = "DataSet1") -> Dataset:
    """Read a SQL query into a dataset. `conn` is a SQLAlchemy URL
    (e.g. sqlite:///path.db, postgresql://user:pw@host/db) or a plain path to a
    SQLite file. Uses SQLAlchemy when available, else stdlib sqlite3."""
    import os

    df: pd.DataFrame
    if "://" not in conn and os.path.exists(conn):
        import sqlite3

        with sqlite3.connect(conn) as cx:
            df = pd.read_sql_query(query, cx)
    else:
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(conn)
            with engine.connect() as cx:
                df = pd.read_sql_query(text(query), cx)
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("SQLAlchemy is required for this connection type.") from exc
    return Dataset(df, _variables_from_dataframe(df), name=name, source_path=None)


def import_text(path: str, opts: dict, name: str = "DataSet1") -> Dataset:
    """Text/CSV import with user-chosen options (the Import wizard)."""
    sep = opts.get("delimiter") or ","
    sep = {"tab": "\t", "\\t": "\t", "space": r"\s+", "semicolon": ";", "comma": ",", "pipe": "|"}.get(sep, sep)
    header = 0 if opts.get("firstRowNames", True) else None
    decimal = opts.get("decimal", ".")
    df = pd.read_csv(path, sep=sep, header=header, decimal=decimal, engine="python")
    if header is None:
        df.columns = [f"V{i + 1}" for i in range(df.shape[1])]
    else:
        df.columns = [str(c) for c in df.columns]
    return Dataset(df, _variables_from_dataframe(df), name=name, source_path=path)


def _open_excel(path: str, name: str) -> Dataset:
    df = pd.read_excel(path)
    return Dataset(df, _variables_from_dataframe(df), name=name, source_path=path)


def _variables_from_dataframe(df: pd.DataFrame) -> list[VariableMeta]:
    out: list[VariableMeta] = []
    for col in df.columns:
        series = df[col]
        if series.dtype == object or pd.api.types.is_string_dtype(series):
            width = int(series.astype(str).str.len().max() or 8)
            fmt = Format("A", max(width, 1))
            measure, align = "nominal", "left"
        else:
            fmt = Format("F", 8, 2)
            measure, align = "scale", "right"
        out.append(
            VariableMeta(name=str(col), print_format=fmt, measure=measure, align=align)
        )
    return out

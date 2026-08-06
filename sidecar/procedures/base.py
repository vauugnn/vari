"""Helpers shared by data procedures."""
from __future__ import annotations

from typing import Any

import numpy as np

from ..data.missing import missing_mask


def var_index(ds: Any, name: str) -> int:
    return ds._index_of(name)


def numeric_valid(ds: Any, name: str, include_user_missing: bool = False) -> np.ndarray:
    """Values with system- and (by default) user-missing removed, as float."""
    idx = ds._index_of(name)
    meta = ds.variables[idx]
    series = ds.df[name]
    mask = missing_mask(series, meta, include_user_missing=include_user_missing)
    kept = series[~mask]
    return np.asarray(kept, dtype="float64")


def value_label(ds: Any, name: str, value: Any) -> str:
    idx = ds._index_of(name)
    meta = ds.variables[idx]
    for k, lab in meta.value_labels.items():
        if _same_value(k, value):
            return str(lab)
    return meta.print_format.render(value) if not meta.is_string else str(value)


def _same_value(a: Any, b: Any) -> bool:
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return str(a) == str(b)

"""Descriptive statistics matching SPSS defaults (HLD 9).

Every function here uses SPSS's convention, not the library default:
  - std / variance use n-1 (ddof=1)
  - skewness is G1 with SES; kurtosis is G2 with SEK
  - percentiles use HAVERAGE (weighted average at (n+1)p)
Parity divergences are logged in docs/PARITY.md as they are found.
"""
from __future__ import annotations

import math
from typing import Optional

import numpy as np


def valid_values(arr: np.ndarray) -> np.ndarray:
    a = np.asarray(arr, dtype="float64")
    return a[~np.isnan(a)]


def n_valid(x: np.ndarray) -> int:
    return int(valid_values(x).size)


def mean(x: np.ndarray) -> Optional[float]:
    v = valid_values(x)
    return float(v.mean()) if v.size else None


def std(x: np.ndarray) -> Optional[float]:
    v = valid_values(x)
    return float(v.std(ddof=1)) if v.size > 1 else None


def variance(x: np.ndarray) -> Optional[float]:
    v = valid_values(x)
    return float(v.var(ddof=1)) if v.size > 1 else None


def sem(x: np.ndarray) -> Optional[float]:
    v = valid_values(x)
    if v.size < 2:
        return None
    return float(v.std(ddof=1) / math.sqrt(v.size))


def minimum(x: np.ndarray) -> Optional[float]:
    v = valid_values(x)
    return float(v.min()) if v.size else None


def maximum(x: np.ndarray) -> Optional[float]:
    v = valid_values(x)
    return float(v.max()) if v.size else None


def value_range(x: np.ndarray) -> Optional[float]:
    v = valid_values(x)
    return float(v.max() - v.min()) if v.size else None


def total(x: np.ndarray) -> Optional[float]:
    v = valid_values(x)
    return float(v.sum()) if v.size else None


def skewness(x: np.ndarray) -> Optional[float]:
    v = valid_values(x)
    n = v.size
    if n < 3:
        return None
    s = v.std(ddof=1)
    if s == 0:
        return None
    z = (v - v.mean()) / s
    return float(n / ((n - 1) * (n - 2)) * np.sum(z**3))


def se_skewness(x: np.ndarray) -> Optional[float]:
    n = n_valid(x)
    if n < 3:
        return None
    return float(math.sqrt(6 * n * (n - 1) / ((n - 2) * (n + 1) * (n + 3))))


def kurtosis(x: np.ndarray) -> Optional[float]:
    v = valid_values(x)
    n = v.size
    if n < 4:
        return None
    s = v.std(ddof=1)
    if s == 0:
        return None
    z = (v - v.mean()) / s
    a = n * (n + 1) / ((n - 1) * (n - 2) * (n - 3))
    b = 3 * (n - 1) ** 2 / ((n - 2) * (n - 3))
    return float(a * np.sum(z**4) - b)


def se_kurtosis(x: np.ndarray) -> Optional[float]:
    n = n_valid(x)
    if n < 4:
        return None
    ses = se_skewness(x)
    if ses is None:
        return None
    return float(2 * ses * math.sqrt((n * n - 1) / ((n - 3) * (n + 5))))


def percentile(x: np.ndarray, p: float) -> Optional[float]:
    """HAVERAGE: weighted average at rank (n+1)*p/100 (SPSS default)."""
    v = np.sort(valid_values(x))
    n = v.size
    if n == 0:
        return None
    rank = (p / 100.0) * (n + 1)
    if rank < 1:
        return float(v[0])
    if rank >= n:
        return float(v[-1])
    k = int(math.floor(rank))
    frac = rank - k
    return float(v[k - 1] + frac * (v[k] - v[k - 1]))


def median(x: np.ndarray) -> Optional[float]:
    return percentile(x, 50.0)


def mode(x: np.ndarray) -> Optional[float]:
    """Smallest most-frequent value (SPSS reports the smallest on ties)."""
    v = valid_values(x)
    if v.size == 0:
        return None
    vals, counts = np.unique(v, return_counts=True)
    top = counts.max()
    return float(vals[counts == top].min())


# ---- weighted variants (WEIGHT BY) ----
def _wvalid(x: np.ndarray, w: np.ndarray):
    x = np.asarray(x, dtype="float64")
    w = np.asarray(w, dtype="float64")
    keep = ~np.isnan(x) & ~np.isnan(w) & (w > 0)
    return x[keep], w[keep]


def w_n(x: np.ndarray, w: np.ndarray) -> float:
    _, ww = _wvalid(x, w)
    return float(ww.sum())


def w_mean(x: np.ndarray, w: np.ndarray) -> Optional[float]:
    xv, ww = _wvalid(x, w)
    return float((xv * ww).sum() / ww.sum()) if ww.sum() > 0 else None


def w_std(x: np.ndarray, w: np.ndarray) -> Optional[float]:
    xv, ww = _wvalid(x, w)
    sw = ww.sum()
    if sw <= 1:
        return None
    m = (xv * ww).sum() / sw
    var = (ww * (xv - m) ** 2).sum() / (sw - 1)
    return float(math.sqrt(var))

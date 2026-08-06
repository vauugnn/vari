"""User-missing value definitions and the missing mask (HLD 3.3).

The trap this module exists to avoid: SPSS user-missing values are REAL values
the user declared as missing (e.g. 99 = "declined"). They must stay in the
DataFrame, survive a round trip to .sav, display as their actual value, and be
includable via MISSING=INCLUDE. They are NOT NaN. System-missing ($SYSMIS) is
absence of a value and IS NaN.

`missing_mask` combines the two:

    m = series.isna()                       # system-missing
    if not include_user_missing:
        m |= meta.missing.matches(series)   # user-missing
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd


@dataclass
class MissingSpec:
    """One of: none; up to 3 discrete values; a range [lo, hi] + optional 1 discrete."""

    kind: str = "none"  # 'none' | 'discrete' | 'range'
    values: list[Any] = field(default_factory=list)
    lo: Optional[float] = None
    hi: Optional[float] = None

    # ---- constructors -------------------------------------------------
    @classmethod
    def none(cls) -> "MissingSpec":
        return cls("none")

    @classmethod
    def discrete(cls, values: list[Any]) -> "MissingSpec":
        if len(values) > 3:
            raise ValueError("At most 3 discrete missing values are allowed.")
        return cls("discrete", list(values))

    @classmethod
    def range(cls, lo: float, hi: float, discrete: Optional[Any] = None) -> "MissingSpec":
        vals = [discrete] if discrete is not None else []
        return cls("range", vals, lo, hi)

    # ---- behaviour ----------------------------------------------------
    def matches(self, series: pd.Series) -> pd.Series:
        """Boolean Series: True where a value is user-missing under this spec."""
        if self.kind == "none":
            return pd.Series(False, index=series.index)
        if self.kind == "discrete":
            return series.isin(self.values)
        # range (+ optional single discrete)
        lo = -math.inf if self.lo is None else self.lo
        hi = math.inf if self.hi is None else self.hi
        numeric = pd.to_numeric(series, errors="coerce")
        mask = (numeric >= lo) & (numeric <= hi)
        if self.values:
            mask = mask | series.isin(self.values)
        return mask.fillna(False)

    def copy(self) -> "MissingSpec":
        return MissingSpec(self.kind, list(self.values), self.lo, self.hi)

    def to_json(self) -> dict[str, Any]:
        return {"kind": self.kind, "values": list(self.values), "lo": self.lo, "hi": self.hi}

    @classmethod
    def from_json(cls, d: Optional[dict[str, Any]]) -> "MissingSpec":
        if not d or d.get("kind", "none") == "none":
            return cls.none()
        return cls(d["kind"], list(d.get("values", [])), d.get("lo"), d.get("hi"))


def missing_mask(series: pd.Series, meta: "Any", include_user_missing: bool = False) -> pd.Series:
    """Boolean Series marking values to be treated as missing for a procedure."""
    m = series.isna()
    if not include_user_missing:
        m = m | meta.missing.matches(series)
    return m

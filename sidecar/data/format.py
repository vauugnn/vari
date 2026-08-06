"""SPSS print/write formats (HLD 3.2).

A format is TYPE + width + optional decimals, e.g. F8.2, A10, DATE11,
DOLLAR12.2, PCT5.1, COMMA10.0, E10.3. Formats drive display in the grid, in
output tables, everywhere — so this is a first-class object, not a string.

SPSS-specific parity notes baked in here (HLD 9):
  - Rounding is half AWAY FROM ZERO, not Python's banker's rounding.
  - F format keeps its leading zero (0.50 -> "0.50"); leading-zero suppression
    is a property of specific output cells (p-values, correlations), not of the
    base F format, so it is NOT applied here.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

_FORMAT_RE = re.compile(r"^([A-Za-z]+)(\d+)(?:\.(\d+))?$")

# Numeric families that render with fixed decimals.
_NUMERIC_TYPES = {"F", "COMMA", "DOT", "DOLLAR", "PCT", "E", "N", "Z"}
# Date/time families (value is a python date/datetime/time or SPSS-seconds).
_DATE_TYPES = {"DATE", "ADATE", "EDATE", "SDATE", "JDATE", "DATETIME", "TIME", "DTIME"}
_STRING_TYPES = {"A", "AHEX"}

# SPSS three-letter uppercase month abbreviations.
_MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def _round_half_up(value: float, decimals: int) -> Decimal:
    """Quantize to `decimals` places, ties away from zero (SPSS rule)."""
    q = Decimal(1).scaleb(-decimals)
    return Decimal(repr(float(value))).quantize(q, rounding=ROUND_HALF_UP)


def _group(int_part: str, grp_sep: str) -> str:
    """Insert a thousands separator into a run of digits."""
    if not grp_sep:
        return int_part
    rev = int_part[::-1]
    chunks = [rev[i : i + 3] for i in range(0, len(rev), 3)]
    return grp_sep.join(chunks)[::-1]


@dataclass(frozen=True)
class Format:
    type: str
    width: int
    decimals: int = 0

    # ---- construction -------------------------------------------------
    @classmethod
    def parse(cls, s: str) -> "Format":
        m = _FORMAT_RE.match(s.strip())
        if not m:
            raise ValueError(f"Invalid format: {s!r}")
        typ = m.group(1).upper()
        width = int(m.group(2))
        decimals = int(m.group(3)) if m.group(3) is not None else 0
        return cls(typ, width, decimals)

    @classmethod
    def default_for(cls, dtype: Any, width: int = 8) -> "Format":
        """Default format for a coarse dtype ('numeric'/'string' or a numpy/pandas dtype)."""
        kind = _dtype_kind(dtype)
        if kind == "string":
            return cls("A", max(width, 1), 0)
        return cls("F", 8, 2)

    def to_spss(self) -> str:
        if self.type in _STRING_TYPES:
            return f"{self.type}{self.width}"
        if self.decimals:
            return f"{self.type}{self.width}.{self.decimals}"
        return f"{self.type}{self.width}"

    # ---- rendering ----------------------------------------------------
    def render(self, value: Any) -> str:
        """Value -> display string. System-missing (None/NaN) renders as '.'."""
        if value is None:
            return "."
        if isinstance(value, float) and value != value:  # NaN
            return "."
        if self.type in _STRING_TYPES:
            return str(value)
        if self.type in _DATE_TYPES:
            return self._render_date(value)
        return self._render_numeric(float(value))

    def _render_numeric(self, value: float) -> str:
        d = _round_half_up(value, self.decimals)
        sign = "-" if d < 0 else ""
        d = abs(d)
        body = f"{d:.{self.decimals}f}"

        if self.type in ("COMMA", "DOLLAR"):
            grp, dec = ",", "."
        elif self.type == "DOT":
            grp, dec = ".", ","
        else:  # F, PCT, E, N, Z
            grp, dec = "", "."

        if self.type == "E":
            return f"{value:.{self.decimals}E}"

        if "." in body:
            int_part, frac = body.split(".")
        else:
            int_part, frac = body, ""
        int_part = _group(int_part, grp)
        out = int_part + (dec + frac if frac else "")

        if self.type == "DOLLAR":
            out = "$" + out
        elif self.type == "PCT":
            out = out + "%"
        return sign + out

    def _render_date(self, value: Any) -> str:
        d = _coerce_date(value)
        if d is None:
            return "."
        if self.type in ("DATE", "SDATE", "ADATE", "EDATE"):
            return f"{d.day:02d}-{_MONTHS[d.month - 1]}-{d.year:04d}"
        if self.type == "JDATE":
            return f"{d.year:04d}{d.timetuple().tm_yday:03d}"
        if self.type in ("DATETIME",):
            return (
                f"{d.day:02d}-{_MONTHS[d.month - 1]}-{d.year:04d} "
                f"{d.hour:02d}:{d.minute:02d}:{d.second:02d}"
            )
        if self.type in ("TIME", "DTIME"):
            return f"{d.hour:02d}:{d.minute:02d}:{d.second:02d}"
        return f"{d.day:02d}-{_MONTHS[d.month - 1]}-{d.year:04d}"

    # ---- input parsing (display string -> value) ----------------------
    def parse_input(self, s: str) -> Any:
        s = s.strip()
        if s == "" or s == ".":
            return None
        if self.type in _STRING_TYPES:
            return s
        if self.type in _DATE_TYPES:
            return _parse_date_input(s)
        cleaned = s.strip()
        if self.type == "DOLLAR":
            cleaned = cleaned.replace("$", "")
        if self.type == "PCT":
            cleaned = cleaned.replace("%", "")
        if self.type == "DOT":
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
        return float(cleaned)


def _dtype_kind(dtype: Any) -> str:
    if isinstance(dtype, str):
        return "string" if dtype.lower().startswith(("str", "string", "object")) else "numeric"
    kind = getattr(dtype, "kind", None)
    if kind in ("O", "U", "S"):
        return "string"
    return "numeric"


def _coerce_date(value: Any):
    if isinstance(value, _dt.datetime):
        return value
    if isinstance(value, _dt.date):
        return _dt.datetime(value.year, value.month, value.day)
    return None


def _parse_date_input(s: str):
    # Accept "dd-MMM-yyyy" (SPSS) or ISO "yyyy-mm-dd".
    m = re.match(r"^(\d{1,2})-([A-Za-z]{3})-(\d{4})$", s)
    if m:
        day, mon, year = int(m.group(1)), m.group(2).upper(), int(m.group(3))
        if mon in _MONTHS:
            return _dt.datetime(year, _MONTHS.index(mon) + 1, day)
    try:
        return _dt.datetime.fromisoformat(s)
    except ValueError:
        return None

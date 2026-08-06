"""VariableMeta — the eleven Variable View attributes (HLD 3.1).

The Variable View "Type" column is derived from the print format, so we store
a single `Format` and expose type/width/decimals through it rather than
duplicating state that could drift.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Optional

from .format import Format
from .missing import MissingSpec

# Cannot be used as variable names (HLD 3.1).
RESERVED = {"ALL", "AND", "BY", "EQ", "GE", "GT", "LE", "LT", "NE", "NOT", "OR", "TO", "WITH"}

MEASURES = ("nominal", "ordinal", "scale")
ALIGNS = ("left", "right", "center")
ROLES = ("input", "target", "both", "none", "partition", "split")

# Map a Format type code to the Variable View "Type" label.
_TYPE_LABEL = {
    "F": "Numeric",
    "N": "Restricted Numeric",
    "COMMA": "Comma",
    "DOT": "Dot",
    "E": "Scientific notation",
    "DOLLAR": "Dollar",
    "PCT": "Numeric",
    "A": "String",
    "AHEX": "String",
    "DATE": "Date",
    "ADATE": "Date",
    "EDATE": "Date",
    "SDATE": "Date",
    "JDATE": "Date",
    "DATETIME": "Date",
    "TIME": "Date",
    "DTIME": "Date",
}


class NameError_(ValueError):
    """Raised when a variable name is invalid or a duplicate."""


def validate_name(name: str, existing: Optional[set[str]] = None) -> str:
    """Validate a variable name; return it unchanged or raise NameError_.

    Matching against reserved words and duplicates is case-insensitive; the
    original casing is preserved on return.
    """
    if not name:
        raise NameError_("Variable name may not be empty.")
    if len(name.encode("utf-8")) > 64:
        raise NameError_("Variable name exceeds 64 bytes.")
    if name[0].isdigit():
        raise NameError_(f"Variable name '{name}' may not begin with a digit.")
    if name[0] in "._":
        raise NameError_(f"Variable name '{name}' may not begin with '{name[0]}'.")
    if name.endswith("."):
        raise NameError_(f"Variable name '{name}' may not end with a period.")
    for ch in name:
        if not (ch.isalnum() or ch in "@#$._" or ord(ch) > 127):
            raise NameError_(f"Variable name '{name}' contains invalid character '{ch}'.")
    if name.upper() in RESERVED:
        raise NameError_(f"'{name}' is a reserved keyword and cannot be a variable name.")
    if existing is not None:
        lowered = name.lower()
        if lowered in {e.lower() for e in existing}:
            raise NameError_(f"There is already a variable named '{name}'.")
    return name


@dataclass
class VariableMeta:
    name: str
    print_format: Format = field(default_factory=lambda: Format("F", 8, 2))
    label: str = ""
    value_labels: dict[Any, str] = field(default_factory=dict)
    missing: MissingSpec = field(default_factory=MissingSpec.none)
    columns: int = 8
    align: str = "right"
    measure: str = "scale"
    role: str = "input"

    # ---- derived Variable View columns --------------------------------
    @property
    def is_string(self) -> bool:
        return self.print_format.type in ("A", "AHEX")

    @property
    def type_label(self) -> str:
        return _TYPE_LABEL.get(self.print_format.type, "Numeric")

    @property
    def width(self) -> int:
        return self.print_format.width

    @property
    def decimals(self) -> int:
        return self.print_format.decimals

    def copy(self) -> "VariableMeta":
        return replace(
            self,
            value_labels=dict(self.value_labels),
            missing=self.missing.copy(),
        )

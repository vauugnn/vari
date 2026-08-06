"""Output document model (HLD 4).

Output is a tree of typed objects, not HTML. Procedures build these; the
renderer renders them. Numeric cells are pre-rendered to display strings via
Format so SPSS numeric parity lives in the sidecar, not the UI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..data.format import Format


@dataclass
class Dimension:
    label: str
    categories: list[str]


@dataclass
class PivotTable:
    title: str
    row_dims: list[Dimension]
    col_dims: list[Dimension]
    # key: (row_index_tuple, col_index_tuple) -> (display_string, kind)
    cells: dict[tuple, tuple] = field(default_factory=dict)
    caption: Optional[str] = None
    corner: str = ""
    footnotes: list[str] = field(default_factory=list)
    # Ragged columns: when col_leaves is set, columns are a flat list of leaf
    # labels with optional spanner rows (top-to-bottom), instead of a strict
    # nested cross-product. This lets sibling groups have different widths
    # (SPSS "Levene's Test" | "t-test for Equality of Means" | "95% CI").
    col_leaves: Optional[list[str]] = None
    col_spanners: list[list[tuple[str, int]]] = field(default_factory=list)

    def set(self, rkey: list[int], ckey: list[int], value: str, kind: str = "num") -> None:
        self.cells[(tuple(rkey), tuple(ckey))] = (value, kind)

    def set_columns(self, leaves: list[str], spanners: Optional[list[list[tuple[str, int]]]] = None) -> None:
        self.col_leaves = leaves
        self.col_spanners = spanners or []

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "type": "PivotTable",
            "title": self.title,
            "caption": self.caption,
            "corner": self.corner,
            "rowDims": [{"label": d.label, "categories": d.categories} for d in self.row_dims],
            "colDims": [{"label": d.label, "categories": d.categories} for d in self.col_dims],
            "cells": [
                {"r": list(r), "c": list(c), "v": v, "kind": k}
                for (r, c), (v, k) in self.cells.items()
            ],
        }
        if self.footnotes:
            out["footnotes"] = self.footnotes
        if self.col_leaves is not None:
            out["colLeaves"] = self.col_leaves
            out["colSpanners"] = [[{"label": lbl, "span": sp} for lbl, sp in row] for row in self.col_spanners]
        return out


def title(text: str) -> dict[str, Any]:
    return {"type": "Title", "text": text}


def text_block(text: str) -> dict[str, Any]:
    return {"type": "TextBlock", "text": text}


def warning(text: str) -> dict[str, Any]:
    return {"type": "Warning", "text": text}


def notes(rows: list[tuple[str, str]]) -> dict[str, Any]:
    return {"type": "Notes", "rows": [{"label": a, "value": b} for a, b in rows]}


def simple_table(
    title_text: str,
    row_labels: list[str],
    col_labels: list[str],
    matrix: list[list[Any]],
    fmt: Format = Format("F", 8, 3),
    row_dim_label: str = "",
    col_dim_label: str = "",
    col_formats: Optional[list[Format]] = None,
) -> PivotTable:
    """One row dimension, one column dimension. matrix[i][j] may be a number
    (formatted), a string (shown verbatim), or None (system-missing '.')."""
    t = PivotTable(title_text, [Dimension(row_dim_label, row_labels)], [Dimension(col_dim_label, col_labels)])
    for i in range(len(row_labels)):
        for j in range(len(col_labels)):
            val = matrix[i][j]
            f = col_formats[j] if col_formats else fmt
            if isinstance(val, str):
                t.set([i], [j], val, "text")
            elif val is None:
                t.set([i], [j], ".", "num")
            else:
                t.set([i], [j], f.render(val), "num")
    return t

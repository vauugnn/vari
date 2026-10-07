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
    # Row groups for a single row dimension: (label, first row, row count). Rows in a
    # group get the group's label in an outer header column, as SPSS does ("Valid" over
    # the values and their Total); rows outside any group span both header columns.
    row_groups: list[tuple[str, int, int]] = field(default_factory=list)

    def set(self, rkey: list[int], ckey: list[int], value: str, kind: str = "num") -> None:
        self.cells[(tuple(rkey), tuple(ckey))] = (value, kind)

    def set_columns(self, leaves: list[str], spanners: Optional[list[list[tuple[str, int]]]] = None) -> None:
        self.col_leaves = leaves
        self.col_spanners = spanners or []

    def _flat_with_groups(self) -> Optional[dict[str, Any]]:
        """Header cells with spans for a single row dimension carrying row groups."""
        if self.col_leaves is not None:
            leaves = self.col_leaves
            col_headers = [[{"t": lbl, "cs": sp, "rs": 1} for lbl, sp in row] for row in self.col_spanners]
            col_headers.append([{"t": lab, "cs": 1, "rs": 1} for lab in leaves])
            ncols = len(leaves)
        elif len(self.col_dims) == 1:
            d = self.col_dims[0]
            ncols = len(d.categories)
            col_headers = []
            if d.label:
                col_headers.append([{"t": d.label, "cs": ncols, "rs": 1}])
            col_headers.append([{"t": c, "cs": 1, "rs": 1} for c in d.categories])
        else:
            return None
        labels = self.row_dims[0].categories
        group_of = {start: (name, n) for name, start, n in self.row_groups}
        inside = {i for _, start, n in self.row_groups for i in range(start, start + n)}
        row_headers: list[list[dict[str, Any]]] = []
        for i, lab in enumerate(labels):
            cells: list[dict[str, Any]] = []
            if i in group_of:
                name, n = group_of[i]
                cells.append({"t": name, "rs": n, "cs": 1})
            cells.append({"t": lab, "rs": 1, "cs": 1 if i in inside else 2})
            row_headers.append(cells)
        grid = [[self.cells.get(((i,), (j,)), ("", "text"))[0] for j in range(ncols)] for i in range(len(labels))]
        kinds = [[self.cells.get(((i,), (j,)), ("", "text"))[1] for j in range(ncols)] for i in range(len(labels))]
        return {"rowHeaderCols": 2, "colHeaders": col_headers, "rowHeaders": row_headers, "grid": grid, "kinds": kinds}

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
        if self.row_groups and len(self.row_dims) == 1:
            flat = self._flat_with_groups()
            if flat is not None:
                out["flat"] = flat
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

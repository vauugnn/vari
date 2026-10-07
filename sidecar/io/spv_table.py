"""Turn a parsed SPSS light table into Vari's flat pivot-table JSON.

SPSS tables nest categories in groups (e.g. "Valid" over the values, with
"Total" a sibling of "Valid"). The renderer's cross-product model cannot
express that, so we flatten to a grid plus explicit header cells with
rowspan/colspan:

    {"type": "PivotTable", "title": ..., "flat": {
        "corner": str,
        "colHeaders": [[{"t": str, "cs": int, "rs": int}, ...], ...],   # per header row
        "rowHeaders": [[{"t": str, "cs": int, "rs": int}, ...], ...],   # per body row
        "grid": [[str, ...], ...], "kinds": [[str, ...], ...]}}
"""
from __future__ import annotations

from typing import Any, Optional

from .spv_light import Category, Dimension, LightTable, Val


def _letter(i: int) -> str:
    return chr(97 + i % 26)


def _marker(v: Val, table: LightTable) -> str:
    """Footnote markers shown after a value's text (as in SPSS: a, b, c...)."""
    parts = [_letter(r) for r in v.refs if r < len(table.footnotes)] + list(v.subs)
    return ("" if not parts else " " + ",".join(parts))


# A path entry is (node-identity, label). Identity lets us merge only siblings
# that are the *same* group instance, not just groups with equal labels.
Path = list[tuple[int, str]]


def _leaf_paths(dim: Dimension, dim_pos: int, table: LightTable) -> list[tuple[Path, int]]:
    """All leaves of a dimension in display order: (label path, leaf_index)."""
    out: list[tuple[Path, int]] = []
    ident = [0]

    def walk(cats: list[Category], prefix: Path) -> None:
        for c in cats:
            ident[0] += 1
            nid = (dim_pos << 20) | ident[0]
            if c.leaf_index is not None:
                out.append((prefix + [(nid, c.name.text + _marker(c.name, table))], c.leaf_index))
            else:
                label = c.name.text + _marker(c.name, table)
                # Merged groups act as if their children were direct children.
                walk(c.children, prefix if c.merge else prefix + [(nid, label)])

    base: Path = []
    if not dim.hide_label and not dim.hide_all:
        base = [((dim_pos << 20) | 0xFFFFF, dim.name.text + _marker(dim.name, table))]
    walk(dim.categories, base)
    if dim.hide_all:  # drop every label for this dimension
        out = [([], li) for _, li in out]
    return out


def _axis(dim_ids: list[int], table: LightTable) -> list[tuple[Path, list[tuple[int, int]]]]:
    """Cross the dimensions of one axis. Returns, per display position, the full
    label path and the (dim index, leaf_index) coordinates.

    The axis list gives inner dimensions first; the *last* one is outermost."""
    entries: list[tuple[Path, list[tuple[int, int]]]] = [([], [])]
    for d in reversed(dim_ids):  # outermost first
        leaves = _leaf_paths(table.dims[d], d, table)
        entries = [(p + lp, co + [(d, li)]) for p, co in entries for lp, li in leaves]
    return entries


def _headers(paths: list[Path]) -> list[list[dict[str, Any]]]:
    """Build header cells per level with spans for one axis.

    Returns levels[level] -> list of {"t","span","start","depth_end"} where a
    cell covers positions [start, start+span). Shorter paths extend their last
    label across the remaining levels (cross-span)."""
    n = len(paths)
    depth = max((len(p) for p in paths), default=0)
    levels: list[list[dict[str, Any]]] = [[] for _ in range(depth)]
    for k in range(depth):
        i = 0
        while i < n:
            p = paths[i]
            if len(p) <= k:
                i += 1
                continue
            j = i + 1
            while j < n and len(paths[j]) > k and paths[j][: k + 1] == p[: k + 1]:
                j += 1
            levels[k].append({"t": p[k][1], "start": i, "span": j - i,
                              "leaf": len(p) == k + 1})
            i = j
    return levels


def _cell_text(v: Optional[Val], table: LightTable) -> tuple[str, str]:
    if v is None:
        return "", "text"
    return v.text + _marker(v, table), ("num" if v.num is not None else "text")


def to_pivot_json(table: LightTable, caption_override: Optional[str] = None) -> dict[str, Any]:
    rows = _axis(table.rows, table)
    # A layer with a single category (e.g. the variable name over a Statistics
    # table) is shown by SPSS as an outer column header.
    single_layers = [d for d in table.layers if table.dims[d].n_leaves == 1]
    cols = _axis(table.cols + single_layers, table)
    nr, nc = len(rows), len(cols)
    row_depth = max((len(p) for p, _ in rows), default=0) or 1
    col_depth = max((len(p) for p, _ in cols), default=0) or 1

    # Cell lookup: index folds the leaf-index of every dimension, in dim order.
    sizes = [d.n_leaves for d in table.dims]
    layer_leaf = {d: 0 for d in table.layers}

    def index_of(coords: dict[int, int]) -> int:
        idx = 0
        for i, n in enumerate(sizes):
            idx = idx * n + coords.get(i, layer_leaf.get(i, 0))
        return idx

    grid: list[list[str]] = []
    kinds: list[list[str]] = []
    for _, rco in rows:
        rd = dict(rco)
        g_row, k_row = [], []
        for _, cco in cols:
            t, k = _cell_text(table.cells.get(index_of({**rd, **dict(cco)})), table)
            g_row.append(t)
            k_row.append(k)
        grid.append(g_row)
        kinds.append(k_row)

    # Row headers: per-row <th> cells that start on that row (rowspan covers the rest).
    row_headers = _row_header_cells(rows, row_depth, nr)

    col_levels = _headers([p for p, _ in cols])
    col_headers: list[list[dict[str, Any]]] = []
    for k, level in enumerate(col_levels):
        row_cells = []
        for c in level:
            rs = (col_depth - k) if c["leaf"] else 1
            row_cells.append({"t": c["t"], "cs": c["span"], "rs": rs})
        col_headers.append(row_cells)
    if not col_headers:
        col_headers = [[{"t": "", "cs": max(nc, 1), "rs": 1}]]

    cap = caption_override if caption_override is not None else (
        table.caption.text if table.caption else None)
    foot = [t.text for t, _ in table.footnotes]
    title = table.user_title.text or table.title.text
    out: dict[str, Any] = {
        "type": "PivotTable",
        "title": title,
        "caption": cap,
        "corner": table.corner.text if table.corner else "",
        "rowDims": [], "colDims": [], "cells": [],
        "flat": {
            "rowHeaderCols": row_depth,
            "colHeaders": col_headers,
            "rowHeaders": row_headers,
            "grid": grid,
            "kinds": kinds,
        },
    }
    if foot:
        out["footnotes"] = foot
    return out


def _row_header_cells(rows: list[tuple[Path, list[tuple[int, int]]]], depth: int, n: int
                      ) -> list[list[dict[str, Any]]]:
    """Per body row, the <th> cells that *start* on that row (rowspan merges the rest)."""
    paths = [p for p, _ in rows]
    out: list[list[dict[str, Any]]] = [[] for _ in range(n)]
    for k in range(depth):
        i = 0
        while i < n:
            p = paths[i]
            if len(p) <= k:
                i += 1
                continue
            j = i + 1
            while j < n and len(paths[j]) > k and paths[j][: k + 1] == p[: k + 1]:
                j += 1
            leaf = len(p) == k + 1
            out[i].append({"t": p[k][1], "rs": j - i, "cs": (depth - k) if leaf else 1})
            i = j
    return out

"""Writer for IBM SPSS Statistics `.spv` output files.

Layout and binary grammar follow the public SPV format documentation (GNU PSPP
Developer's Guide). Default styling values mirror what SPSS itself writes.

Per output item:
  Title/TextBlock -> `container` with `text` in the structure XML
  PivotTable      -> `*_lightTableData.bin` (version 3 light member)
  Chart           -> original VizML + data members when the chart came from an
                     .spv (byte-exact), otherwise a PNG image member
Everything else becomes a text block so nothing is silently dropped.
"""
from __future__ import annotations

import base64
import re
import struct
import time
import zipfile
from datetime import datetime
from typing import Any, Optional
from xml.sax.saxutils import escape, quoteattr

from .spv_light import Category, Dimension, LightTable, Val, fmt_number

# Claim the oldest viewer version that has light members (what PSPP writes), so a file is not
# presented as coming from a newer SPSS than the one opening it.
CREATOR_VERSION = "21"
_F40 = (5 << 16) | (40 << 8)  # F format, width 40 ("show as-is"), decimals OR'd in


# ---- binary primitives --------------------------------------------------
def _s(text: str) -> bytes:
    b = text.encode("utf-8")
    return struct.pack("<I", len(b)) + b


def _i32(v: int) -> bytes:
    return struct.pack("<i", v)


def _be32(v: int) -> bytes:
    return struct.pack(">I", v)


def _count(b: bytes) -> bytes:
    return struct.pack("<I", len(b)) + b


# ---- Value ----------------------------------------------------------------
def _value(v: Val) -> bytes:
    # A bare number only when its text is just the formatted number; a value-labelled
    # number ("Did not complete high school" for 1) is written as the label text.
    if v.num is not None and v.fmt is not None and v.text == fmt_number(v.num, v.fmt):
        return b"\x01\x58" + struct.pack("<I", v.fmt) + struct.pack("<d", v.num)
    # type 3 text: local, ValueMod(none), id, c, fixed
    return b"\x03" + _s(v.text) + b"\x58" + _s("") + _s(v.text) + b"\x01"


def text_val(text: str) -> Val:
    return Val(text)


_NUM = re.compile(r"^-?\d+(\.\d+)?$")


def cell_val(text: str) -> Val:
    """A cell from pre-formatted text: plain decimals become real numbers (F40.d)
    so SPSS renders them itself; everything else stays text."""
    t = text.strip()
    if _NUM.match(t):
        d = len(t.split(".")[1]) if "." in t else 0
        return Val(text, float(t), _F40 | d, kind="num")
    return Val(text)


# ---- sections ----------------------------------------------------------------
_AREAS = [  # (size, style, halign, valign, fg, bg, margins) for: title, caption,
    # footer, corner, column labels, row labels, data, layers (SPSS defaults)
    (14.0, 1, 0, 0, "#010205", "#ffffff", (6, 8, 1, 6)),
    (12.0, 0, 2, 1, "#010205", "#ffffff", (6, 8, 1, 1)),
    (12.0, 0, 2, 1, "#010205", "#ffffff", (18, 18, 2, 3)),
    (12.0, 0, 2, 3, "#264a60", "#ffffff", (6, 8, 3, 1)),
    (12.0, 0, 0, 3, "#264a60", "#ffffff", (6, 8, 2, 2)),
    (12.0, 0, 2, 1, "#264a60", "#e0e0e0", (6, 8, 3, 2)),
    (12.0, 0, 64173, 1, "#010205", "#f9f9fb", (6, 8, 3, 2)),
    (12.0, 0, 2, 3, "#010205", "#ffffff", (6, 8, 1, 3)),
]

_BORDERS = [  # (type, stroke, argb) in the order SPSS writes them
    (4, 0, 4279576885), (2, 0, 4279576885), (3, 0, 4279576885), (14, 0, 4289638062),
    (0, 0, 4279576885), (18, 1, 4292927712), (6, 0, 4279576885), (7, 0, 4279576885),
    (9, 0, 4279576885), (12, 0, 4289638062), (13, 0, 4289638062), (15, 1, 4289638062),
    (10, 1, 4279576885), (8, 1, 4279576885), (11, 0, 4289638062), (16, 0, 4289638062),
    (1, 0, 4279576885), (17, 0, 4289638062), (5, 0, 4279576885),
]


def _areas() -> bytes:
    out = b""
    for i, (size, style, ha, va, fg, bg, m) in enumerate(_AREAS, start=1):
        out += bytes([i, 0x31]) + _s("SansSerif") + struct.pack("<f", size) + _i32(style) + b"\x00"
        out += _i32(ha) + _i32(va) + _s(fg) + _s(bg) + b"\x00" + _s("") + _s("")
        out += struct.pack("<4i", *m)
    return out


def _borders() -> bytes:
    body = b"\x00\x00\x00\x01" + _be32(len(_BORDERS))
    for t, st, argb in _BORDERS:
        body += _be32(t) + _be32(st) + _be32(argb)
    body += b"\x00" + b"\x00\x00\x00"  # show-grid-lines off, padding
    return _count(body)


def _print_settings() -> bytes:
    body = b"\x00\x00\x00\x01" + bytes([0, 0, 0, 0, 0, 0]) + _be32(2) + _be32(0)
    return _count(body)


def _table_settings() -> bytes:
    body = b"\x00\x00\x00\x01" + _be32(4) + _be32(0)  # endian, x5, current-layer
    body += bytes([1, 1, 1, 1, 0])  # omit-empty, labels-in-corner, alpha markers, superscripts, x6
    body += _be32(24) + b"\x00" * 24  # breakpoints/keeps (none)
    body += _be32(0)  # notes
    body += _be32(7) + b"default"  # table-look
    body += b"\x00" * 82
    return _count(body)


_CCS = _i32(5) + b"".join(_s("-,,,") for _ in range(5))


def _y0() -> bytes:
    return _i32(1957) + b".,"  # epoch, decimal, grouping


def _y1(command: str) -> bytes:
    # Strings are written as UTF-8, so say so (as PSPP does) rather than a Latin-1 charset.
    return (_s(command) + _s("") + _s("en") + _s("UTF-8") + _s("en_US.UTF-8")
            + bytes([0, 0, 1, 1]) + _y0())


def _formats(command: str) -> bytes:
    x1 = (bytes([0, 1, 0, 0, 2, 2]) + _i32(-1) + _i32(-1) + b"\x00" * 17 + bytes([0, 1]))
    x2 = _i32(0) + _i32(0) + _i32(0) + _count(b"\x00" * 8)
    x3 = (b"\x01\x00\x04\x00\x00\x00" + _y1(command) + struct.pack("<d", 0.0001) + b"\x01"
          + _s("DataSet1") + _s("") + _i32(0) + struct.pack("<I", int(time.time()) & 0xFFFFFFFF) + _i32(0)
          + _CCS + b".\x00")
    inner = _count(x1 + _count(x2)) + _count(x3)
    out = _i32(0) + _s("en_US.ISO_8859-1:1987") + _i32(0) + bytes([0, 0, 1]) + _y0() + _CCS
    return out + _count(inner)


# ---- dimensions ----------------------------------------------------------------
def _category(c: Category) -> bytes:
    out = _value(c.name)
    if c.leaf_index is not None:
        return out + b"\x00\x00\x00" + _i32(2) + _i32(c.leaf_index) + _i32(0)
    out += bytes([1 if c.merge else 0, 0, 1]) + _i32(0) + _i32(-1) + _i32(len(c.children))
    return out + b"".join(_category(k) for k in c.children)


def _dimension(d: Dimension, pos: int, axis_kind: int) -> bytes:
    out = _value(d.name)
    out += bytes([0, axis_kind]) + _i32(2) + bytes([1 if d.hide_label else 0, 1 if d.hide_all else 0, 1])
    out += _i32(pos) + _i32(len(d.categories))
    return out + b"".join(_category(c) for c in d.categories)


def write_light(t: LightTable, table_id: int, command: str) -> bytes:
    """Serialize a LightTable as a version-3 light member."""
    out = b"\x01\x00" + _i32(3) + bytes([1, 0, 0, 0, 1]) + _i32(0x15)
    out += _i32(68) + _i32(98) + _i32(49) + _i32(164) + struct.pack("<q", table_id)
    out += _value(t.title) + _value(t.subtype) + b"\x01\x31" + _value(t.user_title)
    out += (b"\x31" + _value(t.corner)) if t.corner else b"\x58"
    out += (b"\x31" + _value(t.caption)) if t.caption else b"\x58"
    out += _i32(0)  # footnotes (folded into the caption)
    out += _areas() + _borders() + _print_settings() + _table_settings() + _formats(command)
    kinds = {d: 2 for d in t.layers}
    kinds.update({d: 0 for d in t.rows})
    kinds.update({d: 1 for d in t.cols})
    out += _i32(len(t.dims))
    out += b"".join(_dimension(d, i, kinds.get(i, 0)) for i, d in enumerate(t.dims))
    out += _i32(len(t.layers)) + _i32(len(t.rows)) + _i32(len(t.cols))
    out += b"".join(_i32(i) for i in t.layers + t.rows + t.cols)
    out += _i32(len(t.cells))
    for idx in sorted(t.cells):
        out += struct.pack("<Q", idx) + _value(t.cells[idx])
    return out + b"\x01"


# ---- PivotTable JSON -> LightTable -------------------------------------------------
def _leaf_dim(label: str, names: list[str]) -> Dimension:
    cats = [Category(text_val(n), leaf_index=i) for i, n in enumerate(names)]
    return Dimension(text_val(label), hide_label=not label, hide_all=False, categories=cats,
                     n_leaves=len(names))


def _spanner_dim(leaves: list[str], spanners: list[list[dict[str, Any]]]) -> Dimension:
    """One column dimension whose category tree reproduces spanner rows (top -> bottom)."""

    def build(level: int, lo: int, hi: int) -> list[Category]:
        if level >= len(spanners):
            return [Category(text_val(leaves[i]), leaf_index=i) for i in range(lo, hi)]
        out: list[Category] = []
        pos = 0
        for g in spanners[level]:
            a, b = pos, pos + int(g["span"])
            pos = b
            if b <= lo or a >= hi:
                continue
            kids = build(level + 1, max(a, lo), min(b, hi))
            label = g.get("label", "")
            out.append(Category(text_val(label), children=kids, merge=not label))
        return out

    cats = build(0, 0, len(leaves))
    return Dimension(text_val(""), hide_label=True, hide_all=False, categories=cats, n_leaves=len(leaves))


def table_to_light(tj: dict[str, Any]) -> LightTable:
    title = tj.get("title") or "Table"
    row_dims = tj.get("rowDims", [])
    cells = {(tuple(c["r"]), tuple(c["c"])): c["v"] for c in tj.get("cells", [])}
    dims: list[Dimension] = [_leaf_dim(d["label"], d["categories"]) for d in row_dims]
    n_row = len(dims)
    if tj.get("colLeaves") is not None:
        dims.append(_spanner_dim(tj["colLeaves"], [[{"label": g["label"], "span": g["span"]}
                                                    for g in row] for row in tj.get("colSpanners", [])]))
        col_keys = [(i,) for i in range(len(tj["colLeaves"]))]
    else:
        dims += [_leaf_dim(d["label"], d["categories"]) for d in tj.get("colDims", [])]
        col_keys = [()]
        for d in tj.get("colDims", []):
            col_keys = [k + (i,) for k in col_keys for i in range(len(d["categories"]))]
    row_keys = [()]
    for d in row_dims:
        row_keys = [k + (i,) for k in row_keys for i in range(len(d["categories"]))]
    sizes = [d.n_leaves for d in dims]
    out: dict[int, Val] = {}
    for rk in row_keys:
        for ck in col_keys:
            text = cells.get((rk, ck))
            if text is None:
                continue
            coords = list(rk) + list(ck)
            idx = 0
            for n, x in zip(sizes, coords):
                idx = idx * n + x
            out[idx] = cell_val(text)
    n_col = len(dims) - n_row
    # Axis lists give the inner dimension first (the last entry is outermost).
    rows = list(range(n_row))[::-1]
    cols = list(range(n_row, n_row + n_col))[::-1]
    caption = tj.get("caption") or ""
    foot = tj.get("footnotes") or []
    if foot:
        caption = "\n".join([caption] if caption else []) + ("\n" if caption else "") + "\n".join(
            f"{chr(97 + i % 26)}. {t}" for i, t in enumerate(foot))
    return LightTable(3, text_val(title), text_val(title), text_val(title),
                      text_val(tj["corner"]) if tj.get("corner") else None,
                      text_val(caption) if caption else None, [], dims, [], rows, cols, out)


# ---- structure XML ---------------------------------------------------------------------
_NS = ('xmlns="http://xml.spss.com/spss/viewer/viewer-tree" '
       'xmlns:vgr="http://xml.spss.com/spss/viewer/viewer-graph" '
       'xmlns:vizml="http://xml.spss.com/visualization" '
       'xmlns:vmd="http://xml.spss.com/spss/viewer/viewer-model" '
       'xmlns:vps="http://xml.spss.com/spss/viewer/viewer-pagesetup" '
       'xmlns:vst="http://xml.spss.com/spss/viewer/viewer-style" '
       'xmlns:vtb="http://xml.spss.com/spss/viewer/viewer-table" '
       'xmlns:vtl="http://xml.spss.com/spss/viewer/table-looks" '
       'xmlns:vtt="http://xml.spss.com/spss/viewer/viewer-treemodel" '
       'xmlns:vtx="http://xml.spss.com/spss/viewer/viewer-text" '
       'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')

_SCHEMA = ('xsi:schemaLocation="http://xml.spss.com/spss/viewer/viewer-tree '
           'http://xml.spss.com/spss/viewer/viewer-tree-1.2.xsd"')


def _root(body: str) -> str:
    stamp = datetime.now().strftime("%A, %d %B %Y at %I:%M:%S %p")
    return ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>'
            f'<heading {_NS} creation-date-time={quoteattr(stamp)} creator="Vari" '
            f'creator-version="{CREATOR_VERSION}" {_SCHEMA}>'
            f"<label>Output</label>{body}</heading>")


def _text_container(label: str, text: str, kind: str, command: str) -> str:
    if kind == "title":
        style = "p{color:0;font-family:SansSerif;font-size:14pt;font-style:normal;font-weight:bold;text-decoration:none}"
        cmd = f' commandName={quoteattr(command)}'
    else:
        style = "p{color:0;font-family:Monospaced;font-size:14pt;font-style:normal;font-weight:normal;text-decoration:none}"
        cmd = ' commandName="log"'
    html = f'<head><style type="text/css">{style}</style></head><BR>{text}'.replace("]]>", "]]]]><![CDATA[>")
    return (f'<container text-align="left" visibility="visible" width="706px"><label>{escape(label)}</label>'
            f'<vtx:text{cmd} type="{kind}"><html xmlns="http://www.w3.org/1999/xhtml" lang="en">'
            f"<![CDATA[{html}]]></html></vtx:text></container>")


# ---- assembly ------------------------------------------------------------------------------
class _Writer:
    def __init__(self, z: zipfile.ZipFile) -> None:
        self.z = z
        self.n = 0
        self.tid = -4000000000000000000

    def member(self) -> str:
        self.n += 1
        return f"{self.n:011d}"

    def table_id(self) -> int:
        self.tid += 1024
        return self.tid

    def container(self, item: dict[str, Any], command: str) -> str:
        t = item.get("type")
        if t == "PivotTable":
            return self._table(item, command)
        if t == "Chart":
            return self._chart(item, command)
        if t in ("Title", "TextBlock", "Warning", "Error"):
            return _text_container("Text", str(item.get("text", "")), "log", command)
        if t == "Notes":
            rows = "\n".join(f"{r['label']}: {r['value']}" for r in item.get("rows", []))
            return _text_container("Notes", rows, "log", command)
        return _text_container("Text", f"[{t}]", "log", command)

    def _table(self, item: dict[str, Any], command: str) -> str:
        raw = item.get("spv")
        tid = self.table_id()
        name = f"{self.member()}_lightTableData.bin"
        if raw and raw.get("kind") == "light":
            # Came from an IBM file and not rebuilt: keep the original bytes.
            data = base64.b64decode(raw["data"])
        else:
            light = flat_to_light(item) if item.get("flat") else table_to_light(item)
            data = write_light(light, tid, command)
        self.z.writestr(name, data)
        title = escape(str(item.get("title") or "Table"))
        sub = quoteattr(str(item.get("title") or "Table"))
        return (f'<container text-align="left" visibility="visible"><label>{title}</label>'
                f'<vtb:table commandName={quoteattr(command)} '
                f'subType={sub} tableId="{tid}" type="table"><vtb:tableStructure>'
                f"<vtb:dataPath>{name}</vtb:dataPath></vtb:tableStructure></vtb:table></container>")

    def _chart(self, item: dict[str, Any], command: str) -> str:
        raw = item.get("spv")
        if raw and "xml" in raw:
            base = self.member()
            xml_name = f"{base}_{raw['xmlName'].split('_', 1)[-1]}" if raw.get("xmlName") else f"{base}_chart.xml"
            data_name = f"{base}_{raw['dataName'].split('_', 1)[-1]}" if raw.get("dataName") else f"{base}_chartData.bin"
            self.z.writestr(xml_name, base64.b64decode(raw["xml"]))
            self.z.writestr(data_name, base64.b64decode(raw["data"]))
            return ('<container text-align="left" visibility="visible"><label>Graph</label>'
                    f'<vgr:graph commandName={quoteattr(command)} '
                    'editor="ChartEditor"><vtb:dataPath>' + data_name + "</vtb:dataPath><vtb:path>"
                    + xml_name + "</vtb:path></vgr:graph></container>")
        png = item.get("png")
        if not png:
            return _text_container("Graph", "[Chart image unavailable]", "log", command)
        name = f"{self.member()}_Imagegeneric.png"
        self.z.writestr(name, base64.b64decode(png))
        return ('<container text-align="left" visibility="visible"><label>Graph</label>'
                f'<object commandName={quoteattr(command)} type="unknown" uri="{name}"/></container>')


def _tree_from_paths(paths: list[list[tuple[int, str]]]) -> list[Category]:
    """Category tree from per-leaf header paths. Consecutive leaves sharing a path prefix
    (same header-cell identity) share a group; the last element of a path is the leaf."""
    roots: list[Category] = []
    stack: list[tuple[int, Category]] = []  # open groups: (cell identity, group)
    for leaf_index, path in enumerate(paths):
        # keep the open groups that this path still belongs to
        keep = 0
        while keep < len(stack) and keep < len(path) - 1 and stack[keep][0] == path[keep][0]:
            keep += 1
        del stack[keep:]
        for ident, label in path[keep:-1]:
            group = Category(text_val(label), children=[])
            (stack[-1][1].children if stack else roots).append(group)
            stack.append((ident, group))
        leaf = Category(text_val(path[-1][1]), leaf_index=leaf_index)
        (stack[-1][1].children if stack else roots).append(leaf)
    return roots


def flat_to_light(item: dict[str, Any]) -> LightTable:
    """Rebuild a LightTable from a flat (header-cells-with-spans) table, keeping row groups
    and column spanners as category groups."""
    f = item["flat"]
    grid = f["grid"]
    nr = len(grid)
    nc = len(grid[0]) if grid else 0
    width = f["rowHeaderCols"]

    # Row header paths: place each body row's cells into the first free header column.
    ident = 0
    busy: list[tuple[int, str, int] | None] = [None] * width  # (identity, label, rows left)
    row_paths: list[list[tuple[int, str]]] = []
    for r in range(nr):
        for c in f["rowHeaders"][r] if r < len(f["rowHeaders"]) else []:
            col = next((i for i in range(width) if busy[i] is None), 0)
            ident += 1
            for i in range(col, min(col + c["cs"], width)):
                busy[i] = (ident, c["t"], c["rs"])
        path: list[tuple[int, str]] = []
        for slot in busy:
            if slot and (not path or path[-1][0] != slot[0]):
                path.append((slot[0], slot[1]))
        row_paths.append(path or [(-r - 1, str(r + 1))])
        busy = [(b[0], b[1], b[2] - 1) if b and b[2] > 1 else None for b in busy]

    # Column header paths: header rows top to bottom, cells placed left to right.
    col_busy: list[list[tuple[int, str] | None]] = [[None] * nc for _ in f["colHeaders"]]
    col_paths: list[list[tuple[int, str]]] = [[] for _ in range(nc)]
    for k, row in enumerate(f["colHeaders"]):
        pos = 0
        for c in row:
            while pos < nc and col_busy[k][pos] is not None:
                pos += 1
            ident += 1
            for j in range(pos, min(pos + c["cs"], nc)):
                for kk in range(k, min(k + c["rs"], len(f["colHeaders"]))):
                    col_busy[kk][j] = (ident, c["t"])
            pos += c["cs"]
    for j in range(nc):
        for k in range(len(f["colHeaders"])):
            slot = col_busy[k][j]
            if slot and (not col_paths[j] or col_paths[j][-1][0] != slot[0]):
                col_paths[j].append(slot)
        if not col_paths[j]:
            col_paths[j] = [(-j - 1, str(j + 1))]

    row_dim = Dimension(text_val(""), True, False, _tree_from_paths(row_paths), nr)
    col_dim = Dimension(text_val(""), True, False, _tree_from_paths(col_paths), nc)
    cells = {r * nc + c: cell_val(grid[r][c]) for r in range(nr) for c in range(nc) if grid[r][c] != ""}
    title = item.get("title") or "Table"
    caption = item.get("caption") or ""
    foot = item.get("footnotes") or []
    if foot:
        caption = "\n".join(([caption] if caption else []) + [f"{chr(97 + i % 26)}. {t}" for i, t in enumerate(foot)])
    return LightTable(3, text_val(title), text_val(title), text_val(title),
                      text_val(item["corner"]) if item.get("corner") else None,
                      text_val(caption) if caption else None, [], [row_dim, col_dim], [], [0], [1], cells)


def _command_of(group: list[dict[str, Any]]) -> str:
    for it in group:
        if it.get("type") == "Title":
            return str(it.get("text") or "Output")
    return "Output"


def _groups(items: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """Split the output stream into one group per procedure (starting at each Title)."""
    groups: list[list[dict[str, Any]]] = []
    pending_log: list[dict[str, Any]] = []
    for it in items:
        if it.get("type") == "Title":
            groups.append(pending_log + [it])
            pending_log = []
        elif not groups:
            pending_log.append(it)
        else:
            groups[-1].append(it)
    if pending_log:
        groups.append(pending_log)
    return groups


def write_ibm_spv(items: list[dict[str, Any]], path: str) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        w = _Writer(z)
        for gi, group in enumerate(_groups(items)):
            command = _command_of(group)
            body = ""
            for it in group:
                if it.get("type") == "Title":
                    body += _text_container("Title", str(it.get("text", "")), "title", command)
                else:
                    body += w.container(it, command)
            inner = (f'<heading commandName={quoteattr(command)} '
                     f'locale="en-US" olang="en"><label>{escape(command)}</label>{body}</heading>')
            z.writestr(f"outputViewer{gi:010d}_heading.xml", _root(inner))
        z.writestr("META-INF/MANIFEST.MF", "allowPivoting=true")

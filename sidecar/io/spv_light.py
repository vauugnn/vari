"""Reader for SPSS Viewer "light" detail members (`*_lightTableData.bin`,
`*_lightNotesData.bin`, `*_lightWarningData.bin`).

Implemented from the publicly documented SPV light-member grammar (GNU PSPP
Developer's Guide, "SPSS Viewer File Format"). The reader extracts the table
structure (title, dimensions, category trees, axis assignment, cells,
footnotes); presentation-only sections (areas, borders, print/table settings)
are skipped by length.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Optional

DBL_MAX_NEG = -1.7976931348623157e308  # SYSMIS marker


class LightError(ValueError):
    pass


@dataclass
class Val:
    """A decoded Value: display text plus the numeric payload when there is one."""
    text: str
    num: Optional[float] = None
    fmt: Optional[int] = None
    refs: list[int] = field(default_factory=list)
    subs: list[str] = field(default_factory=list)
    kind: str = "text"  # text | num | var | template


@dataclass
class Category:
    name: Val
    leaf_index: Optional[int] = None  # None for groups
    children: list["Category"] = field(default_factory=list)
    merge: bool = False


@dataclass
class Dimension:
    name: Val
    hide_label: bool
    hide_all: bool
    categories: list[Category]
    n_leaves: int = 0


@dataclass
class LightTable:
    version: int
    title: Val
    subtype: Val
    user_title: Val
    corner: Optional[Val]
    caption: Optional[Val]
    footnotes: list[tuple[Val, Optional[Val]]]
    dims: list[Dimension]
    layers: list[int]
    rows: list[int]
    cols: list[int]
    cells: dict[int, Val]
    show_variables: int = 0
    show_values: int = 0


class _R:
    def __init__(self, b: bytes) -> None:
        self.b = b
        self.i = 0

    def peek(self) -> int:
        return self.b[self.i] if self.i < len(self.b) else -1

    def u8(self) -> int:
        v = self.b[self.i]
        self.i += 1
        return v

    def take(self, n: int) -> bytes:
        if n < 0 or self.i + n > len(self.b):
            raise LightError("truncated light member")
        v = self.b[self.i : self.i + n]
        self.i += n
        return v

    def i16(self) -> int:
        return struct.unpack("<H", self.take(2))[0]

    def i32(self) -> int:
        return struct.unpack("<I", self.take(4))[0]

    def s32(self) -> int:
        return struct.unpack("<i", self.take(4))[0]

    def i64(self) -> int:
        return struct.unpack("<Q", self.take(8))[0]

    def f64(self) -> float:
        return struct.unpack("<d", self.take(8))[0]

    def string(self) -> str:
        n = self.i32()
        raw = self.take(n)
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            return raw.decode("cp1252", errors="replace")

    def expect(self, *vals: int) -> int:
        v = self.u8()
        if v not in vals:
            raise LightError(f"expected {vals} at offset {self.i - 1}, got {v:#x}")
        return v


# ---- number formatting ------------------------------------------------
def fmt_number(x: float, fmt: int) -> str:
    """Render a numeric Value per its SPSS format word (type<<16|width<<8|decimals)."""
    if x == DBL_MAX_NEG:
        return "."
    typ, d = (fmt >> 16) & 0xFF, fmt & 0xFF
    if typ in (5, 40) or typ == 0:  # F / generic
        if x != x:
            return "."
        return f"{x:.{d}f}" if (typ == 5 or d) else _plain(x)
    if typ == 3:  # COMMA
        return f"{x:,.{d}f}"
    if typ == 4:  # DOLLAR
        return f"${x:,.{d}f}"
    if typ == 6:  # PCT? (treated as number + %)
        return f"{x:.{d}f}%"
    if typ == 7:  # E
        return f"{x:.{d}E}"
    return _plain(x) if not d else f"{x:.{d}f}"


def _plain(x: float) -> str:
    if x == int(x) and abs(x) < 1e15:
        return str(int(x))
    return repr(x)


# ---- Value ------------------------------------------------------------
def _value(r: _R, v: int) -> Val:
    for _ in range(4):
        if r.peek() == 0:
            r.u8()
        else:
            break
    t = r.peek()
    if t == 1:
        r.u8()
        refs, subs = _valuemod(r, v)
        fmt = r.i32()
        x = r.f64()
        return Val(fmt_number(x, fmt), x, fmt, refs, subs, "num")
    if t == 2:
        r.u8()
        refs, subs = _valuemod(r, v)
        fmt = r.i32()
        x = r.f64()
        var, label, show = r.string(), r.string(), r.u8()
        txt = _show_value(fmt_number(x, fmt), label, show)
        return Val(txt, x, fmt, refs, subs, "num")
    if t == 3:
        r.u8()
        local = r.string()
        refs, subs = _valuemod(r, v)
        r.string()  # id
        c = r.string()
        r.u8()  # fixed
        return Val(local or c, None, None, refs, subs)
    if t == 4:
        r.u8()
        refs, subs = _valuemod(r, v)
        r.i32()  # format (ignored for strings)
        label, var, show = r.string(), r.string(), r.u8()
        s = r.string()
        return Val(_show_value(s, label, show), None, None, refs, subs)
    if t == 5:
        r.u8()
        refs, subs = _valuemod(r, v)
        var, vlabel, show = r.string(), r.string(), r.u8()
        txt = {1: var, 2: vlabel or var, 3: f"{var} {vlabel}".strip()}.get(show, vlabel or var)
        return Val(txt, None, None, refs, subs, "var")
    if t == 6:
        r.u8()
        local = r.string()
        refs, subs = _valuemod(r, v)
        r.string()
        c = r.string()
        return Val(local or c, None, None, refs, subs)
    # template
    refs, subs = _valuemod(r, v)
    template = r.string()
    n = r.i32()
    args: list[list[Val]] = []
    for _ in range(n):
        x = r.i32()
        if x == 0:  # `i0 Value`: the zero was x itself
            args.append([_value(r, v)])
        else:
            r.i32()  # i0
            args.append([_value(r, v) for _ in range(x)])
    return Val(_expand(template, args), None, None, refs, subs, "template")


def _show_value(num_txt: str, label: str, show: int) -> str:
    if show == 2 and label:
        return label
    if show == 3 and label:
        return f"{num_txt} {label}"
    return num_txt


def _valuemod(r: _R, v: int) -> tuple[list[int], list[str]]:
    b = r.u8()
    if b == 0x58:
        return [], []
    if b != 0x31:
        raise LightError(f"bad ValueMod byte {b:#x} at {r.i - 1}")
    refs = [r.i16() for _ in range(r.i32())]
    subs = [r.string() for _ in range(r.i32())]
    if v == 3:
        r.take(r.i32())  # TemplateString + StylePair, not needed to read
    else:  # version 1: 00 (i1|i2) 00? 00? int32 00? 00?
        r.u8()
        r.i32()
        for _ in range(2):
            if r.peek() == 0:
                r.u8()
        r.i32()
        for _ in range(2):
            if r.peek() == 0:
                r.u8()
    return refs, subs


def _expand(t: str, args: list[list[Val]]) -> str:
    """Expand a PSPP-style template: ^i, [:a:]i, [a:b:]i and \\x escapes."""
    out: list[str] = []
    i, n = 0, len(t)

    def texts(k: int) -> list[str]:
        return [a.text for a in args[k - 1]] if 0 < k <= len(args) else []

    def fill(pat: str, vals: list[str], pos: int) -> tuple[str, int]:
        """Substitute ^j / %j in pat with consecutive values starting at pos."""
        s = pat
        for j in range(1, 10):
            for mark in (f"^{j}", f"%{j}"):
                if mark in s and pos < len(vals):
                    s = s.replace(mark, vals[pos], 1)
                    pos += 1
        return s, pos

    while i < n:
        c = t[i]
        if c == "\\" and i + 1 < n:
            out.append("\n" if t[i + 1] == "n" else t[i + 1])
            i += 2
        elif c == "^" and i + 1 < n and t[i + 1].isdigit():
            v = texts(int(t[i + 1]))
            out.append(v[0] if v else "")
            i += 2
        elif c == "[" and (j := t.find("]", i)) > 0 and j + 1 < n and t[j + 1].isdigit():
            parts = t[i + 1 : j].split(":")
            # `[:a:]k` -> a for every value; `[a:b:]k` -> a for the first, b after.
            first, rest = (parts[1], parts[1]) if parts[0] == "" else (parts[0], parts[1])
            vals, pos, k = texts(int(t[j + 1])), 0, 0
            while pos < len(vals):
                piece, new_pos = fill(first if k == 0 else rest, vals, pos)
                out.append(piece)
                pos = new_pos if new_pos > pos else pos + 1
                k += 1
            i = j + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


# ---- categories / dimensions ------------------------------------------
def _category(r: _R, v: int) -> Category:
    name = _value(r, v)
    if r.b[r.i : r.i + 3] == b"\x00\x00\x00" and r.b[r.i + 3 : r.i + 7] == b"\x02\x00\x00\x00":
        r.take(7)
        idx = r.i32()
        r.i32()  # i0
        return Category(name, leaf_index=idx)
    merge = bool(r.u8())
    r.expect(0)
    r.expect(1)
    r.i32()  # x23
    r.s32()  # -1
    n = r.i32()
    return Category(name, children=[_category(r, v) for _ in range(n)], merge=merge)


def _count_leaves(cats: list[Category]) -> int:
    return sum(1 if c.leaf_index is not None else _count_leaves(c.children) for c in cats)


def _dimension(r: _R, v: int) -> Dimension:
    name = _value(r, v)
    r.u8()  # x1
    r.u8()  # x2
    r.i32()  # x3
    hide_label = bool(r.u8())
    hide_all = bool(r.u8())
    r.expect(1)
    r.i32()  # dim-index
    n = r.i32()
    cats = [_category(r, v) for _ in range(n)]
    return Dimension(name, hide_label, hide_all, cats, _count_leaves(cats))


# ---- top level ---------------------------------------------------------
def parse_light(data: bytes) -> LightTable:
    r = _R(data)
    r.expect(0x01)
    r.expect(0x00)
    version = r.i32()
    if version not in (1, 3):
        raise LightError(f"unsupported light member version {version}")
    r.take(5 + 4 + 16 + 8)  # bools, x3, widths, table-id
    # Titles
    title = _value(r, version)
    if r.peek() == 1:
        r.u8()
    subtype = _value(r, version)
    if r.peek() == 1:
        r.u8()
    r.expect(0x31)
    user_title = _value(r, version)
    if r.peek() == 1:
        r.u8()
    corner = caption = None
    if r.u8() == 0x31:
        corner = _value(r, version)
    if r.u8() == 0x31:
        caption = _value(r, version)
    # Footnotes
    notes: list[tuple[Val, Optional[Val]]] = []
    for _ in range(r.i32()):
        text = _value(r, version)
        marker = _value(r, version) if r.u8() == 0x31 else None
        r.i32()  # show
        notes.append((text, marker))
    # Areas
    if r.peek() == 0:
        r.u8()
    for _ in range(8):
        r.u8()  # index
        r.expect(0x31)
        r.string()
        r.take(4 + 4 + 1 + 4 + 4)  # size style underline halign valign
        r.string()
        r.string()
        r.u8()
        r.string()
        r.string()
        if version == 3:
            r.take(16)
    # Borders, PrintSettings, TableSettings: length-prefixed blobs
    r.take(r.i32())
    r.take(r.i32())
    if version == 3:
        r.take(r.i32())
    show_vars = show_vals = 0
    # Formats
    for _ in range(r.i32()):
        r.i32()  # manual column widths
    r.string()  # locale
    r.i32()
    r.take(3)
    r.take(4 + 1 + 1)  # Y0
    for _ in range(r.i32()):
        r.string()
    blob = r.take(r.i32())
    if version == 3 and len(blob) > 10:
        l1 = struct.unpack("<I", blob[:4])[0]
        x1 = blob[4 : 4 + l1]
        if len(x1) > 5:
            show_vars, show_vals = x1[4], x1[5]
    # Dimensions
    dims = [_dimension(r, version) for _ in range(r.i32())]
    # Axes
    nl, nr, nc = r.i32(), r.i32(), r.i32()
    layers = [r.i32() for _ in range(nl)]
    rows = [r.i32() for _ in range(nr)]
    cols = [r.i32() for _ in range(nc)]
    # Cells
    cells: dict[int, Val] = {}
    for _ in range(r.i32()):
        idx = r.i64()
        if version == 1 and r.peek() == 0:
            r.u8()
        cells[idx] = _value(r, version)
    return LightTable(version, title, subtype, user_title, corner, caption, notes, dims,
                      layers, rows, cols, cells, show_vars, show_vals)

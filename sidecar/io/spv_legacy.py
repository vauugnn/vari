"""Legacy detail member binary (`*_chartData.bin`, old `*_tableData.bin`):
named sources of named variables, each a 1-D array of numbers/strings.
From the public SPV format documentation."""
from __future__ import annotations

import struct
from typing import Any

DBL_MAX_NEG = -1.7976931348623157e308


def _cstr(b: bytes) -> str:
    return b.split(b"\x00", 1)[0].decode("utf-8", errors="replace")


def parse_legacy(data: bytes) -> dict[str, dict[str, list[Any]]]:
    """Return {source-name: {variable-name: [values]}}; SYSMIS -> None, strings resolved."""
    if len(data) < 8 or data[0] != 0:
        raise ValueError("not a legacy binary member")
    version = data[1]
    n_sources = struct.unpack_from("<H", data, 2)[0]
    pos = 8
    metas = []
    for _ in range(n_sources):
        n_values, n_vars, offset = struct.unpack_from("<III", data, pos)
        pos += 12
        if version == 0xAF:
            name = _cstr(data[pos : pos + 28])
            pos += 28
        else:  # 0xB0: 64-byte name + int32
            name = _cstr(data[pos : pos + 64])
            pos += 68
        metas.append((name, n_values, n_vars, offset))
    out: dict[str, dict[str, list[Any]]] = {}
    end_of_numeric = pos
    for name, n_values, n_vars, offset in metas:
        p = offset
        vars_: dict[str, list[Any]] = {}
        for _ in range(n_vars):
            vname = _cstr(data[p : p + 288])
            p += 288
            vals = list(struct.unpack_from(f"<{n_values}d", data, p))
            p += 8 * n_values
            vars_[vname] = [None if v == DBL_MAX_NEG else v for v in vals]
        out[name] = vars_
        end_of_numeric = max(end_of_numeric, p)
    _apply_strings(data, end_of_numeric, out)
    return out


def _apply_strings(data: bytes, pos: int, out: dict[str, dict[str, list[Any]]]) -> None:
    if pos + 4 > len(data):
        return

    def i32() -> int:
        nonlocal pos
        v = struct.unpack_from("<i", data, pos)[0]
        pos += 4
        return v

    def string() -> str:
        nonlocal pos
        n = i32()
        s = data[pos : pos + n].decode("utf-8", errors="replace")
        pos += n
        return s

    try:
        maps = []
        for _ in range(i32()):
            src = string()
            vmaps = []
            for _ in range(i32()):
                vname = string()
                vmaps.append((vname, [(i32(), i32()) for _ in range(i32())]))
            maps.append((src, vmaps))
        labels = []
        for _ in range(i32()):
            i32()  # frequency
            labels.append(string())
    except (struct.error, IndexError):
        return
    for src, vmaps in maps:
        for vname, pairs in vmaps:
            col = out.get(src, {}).get(vname)
            if col is None:
                continue
            for vi, li in pairs:
                if vi < len(col) and li < len(labels):
                    col[vi] = labels[li]

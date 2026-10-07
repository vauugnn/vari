"""Output archives (.spv).

Reads IBM SPSS Statistics `.spv` files: a ZIP of viewer-structure XML
(`outputViewer*_heading.xml`) plus binary detail members. Implemented from the
publicly documented SPV format (GNU PSPP Developer's Guide). Vari's own older
JSON archive (`vari-output/output.json`) is still read for backward
compatibility; `write_spv` writes real IBM .spv (see spv_write.py).
"""
from __future__ import annotations

import base64
import html as _html
import json
import re
import struct
import zipfile
from typing import Any
from xml.etree import ElementTree as ET

from .spv_light import LightError, parse_light
from .spv_table import to_pivot_json

_MANIFEST = "vari-output/manifest.json"
_PAYLOAD = "vari-output/output.json"


def write_spv(items: list[dict[str, Any]], path: str) -> None:
    """Write an IBM SPSS-compatible .spv."""
    from .spv_write import write_ibm_spv

    write_ibm_spv(items, path)


def read_spv(path: str) -> list[dict[str, Any]]:
    """Read an output file. Damaged files raise ValueError with a plain message."""
    try:
        return _read(path)
    except (zipfile.BadZipFile, ET.ParseError, struct.error, KeyError, IndexError, UnicodeError,
            RecursionError, EOFError, LookupError) as e:
        raise ValueError(f"This output file is damaged or not a supported format ({type(e).__name__}).") from e


def _read(path: str) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path, "r") as z:
        names = z.namelist()
        if _PAYLOAD in names:
            data = json.loads(z.read(_PAYLOAD).decode("utf-8"))
            if not isinstance(data, list):
                raise ValueError("Corrupt output archive.")
            return data
        if not any(n.endswith("_heading.xml") or re.match(r"outputViewer\d+\.xml$", n) for n in names):
            raise ValueError("Not an output (.spv) file.")
        return _read_ibm(z)


# ---- IBM structure walk -----------------------------------------------
def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _structure_members(names: list[str]) -> list[str]:
    def key(n: str) -> int:
        return int(re.search(r"outputViewer(\d+)", n).group(1))  # type: ignore[union-attr]

    return sorted((n for n in names if re.match(r"outputViewer\d+(_heading)?\.xml$", n)), key=key)


def _read_ibm(z: zipfile.ZipFile) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for member in _structure_members(z.namelist()):
        try:
            root = ET.fromstring(z.read(member))
            _walk(root, z, out)
        except (ET.ParseError, zipfile.BadZipFile, KeyError, UnicodeError, LookupError) as e:
            # One damaged section must not make the whole file unreadable.
            out.append({"type": "Warning", "text": f"[Part of the file ({member}) is damaged and was skipped: {type(e).__name__}]"})
    if not out:
        raise ValueError("This output file contains nothing Vari can read.")
    return out


def _walk(el: ET.Element, z: zipfile.ZipFile, out: list[dict[str, Any]]) -> None:
    for child in el:
        tag = _local(child.tag)
        if tag == "heading":
            _walk(child, z, out)
        elif tag == "container":
            if child.get("visibility") == "hidden":
                continue
            for item in child:
                _item(item, z, out)


def _item(el: ET.Element, z: zipfile.ZipFile, out: list[dict[str, Any]]) -> None:
    tag = _local(el.tag)
    if tag == "text":
        txt = _html_text(el)
        if txt:
            kind = el.get("type", "text")
            out.append({"type": "Title" if kind in ("title", "page-title") else "TextBlock", "text": txt})
    elif tag == "table":
        member = _find_path(el, "dataPath")
        if member is None or member not in z.namelist():
            out.append({"type": "Warning", "text": "[Table data missing from file]"})
            return
        try:
            data = z.read(member)
            tbl = to_pivot_json(parse_light(data))
            tbl["spv"] = {"kind": "light", "data": base64.b64encode(data).decode()}
        except (LightError, IndexError, ValueError, struct.error, KeyError, UnicodeError, RecursionError, LookupError) as e:  # damaged table
            out.append({"type": "Warning", "text": f"[Table could not be read: {e}]"})
            return
        out.append(tbl)
    elif tag == "graph":
        from .spv_chart import chart_from_member  # imported lazily: pulls matplotlib

        try:
            res = chart_from_member(z, _find_path(el, "path"), _find_path(el, "dataPath"))
        except Exception as e:  # noqa: BLE001 - a bad chart must not sink the file
            res = {"type": "Warning", "text": f"[Chart could not be read: {type(e).__name__}]"}
        out.extend(res if isinstance(res, list) else [res])
    elif tag in ("object", "image"):
        member = el.get("uri") or _find_path(el, "dataPath")
        if member and member in z.namelist():
            out.append(_png_chart(z.read(member)))
        else:
            out.append({"type": "Warning", "text": "[Image missing from file]"})
    elif tag in ("model", "tree"):
        out.append({"type": "Warning", "text": f"[{tag} output is not supported]"})


def _find_path(el: ET.Element, which: str) -> str | None:
    for node in el.iter():
        if _local(node.tag) == which and node.text:
            return node.text.strip()
    return None


def _html_text(el: ET.Element) -> str:
    raw = ""
    for node in el.iter():
        if _local(node.tag) == "html":
            raw = "".join(node.itertext())
    if not raw:
        return ""
    raw = re.sub(r"(?is)<head>.*?</head>", "", raw)
    raw = re.sub(r"(?i)<br\s*/?>|</p>|</div>", "\n", raw)
    raw = re.sub(r"<[^>]+>", "", raw)
    return _html.unescape(raw).replace("\xa0", " ").strip()


def _png_chart(png: bytes) -> dict[str, Any]:
    """An embedded PNG, shown as a chart (an SVG wrapper around the image)."""
    import struct

    w, h = struct.unpack(">II", png[16:24]) if png[:8] == b"\x89PNG\r\n\x1a\n" else (600, 400)
    b64 = base64.b64encode(png).decode()
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'viewBox="0 0 {w} {h}" width="{w // 2}" height="{h // 2}">'
           f'<image width="{w}" height="{h}" xlink:href="data:image/png;base64,{b64}"/></svg>')
    return {"type": "Chart", "svg": svg, "png": b64}

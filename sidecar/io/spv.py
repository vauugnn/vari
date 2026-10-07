"""Output archives (.spv).

Reads IBM SPSS Statistics `.spv` files: a ZIP of viewer-structure XML
(`outputViewer*_heading.xml`) plus binary detail members. Implemented from the
publicly documented SPV format (GNU PSPP Developer's Guide). Vari's own older
JSON archive (`vari-output/output.json`) is still read for backward
compatibility; writing is `write_spv` (Vari JSON archive until the IBM writer
lands).
"""
from __future__ import annotations

import html as _html
import json
import re
import zipfile
from typing import Any
from xml.etree import ElementTree as ET

from .spv_light import LightError, parse_light
from .spv_table import to_pivot_json

_MANIFEST = "vari-output/manifest.json"
_PAYLOAD = "vari-output/output.json"


def write_spv(items: list[dict[str, Any]], path: str) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(_MANIFEST, json.dumps({"format": "vari-output", "version": 1}))
        z.writestr(_PAYLOAD, json.dumps(items))


def read_spv(path: str) -> list[dict[str, Any]]:
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
        root = ET.fromstring(z.read(member))
        _walk(root, z, out)
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
            tbl = to_pivot_json(parse_light(z.read(member)))
        except (LightError, IndexError, ValueError) as e:  # old-format or damaged table
            out.append({"type": "Warning", "text": f"[Table could not be read: {e}]"})
            return
        out.append(tbl)
    elif tag == "graph":
        from .spv_chart import chart_from_member  # imported lazily: pulls matplotlib

        out.append(chart_from_member(z, _find_path(el, "path"), _find_path(el, "dataPath")))
    elif tag in ("model", "object", "image", "tree"):
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

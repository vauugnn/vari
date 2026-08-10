"""Vari's output archive (.spv). IBM's .spv is a proprietary ZIP of XML; we
clone the *concept* with our own open format: a ZIP whose `output.json` holds the
serialized output-object tree. This round-trips Vari output — it does not read
IBM-authored .spv files.
"""
from __future__ import annotations

import json
import zipfile
from typing import Any

_MANIFEST = "vari-output/manifest.json"
_PAYLOAD = "vari-output/output.json"


def write_spv(items: list[dict[str, Any]], path: str) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(_MANIFEST, json.dumps({"format": "vari-output", "version": 1}))
        z.writestr(_PAYLOAD, json.dumps(items))


def read_spv(path: str) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path, "r") as z:
        names = set(z.namelist())
        if _PAYLOAD not in names:
            raise ValueError(
                "Not a Vari output archive. (IBM-authored .spv files are not supported.)"
            )
        data = json.loads(z.read(_PAYLOAD).decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError("Corrupt output archive.")
    return data

"""Charts inside IBM .spv files (rebuilt from chartData.bin + VizML)."""
from __future__ import annotations

import zipfile
from typing import Any, Optional


def chart_from_member(z: zipfile.ZipFile, xml_path: Optional[str], data_path: Optional[str]) -> dict[str, Any]:
    return {"type": "Warning", "text": "[Chart: not yet readable]"}

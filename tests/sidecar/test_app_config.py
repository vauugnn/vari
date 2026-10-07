"""App-shell invariants that broke silently before."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("window", ["dataeditor", "viewer", "syntax"])
def test_csp_allows_data_images_for_chart_export_and_spv_pictures(window):
    """Charts are rasterised through a data: URL image (PNG export, .spv charts) and SPSS-file
    pictures are inline data: images. A CSP that falls back to default-src 'self' blocks both."""
    html = (ROOT / "src" / "renderer" / window / "index.html").read_text()
    csp = next(ln for ln in html.splitlines() if "Content-Security-Policy" in ln)
    assert "img-src" in csp and "data:" in csp
    assert "script-src 'self'" in csp and "unsafe-eval" not in csp  # still locked down


def test_data_editor_toolbar_follows_spss_32_order():
    """Button order of the SPSS 32 Data Editor toolbar (from its published screenshot)."""
    import re

    src = (ROOT / "src/renderer/dataeditor/DataEditor.tsx").read_text()
    block = src[src.index("const tools: (Tool | 'sep')[] = ["): src.index("const hid = ")]
    ids = re.findall(r"id: '(\w+)'", block)
    spss32 = ["open", "save", "print", "recall", "undo", "redo", "gotocase", "gotovar", "variables", "descmu",
              "find", "insertcase", "insertvar", "valuelabels", "split", "select", "varsets", "showall"]
    assert ids[: len(spss32)] == spss32
    store = (ROOT / "src/renderer/state/store.ts").read_text()
    for extra in ("new", "weight", "syntax", "viewer"):  # not on SPSS 32's toolbar: hidden by default
        assert extra in ids[len(spss32):] and f"'{extra}'" in re.search(r"hiddenTools: \[(.*?)\]", store).group(1)

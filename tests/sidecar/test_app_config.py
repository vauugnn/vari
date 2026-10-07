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

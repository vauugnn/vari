"""IBM .spv reader. Real-file tests use SPSS's own sample files and are skipped
when SPSS is not installed (no IBM files are committed to the repo)."""
import glob
import os

import pytest

from sidecar.io.spv import read_spv
from sidecar.io.spv_light import Val, _expand

SAMPLES = glob.glob("/Applications/IBM SPSS Statistics/Resources/Samples/English/*.spv")
needs_spss = pytest.mark.skipif(not SAMPLES, reason="SPSS sample .spv files not installed")


def test_template_expansion_matches_documented_examples():
    a = lambda *x: [[Val(t) for t in x]]  # noqa: E731
    assert _expand("row % of ^1", a("Owns PDA")) == "row % of Owns PDA"
    assert _expand("[:^1:]1", a("a", "b")) == "ab"
    assert _expand("[%1:*^1:]1", a("X", "Y", "Z")) == "X*Y*Z"
    assert _expand("[%1 = %2:, ^1 = ^2:]1", a("X", "1", "Y", "2")) == "X = 1, Y = 2"


@needs_spss
def test_every_sample_reads_without_error():
    for f in SAMPLES:
        assert read_spv(f), os.path.basename(f)


@needs_spss
def test_frequency_table_structure_and_values():
    path = next(f for f in SAMPLES if f.endswith("viewertut.spv"))
    tables = {t["title"]: t for t in read_spv(path) if t["type"] == "PivotTable"}
    t = tables["Marital status"]["flat"]
    assert [h["t"] for h in t["colHeaders"][0]] == ["Frequency", "Percent", "Valid Percent", "Cumulative Percent"]
    assert t["rowHeaders"][0][0]["t"] == "Valid"          # group spans the value rows
    assert t["rowHeaders"][-1][0]["t"] == "Total"
    assert t["grid"][-1][1] == "100.0"                     # Total percent
    # Percent column sums to the Total row (within rounding).
    pct = [float(r[1]) for r in t["grid"][:-1]]
    assert abs(sum(pct) - 100.0) < 0.2


@needs_spss
def test_sample_bar_charts_rebuild_with_relabelled_categories():
    path = next(f for f in SAMPLES if f.endswith("msouttut.spv"))
    charts = [i for i in read_spv(path) if i["type"] == "Chart"]
    assert len(charts) == 2
    assert "Female" in charts[0]["svg"] and "Male" in charts[0]["svg"]
    assert "spv" in charts[0]  # original members kept for byte-exact re-save


def test_legacy_binary_roundtrip_of_numeric_source():
    import struct

    from sidecar.io.spv_legacy import parse_legacy

    name = b"source0".ljust(64, b"\0")
    var = b"X".ljust(288, b"\0") + struct.pack("<3d", 1.0, 2.0, -1.7976931348623157e308)
    head = b"\x00\xb0" + struct.pack("<H", 1) + struct.pack("<I", 8 + 12 + 68 + len(var))
    meta = struct.pack("<3I", 3, 1, 8 + 12 + 68) + name + struct.pack("<I", 0)
    got = parse_legacy(head + meta + var)
    assert got == {"source0": {"X": [1.0, 2.0, None]}}

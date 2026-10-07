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


def test_writer_sections_match_real_spss_layout():
    """Section sizes equal what SPSS writes; the fixed sections are byte-identical.
    (Font sizes/colours vary between SPSS versions, so Areas is compared by size.)"""
    import zipfile

    from sidecar.io import spv_write as w
    from sidecar.io.spv_light import parse_light

    path = next((f for f in SAMPLES if f.endswith("viewertut.spv")), None)
    if path is None:
        pytest.skip("SPSS samples not installed")
    b = zipfile.ZipFile(path).read("00000000013_lightTableData.bin")
    m = parse_light(b).marks
    assert len(b[m["areas"]:m["borders"]]) == len(w._areas())
    def border_set(blob: bytes) -> list[bytes]:  # order is unspecified by the format
        body = blob[4 + 4 + 4 : -4]
        return sorted(body[i : i + 12] for i in range(0, len(body), 12))

    real_b = b[m["borders"]:m["print"]]
    assert len(real_b) == len(w._borders())
    assert border_set(real_b) == border_set(w._borders())
    assert b[m["print"]:m["tablesettings"]] == w._print_settings()
    assert b[m["tablesettings"]:m["formats"]] == w._table_settings()


@needs_spss
def test_real_tables_survive_the_writer():
    import zipfile

    from sidecar.io.spv_light import parse_light
    from sidecar.io.spv_table import to_pivot_json
    from sidecar.io.spv_write import write_light

    for f in SAMPLES:
        z = zipfile.ZipFile(f)
        for name in z.namelist():
            if name.endswith("lightTableData.bin"):
                t = parse_light(z.read(name))
                again = parse_light(write_light(t, -1, "Frequencies"))
                assert to_pivot_json(t)["flat"] == to_pivot_json(again)["flat"], name


def test_vari_output_roundtrips_through_ibm_format(tmp_path):
    import zipfile

    from sidecar.io.spv import read_spv, write_spv
    from sidecar.output.model import Dimension, PivotTable

    t = PivotTable("Group Statistics", [Dimension("", ["Male", "Female"])],
                   [Dimension("", ["N", "Mean"])])
    t.set([0], [0], "10", "num")
    t.set([0], [1], "3.25", "num")
    t.set([1], [0], "12", "num")
    t.set([1], [1], ".500", "num")  # SPSS-style leading-zero-less value stays text
    items = [{"type": "Title", "text": "T-Test"}, t.to_json(),
             {"type": "TextBlock", "text": "T-TEST GROUPS=g(0 1)."}]
    p = str(tmp_path / "out.spv")
    write_spv(items, p)
    names = zipfile.ZipFile(p).namelist()
    assert names[-1] == "META-INF/MANIFEST.MF"
    back = read_spv(p)
    tbl = next(i for i in back if i["type"] == "PivotTable")
    assert tbl["title"] == "Group Statistics"
    assert tbl["flat"]["grid"] == [["10", "3.25"], ["12", ".500"]]
    assert [h["t"] for h in tbl["flat"]["colHeaders"][0]] == ["N", "Mean"]
    assert [h[0]["t"] for h in tbl["flat"]["rowHeaders"]] == ["Male", "Female"]


def test_damaged_files_fail_cleanly_never_crash(tmp_path):
    """Corrupt a Vari-written .spv hundreds of ways: every outcome is a result or ValueError."""
    import io
    import random
    import zipfile

    from sidecar.io.spv import read_spv, write_spv
    from sidecar.output.model import Dimension, PivotTable

    t = PivotTable("Group Statistics", [Dimension("", ["Male", "Female"])], [Dimension("", ["N", "Mean"])])
    for i in range(2):
        for j in range(2):
            t.set([i], [j], str(10 + i + j), "num")
    good = str(tmp_path / "good.spv")
    write_spv([{"type": "Title", "text": "T-Test"}, t.to_json(), {"type": "TextBlock", "text": "x"}], good)
    orig = zipfile.ZipFile(good)
    rng = random.Random(1)
    bad = str(tmp_path / "bad.spv")
    for _ in range(300):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for n in orig.namelist():
                data = bytearray(orig.read(n))
                if data and rng.random() < 0.6 and n != "META-INF/MANIFEST.MF":
                    kind = rng.choice(["flip", "trunc", "zero"])
                    if kind == "flip":
                        for _ in range(rng.randint(1, 6)):
                            data[rng.randrange(len(data))] = rng.randrange(256)
                    elif kind == "trunc":
                        data = data[: rng.randrange(len(data))]
                    else:
                        i = rng.randrange(len(data))
                        data[i : i + 8] = b"\x00" * 8
                z.writestr(n, bytes(data))
        open(bad, "wb").write(buf.getvalue())
        try:
            read_spv(bad)
        except ValueError:
            pass
    for blob in (b"", b"garbage", open(good, "rb").read()[:300]):
        open(bad, "wb").write(blob)
        with pytest.raises(ValueError):
            read_spv(bad)


def test_vari_chart_roundtrips_as_picture(tmp_path):
    import zipfile

    from sidecar.io.spv import read_spv, write_spv
    from sidecar.output import charts as ch

    chart = ch.bar_chart(["A", "B"], [3, 5], title="Demo", xlabel="Grp")
    p = str(tmp_path / "c.spv")
    write_spv([{"type": "Title", "text": "Graph"}, chart], p)
    z = zipfile.ZipFile(p)
    assert any(n.endswith("_Imagegeneric.png") for n in z.namelist())
    xml = z.read("outputViewer0000000000_heading.xml").decode()
    assert '<object commandName="Graph" type="unknown" uri="' in xml  # the form PSPP/SPSS use
    back = [i for i in read_spv(p) if i["type"] == "Chart"]
    assert len(back) == 1 and "data:image/png;base64" in back[0]["svg"]


def _freq_flat(values):
    import numpy as np
    import pandas as pd

    from sidecar.data.dataset import Dataset, DatasetRegistry
    from sidecar.data.format import Format
    from sidecar.data.variable import VariableMeta
    from sidecar.procedures.registry import build_registry
    from sidecar.syntax.registry import Context, execute_syntax

    reg = DatasetRegistry()
    reg.add(Dataset(pd.DataFrame({"a": np.array(values, float)}), [VariableMeta(name="a", print_format=Format("F", 8, 0))]))
    out = execute_syntax("FREQUENCIES VARIABLES=a.", build_registry(), Context(reg))
    return [o for o in out if o["type"] == "PivotTable"][-1]


def test_frequency_table_matches_spss_layout_without_missing():
    t = _freq_flat([11, 12, 12, 13])["flat"]
    labels = [[h["t"] for h in hs] for hs in t["rowHeaders"]]
    assert labels[0] == ["Valid", "11"]            # the Valid group spans the values
    assert labels[-1] == ["Total"] and len(labels) == 4  # a single Total, nothing else
    assert t["rowHeaders"][0][0]["rs"] == 4        # Valid covers values + its Total
    assert t["grid"][-1] == ["4", "100.0", "100.0", ""]


def test_frequency_table_adds_missing_group_and_grand_total():
    t = _freq_flat([11, 12, 12, float("nan")])["flat"]
    labels = [[h["t"] for h in hs] for hs in t["rowHeaders"]]
    assert labels == [["Valid", "11"], ["12"], ["Total"], ["Missing", "System"], ["Total"]]
    assert t["rowHeaders"][-1][0]["cs"] == 2       # grand Total spans both header columns


def test_grouped_frequency_table_keeps_its_groups_in_an_ibm_file(tmp_path):
    from sidecar.io.spv import read_spv, write_spv

    tbl = _freq_flat([11, 12, 12, float("nan")])
    p = str(tmp_path / "f.spv")
    write_spv([{"type": "Title", "text": "Frequencies"}, tbl], p)
    back = next(i for i in read_spv(p) if i["type"] == "PivotTable")
    assert back["flat"]["rowHeaders"] == tbl["flat"]["rowHeaders"]
    assert back["flat"]["grid"] == tbl["flat"]["grid"]


def test_significance_values_have_no_leading_zero_in_every_table():
    """SPSS prints .001 not 0.001 under any Sig. header — enforced in the table model."""
    from sidecar.output.model import Dimension, PivotTable

    t = PivotTable("T", [Dimension("", ["A", "Sig. (2-tailed)"])], [Dimension("", ["Value", "Sig."])])
    for i in range(2):
        for j in range(2):
            t.set([i], [j], "0.012")
    cells = {(tuple(c["r"]), tuple(c["c"])): c["v"] for c in t.to_json()["cells"]}
    assert cells[((0,), (0,))] == "0.012"            # plain statistic keeps its zero
    assert cells[((0,), (1,))] == ".012"             # under a Sig. column
    assert cells[((1,), (0,))] == ".012"             # in a Sig. row
    r = PivotTable("R", [Dimension("", ["x"])], [Dimension("", ["F"])])
    r.set_columns(["Levene Sig.", "Design"])
    r.set([0], [0], "0.300")
    r.set([0], [1], "0.300")
    got = {tuple(c["c"]): c["v"] for c in r.to_json()["cells"]}
    assert got[(0,)] == ".300" and got[(1,)] == "0.300"   # "Design" is not "Sig"

"""`.sav` metadata + user-missing round trips (PHASE-1 sections 3, 5)."""
import numpy as np
import pandas as pd

from sidecar.data.format import Format
from sidecar.data.variable import VariableMeta
from sidecar.data.dataset import Dataset
from sidecar.io.files import open_file, save_file


def test_reads_metadata(sav_path):
    ds = open_file(sav_path)
    by_name = {v.name: v for v in ds.variables}

    assert by_name["gender"].label == "Gender"
    assert by_name["gender"].value_labels[1.0] == "Male"
    assert by_name["gender"].value_labels[9.0] == "No answer"
    assert by_name["gender"].measure == "nominal"
    assert by_name["agree"].measure == "ordinal"
    assert by_name["sname"].is_string
    assert by_name["id"].print_format.type == "F"


def test_reads_missing_definitions(sav_path):
    ds = open_file(sav_path)
    by_name = {v.name: v for v in ds.variables}

    assert by_name["gender"].missing.kind == "discrete"
    assert 9.0 in by_name["gender"].missing.values

    inc = by_name["income"].missing
    assert inc.kind == "range"
    assert inc.lo == 999998.0 and inc.hi == 999999.0


def test_user_missing_values_stay_real(sav_path):
    ds = open_file(sav_path)
    # 9 (gender) and 999999 (income) are user-missing but must remain as values.
    assert ds.df.loc[3, "gender"] == 9.0
    assert ds.df.loc[2, "income"] == 999999.0
    assert not np.isnan(ds.df.loc[3, "gender"])


def test_round_trip_preserves_user_missing_codes(sav_path, tmp_path):
    ds = open_file(sav_path)
    out = str(tmp_path / "rt.sav")
    save_file(ds, out)
    ds2 = open_file(out)

    pd.testing.assert_series_equal(
        ds.df["gender"], ds2.df["gender"], check_names=False
    )
    pd.testing.assert_series_equal(
        ds.df["income"], ds2.df["income"], check_names=False
    )
    # value labels + missing survive
    g2 = {v.name: v for v in ds2.variables}["gender"]
    assert g2.value_labels[9.0] == "No answer"
    assert g2.missing.kind == "discrete" and 9.0 in g2.missing.values


def test_add_variable_metadata_round_trip(tmp_path, sav_path):
    ds = open_file(sav_path)
    meta = VariableMeta(
        name="newvar",
        print_format=Format("F", 8, 0),
        label="A new one",
        value_labels={1.0: "yes", 0.0: "no"},
        measure="nominal",
    )
    ds.append_variable(meta)
    ds.df.loc[:, "newvar"] = [1.0, 0.0, 1.0, 0.0]

    out = str(tmp_path / "added.sav")
    save_file(ds, out)
    ds2 = open_file(out)
    nv = {v.name: v for v in ds2.variables}["newvar"]
    assert nv.label == "A new one"
    assert nv.value_labels[1.0] == "yes"
    assert nv.measure == "nominal"


def test_edit_cell_persists(tmp_path, sav_path):
    ds = open_file(sav_path)
    ds.set_cell(0, list(v.name for v in ds.variables).index("income"), "70000")
    out = str(tmp_path / "edited.sav")
    save_file(ds, out)
    ds2 = open_file(out)
    assert ds2.df.loc[0, "income"] == 70000.0

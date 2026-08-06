"""Dataset structural edits, windowed reads, value-label rendering."""
import numpy as np
import pandas as pd
import pytest

from sidecar.data.dataset import Dataset
from sidecar.data.format import Format
from sidecar.data.variable import NameError_, VariableMeta


def _ds():
    df = pd.DataFrame({"g": [1.0, 2.0, np.nan], "s": ["a", "b", "c"]})
    variables = [
        VariableMeta(name="g", print_format=Format("F", 8, 0), value_labels={1.0: "Male", 2.0: "Female"}),
        VariableMeta(name="s", print_format=Format("A", 8)),
    ]
    return Dataset(df, variables)


def test_get_rows_formats_and_sysmis():
    ds = _ds()
    rows = ds.get_rows(0, 10)
    assert rows[0] == ["1", "a"]
    assert rows[2][0] == "."      # system-missing numeric -> "."


def test_get_rows_value_labels():
    ds = _ds()
    rows = ds.get_rows(0, 10, value_labels=True)
    assert rows[0][0] == "Male"
    assert rows[1][0] == "Female"


def test_get_rows_window():
    ds = _ds()
    assert ds.get_rows(1, 1) == [["2", "b"]]


def test_set_cell_parses_numeric():
    ds = _ds()
    ds.set_cell(2, 0, "5")
    assert ds.df.iat[2, 0] == 5.0


def test_append_empty_variable_names_var00001():
    ds = _ds()
    meta = ds.append_empty_variable()
    assert meta.name == "VAR00003"  # two existing vars -> next is 3
    assert meta.print_format.to_spss() == "F8.2"


def test_insert_delete_case():
    ds = _ds()
    ds.insert_case(1)
    assert ds.n_rows == 4
    ds.delete_case(1)
    assert ds.n_rows == 3


def test_rename_rejects_reserved():
    ds = _ds()
    with pytest.raises(NameError_):
        ds.rename_variable(0, "BY")


def test_rename_rejects_duplicate():
    ds = _ds()
    with pytest.raises(NameError_):
        ds.rename_variable(0, "s")


def test_delete_variable_updates_both():
    ds = _ds()
    ds.delete_variable(0)
    assert ds.n_vars == 1
    assert list(ds.df.columns) == ["s"]


def test_snapshot_is_independent():
    ds = _ds()
    snap = ds.snapshot()
    ds.set_cell(0, 0, "99")
    assert snap.df.iat[0, 0] == 1.0  # unchanged

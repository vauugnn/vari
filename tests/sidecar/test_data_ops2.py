"""AGGREGATE, FLIP, ADD FILES, MATCH FILES."""
import numpy as np
import pandas as pd
import pyreadstat

from sidecar.data.dataset import Dataset, DatasetRegistry
from sidecar.data.format import Format
from sidecar.data.variable import VariableMeta
from sidecar.procedures.registry import build_registry
from sidecar.syntax.registry import Context, execute_syntax


def make(df):
    reg = DatasetRegistry()
    reg.add(Dataset(df.copy(), [VariableMeta(name=c, print_format=Format("F", 8, 2)) for c in df.columns]))
    return reg


def run(reg, text):
    return execute_syntax(text, build_registry(), Context(reg))


def test_aggregate():
    reg = make(pd.DataFrame({"g": [1.0, 1, 2, 2], "x": [10.0, 20, 30, 50]}))
    run(reg, "AGGREGATE /OUTFILE=* /BREAK=g /mx=MEAN(x) /n=N.")
    ds = reg.active
    assert list(ds.df["g"]) == [1.0, 2.0]
    assert list(ds.df["mx"]) == [15.0, 40.0]
    assert list(ds.df["n"]) == [2, 2]


def test_flip_transpose():
    reg = make(pd.DataFrame({"a": [1.0, 2, 3], "b": [4.0, 5, 6]}))
    run(reg, "FLIP VARIABLES=a b.")
    ds = reg.active
    assert list(ds.df["CASE_LBL"]) == ["a", "b"]
    assert ds.n_rows == 2 and ds.n_vars == 4  # CASE_LBL + 3 cases


def test_add_files(tmp_path):
    p = str(tmp_path / "more.sav")
    pyreadstat.write_sav(pd.DataFrame({"x": [7.0, 8.0]}), p)
    reg = make(pd.DataFrame({"x": [1.0, 2.0]}))
    run(reg, f"ADD FILES /FILE=* /FILE='{p}'.")
    assert list(reg.active.df["x"]) == [1.0, 2.0, 7.0, 8.0]


def test_match_files(tmp_path):
    p = str(tmp_path / "lookup.sav")
    pyreadstat.write_sav(pd.DataFrame({"id": [1.0, 2.0], "grp": [10.0, 20.0]}), p)
    reg = make(pd.DataFrame({"id": [1.0, 2.0], "x": [5.0, 6.0]}))
    run(reg, f"MATCH FILES /FILE=* /FILE='{p}' /BY id.")
    ds = reg.active
    assert "grp" in [v.name for v in ds.variables]
    assert list(ds.df["grp"]) == [10.0, 20.0]

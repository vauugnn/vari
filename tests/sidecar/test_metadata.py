"""Metadata syntax commands + RANK/AUTORECODE/RMV."""
import numpy as np
import pandas as pd

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


def meta(reg, name):
    ds = reg.active
    return ds.variables[ds._index_of(name)]


def test_variable_labels():
    reg = make(pd.DataFrame({"age": [1.0], "sex": [1.0]}))
    run(reg, "VARIABLE LABELS age 'Age in years' sex 'Gender'.")
    assert meta(reg, "age").label == "Age in years"
    assert meta(reg, "sex").label == "Gender"


def test_value_labels():
    reg = make(pd.DataFrame({"sex": [1.0, 2.0]}))
    run(reg, "VALUE LABELS sex 1 'Male' 2 'Female'.")
    assert meta(reg, "sex").value_labels[1.0] == "Male"
    assert meta(reg, "sex").value_labels[2.0] == "Female"


def test_missing_values():
    reg = make(pd.DataFrame({"q": [1.0, 9.0]}))
    run(reg, "MISSING VALUES q (9).")
    assert meta(reg, "q").missing.kind == "discrete"
    run(reg, "MISSING VALUES q (1 THRU 5).")
    assert meta(reg, "q").missing.kind == "range"


def test_rename_and_formats():
    reg = make(pd.DataFrame({"old": [1.0]}))
    run(reg, "RENAME VARIABLES (old=new).")
    assert "new" in [v.name for v in reg.active.variables]
    run(reg, "FORMATS new (F8.0).")
    assert meta(reg, "new").print_format.to_spss() == "F8"


def test_rank():
    reg = make(pd.DataFrame({"x": [10.0, 30, 20]}))
    run(reg, "RANK VARIABLES=x.")
    assert list(reg.active.df["Rx"]) == [1.0, 3.0, 2.0]


def test_autorecode():
    reg = make(pd.DataFrame({"g": [5.0, 9, 5, 9]}))
    run(reg, "AUTORECODE VARIABLES=g /INTO gr.")
    assert list(reg.active.df["gr"]) == [1.0, 2.0, 1.0, 2.0]


def test_rmv_smean():
    reg = make(pd.DataFrame({"x": [2.0, np.nan, 4.0]}))
    run(reg, "RMV newx=SMEAN(x).")
    assert list(reg.active.df["newx"]) == [2.0, 3.0, 4.0]

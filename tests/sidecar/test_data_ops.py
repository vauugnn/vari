"""SORT CASES, SELECT IF, FILTER, SPLIT FILE, WEIGHT (Data menu)."""
import numpy as np
import pandas as pd

from sidecar.data.dataset import Dataset, DatasetRegistry
from sidecar.data.format import Format
from sidecar.data.variable import VariableMeta
from sidecar.procedures.registry import build_registry
from sidecar.syntax.registry import Context, execute_syntax


def make(df):
    variables = [VariableMeta(name=c, print_format=Format("F", 8, 2)) for c in df.columns]
    reg = DatasetRegistry()
    reg.add(Dataset(df.copy(), variables))
    return reg


def run(reg, text):
    return execute_syntax(text, build_registry(), Context(reg))


def tables(out):
    return [o for o in out if o["type"] == "PivotTable"]


def test_sort_cases():
    reg = make(pd.DataFrame({"x": [3.0, 1, 2]}))
    run(reg, "SORT CASES BY x (A).")
    assert list(reg.active.df["x"]) == [1, 2, 3]
    run(reg, "SORT CASES BY x (D).")
    assert list(reg.active.df["x"]) == [3, 2, 1]


def test_select_if_deletes_rows():
    reg = make(pd.DataFrame({"x": [1.0, 5, 9, 2]}))
    run(reg, "SELECT IF (x > 3).")
    assert list(reg.active.df["x"]) == [5, 9]


def test_filter_excludes_from_procedure():
    reg = make(pd.DataFrame({"g": [1.0, 1, 2, 2], "f": [1.0, 0, 1, 1]}))
    run(reg, "FILTER BY f.")
    # frequency of g should exclude the filtered-out row (f=0)
    out = run(reg, "FREQUENCIES VARIABLES=g.")
    freq = tables(out)[1]
    cats = freq["rowDims"][0]["categories"]
    cells = {(tuple(c["r"]), tuple(c["c"])): c["v"] for c in freq["cells"]}
    # 3 valid cases after filter (rows 0,2,3): g=1 once, g=2 twice
    assert cells[((cats.index("Total"),), (0,))] in ("3", "3.00")


def test_split_file_runs_per_group():
    reg = make(pd.DataFrame({"g": [1.0, 1, 2, 2, 2], "y": [10.0, 20, 5, 7, 9]}))
    run(reg, "SPLIT FILE BY g.")
    out = run(reg, "DESCRIPTIVES VARIABLES=y.")
    headings = [o for o in out if o["type"] == "TextBlock" and o["text"].startswith("Split File group")]
    assert len(headings) == 2  # one per group
    assert len(tables(out)) == 2


def test_split_file_off():
    reg = make(pd.DataFrame({"g": [1.0, 2], "y": [1.0, 2]}))
    run(reg, "SPLIT FILE BY g.")
    run(reg, "SPLIT FILE OFF.")
    assert reg.active.split_vars == []


def test_weight_state_set():
    reg = make(pd.DataFrame({"w": [1.0, 2, 3]}))
    run(reg, "WEIGHT BY w.")
    assert reg.active.weight_var == "w"
    run(reg, "WEIGHT OFF.")
    assert reg.active.weight_var is None

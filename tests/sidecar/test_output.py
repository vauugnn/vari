"""Output document model: PivotTable.to_json + simple_table (PHASE-2)."""
from sidecar.data.format import Format
from sidecar.output.model import Dimension, PivotTable, simple_table
from sidecar.server import dispatch


def test_simple_table_shapes_and_formats():
    t = simple_table(
        "Descriptive Statistics",
        ["age", "income"],
        ["N", "Mean"],
        [[400, 38.42], [400, 51873.25]],
        col_formats=[Format("F", 8, 0), Format("F", 8, 2)],
    )
    j = t.to_json()
    assert j["type"] == "PivotTable"
    assert j["rowDims"][0]["categories"] == ["age", "income"]
    assert j["colDims"][0]["categories"] == ["N", "Mean"]
    cells = {(tuple(c["r"]), tuple(c["c"])): c["v"] for c in j["cells"]}
    assert cells[((0,), (0,))] == "400"
    assert cells[((0,), (1,))] == "38.42"


def test_nested_columns_json():
    t = PivotTable(
        "CT",
        row_dims=[Dimension("Agreement", ["Agree", "Disagree"])],
        col_dims=[Dimension("Gender", ["Male", "Female"]), Dimension("", ["Count", "Expected"])],
    )
    t.set([0], [1, 0], "70", "num")
    j = t.to_json()
    assert len(j["colDims"]) == 2
    assert j["cells"][0]["c"] == [1, 0]


def test_pivotdemo_command():
    resp = dispatch({"jsonrpc": "2.0", "id": 1, "method": "syntax.execute", "params": {"text": "PIVOTDEMO."}})
    objs = resp["result"]
    types = [o["type"] for o in objs]
    assert types == ["Title", "PivotTable", "PivotTable"]
    assert objs[1]["title"] == "Descriptive Statistics"
    assert len(objs[2]["colDims"]) == 2  # nested

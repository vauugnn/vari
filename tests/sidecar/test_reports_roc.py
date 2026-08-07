"""ROC, CURVEFIT, SUMMARIZE, CODEBOOK, GRAPH line/area/errorbar."""
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


def errs(out):
    return [o for o in out if o["type"] == "Error"]


def tables(out):
    return [o for o in out if o["type"] == "PivotTable"]


def test_roc():
    rng = np.random.RandomState(1)
    state = np.array([0.0] * 50 + [1.0] * 50)
    score = np.concatenate([rng.normal(0, 1, 50), rng.normal(1.5, 1, 50)])
    reg = make(pd.DataFrame({"score": score, "state": state}))
    out = run(reg, "ROC score BY state(1) /PLOT=CURVE.")
    assert not errs(out), errs(out)
    assert any(t["title"] == "Area Under the Curve" for t in tables(out))
    assert any(o["type"] == "Chart" for o in out)


def test_curvefit():
    rng = np.random.RandomState(2)
    x = np.linspace(1, 10, 50)
    y = 2 + 3 * x + rng.normal(0, 1, 50)
    reg = make(pd.DataFrame({"y": y, "x": x}))
    out = run(reg, "CURVEFIT VARIABLES=y WITH x /MODEL=LINEAR QUADRATIC.")
    assert not errs(out), errs(out)
    t = tables(out)[0]
    assert t["rowDims"][0]["categories"] == ["Linear", "Quadratic"]


def test_summarize_and_codebook():
    reg = make(pd.DataFrame({"y": [1.0, 2, 3, 4], "g": [1.0, 1, 2, 2]}))
    assert not errs(run(reg, "SUMMARIZE /TABLES=y BY g."))
    reg2 = make(pd.DataFrame({"y": [1.0, 2, 3]}))
    assert not errs(run(reg2, "CODEBOOK y."))


def test_graph_line_area_errorbar():
    reg = make(pd.DataFrame({"y": [1.0, 2, 3, 4, 5, 6], "g": [1.0, 1, 2, 2, 3, 3]}))
    for cmd in ["GRAPH /LINE(SIMPLE)=MEAN(y) BY g.", "GRAPH /AREA(SIMPLE)=MEAN(y) BY g.", "GRAPH /ERRORBAR(SIMPLE)=MEAN(y) BY g."]:
        out = run(reg, cmd)
        assert not errs(out), (cmd, errs(out))
        assert any(o["type"] == "Chart" for o in out), cmd

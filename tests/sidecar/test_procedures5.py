"""EXAMINE (Explore) + PARTIAL CORR."""
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


def types(out):
    return [o["type"] for o in out]


def test_examine_emits_descriptives_normality_boxplot():
    rng = np.random.RandomState(1)
    reg = make(pd.DataFrame({"y": rng.normal(50, 10, 60)}))
    out = run(reg, "EXAMINE VARIABLES=y /PLOT BOXPLOT /STATISTICS DESCRIPTIVES.")
    titles = [o.get("title") for o in out if o["type"] == "PivotTable"]
    assert "Tests of Normality" in titles
    assert any(o["type"] == "Chart" for o in out)


def test_partial_corr_matches_pingouin():
    rng = np.random.RandomState(2)
    z = rng.normal(0, 1, 100)
    x = z + rng.normal(0, 1, 100)
    y = z + rng.normal(0, 1, 100)
    reg = make(pd.DataFrame({"x": x, "y": y, "z": z}))
    out = run(reg, "PARTIAL CORR /VARIABLES=x y BY z.")
    t = [o for o in out if o["type"] == "PivotTable"][0]
    cells = {(tuple(c["r"]), tuple(c["c"])): c["v"] for c in t["cells"]}
    import pingouin as pg

    expected = pg.partial_corr(data=pd.DataFrame({"x": x, "y": y, "z": z}), x="x", y="y", covar=["z"])["r"].iloc[0]
    got = float(cells[((0, 0), (1,))].replace(".", "0.", 1) if cells[((0, 0), (1,))].startswith(".") else cells[((0, 0), (1,))])
    assert abs(got - expected) < 0.01

"""UNIANOVA (GLM) + FACTOR."""
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


def tables(out):
    return [o for o in out if o["type"] == "PivotTable"]


def cells(t):
    return {(tuple(c["r"]), tuple(c["c"])): c["v"] for c in t["cells"]}


def test_unianova_matches_statsmodels():
    rng = np.random.RandomState(5)
    a = rng.randint(1, 3, 60).astype(float)
    b = rng.randint(1, 4, 60).astype(float)
    y = 2 * a + b + rng.normal(0, 1, 60)
    reg = make(pd.DataFrame({"y": y, "a": a, "b": b}))
    out = run(reg, "UNIANOVA y BY a b.")
    eff = [t for t in tables(out) if t["title"].startswith("Tests of Between")][0]
    rows = eff["rowDims"][0]["categories"]
    assert "Corrected Model" in rows and "Error" in rows and "a" in rows
    # F for factor a should be positive and finite
    c = cells(eff)
    ia = rows.index("a")
    assert float(c[((ia,), (3,))]) > 0


def test_factor_kmo_and_components():
    rng = np.random.RandomState(6)
    latent = rng.normal(0, 1, 200)
    df = pd.DataFrame({f"q{i}": latent + rng.normal(0, 0.6, 200) for i in range(1, 6)})
    reg = make(df)
    out = run(reg, "FACTOR /VARIABLES=q1 q2 q3 q4 q5 /EXTRACTION PC /ROTATION VARIMAX.")
    titles = [t["title"] for t in tables(out)]
    assert "KMO and Bartlett's Test" in titles
    assert "Total Variance Explained" in titles
    assert "Component Matrix" in titles
    # one strong factor -> first eigenvalue > 1
    tve = [t for t in tables(out) if t["title"] == "Total Variance Explained"][0]
    assert float(cells(tve)[((0,), (0,))]) > 1

"""K-Means, hierarchical cluster, discriminant."""
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


def errs(out):
    return [o for o in out if o["type"] == "Error"]


def test_kmeans():
    rng = np.random.RandomState(1)
    a = np.vstack([rng.normal(0, 0.5, (30, 2)), rng.normal(5, 0.5, (30, 2))])
    reg = make(pd.DataFrame({"x": a[:, 0], "y": a[:, 1]}))
    out = run(reg, "QUICK CLUSTER x y /CRITERIA CLUSTERS(2).")
    assert not errs(out), errs(out)
    assert any(t["title"] == "Final Cluster Centers" for t in tables(out))


def test_hierarchical():
    rng = np.random.RandomState(2)
    reg = make(pd.DataFrame({"x": rng.normal(0, 1, 15), "y": rng.normal(0, 1, 15)}))
    out = run(reg, "CLUSTER x y /METHOD WARD.")
    assert not errs(out), errs(out)
    assert tables(out)[0]["title"] == "Agglomeration Schedule"


def test_discriminant():
    rng = np.random.RandomState(3)
    x = np.concatenate([rng.normal(0, 1, 40), rng.normal(3, 1, 40)])
    g = np.array([1.0] * 40 + [2.0] * 40)
    reg = make(pd.DataFrame({"g": g, "x": x}))
    out = run(reg, "DISCRIMINANT /GROUPS=g(1 2) /VARIABLES=x.")
    assert not errs(out), errs(out)
    assert any(t["title"] == "Classification Results" for t in tables(out))

"""Wave 5: TwoStep, KNN, Correspondence, MDS, Neural nets."""
import numpy as np
import pandas as pd

from sidecar.data.dataset import Dataset, DatasetRegistry
from sidecar.data.format import Format
from sidecar.data.variable import VariableMeta
from sidecar.procedures.registry import build_registry
from sidecar.syntax.registry import Context, execute_syntax


def _ctx(df):
    reg = build_registry()
    dr = DatasetRegistry()
    dr.add(Dataset(df, [VariableMeta(name=c, print_format=Format("F", 8, 2)) for c in df.columns]), activate=True)
    return reg, Context(dr)


def _col(pt, col):
    return [float(c["v"]) for c in sorted(pt["cells"], key=lambda x: x["r"][0]) if c["c"] == [col]]


def _pt(out, i=0):
    return [o for o in out if o["type"] == "PivotTable"][i]


def test_correspondence_total_inertia_equals_chi2_over_n():
    np.random.seed(11)
    n = 400
    row = np.random.randint(1, 4, n).astype(float)
    col = ((row + np.random.randint(0, 3, n)) % 3 + 1).astype(float)
    df = pd.DataFrame({"row": row, "col": col})
    reg, ctx = _ctx(df)
    out = execute_syntax("CORRESPONDENCE TABLE=row BY col.", reg, ctx)
    pt = _pt(out)
    total_inertia = sum(_col(pt, 1))
    ct = pd.crosstab(df["row"], df["col"]).to_numpy(float)
    from scipy.stats import chi2_contingency
    chi2 = chi2_contingency(ct)[0]
    assert abs(total_inertia - chi2 / ct.sum()) < 1e-3


def test_twostep_produces_requested_clusters():
    np.random.seed(11)
    n = 150
    g = np.random.randint(0, 3, n)
    df = pd.DataFrame({"x1": np.random.randn(n) + g * 3, "x2": np.random.randn(n) + g * 3})
    reg, ctx = _ctx(df)
    out = execute_syntax("TWOSTEP x1 x2.", reg, ctx)
    pt = _pt(out)
    # last row is "Combined"; cluster rows before it
    ns = _col(pt, 0)
    assert ns[-1] == sum(ns[:-1])


def test_knn_beats_chance():
    np.random.seed(11)
    n = 200
    g = np.random.randint(0, 2, n)
    df = pd.DataFrame({"g": g.astype(float), "x1": np.random.randn(n) + g * 2, "x2": np.random.randn(n) + g * 2})
    reg, ctx = _ctx(df)
    out = execute_syntax("KNN g BY x1 x2 /K 5.", reg, ctx)
    pt = _pt(out)
    overall = _col(pt, 2)[-1]  # overall percent correct
    assert overall > 60.0


def test_mds_runs_and_reports_stress():
    np.random.seed(11)
    df = pd.DataFrame({"a": np.random.randn(30), "b": np.random.randn(30), "c": np.random.randn(30)})
    reg, ctx = _ctx(df)
    out = execute_syntax("PROXSCAL a b c /DIMENSIONS 2.", reg, ctx)
    pt = _pt(out)
    stress1 = _col(pt, 0)[1]
    assert 0.0 <= stress1 <= 1.0

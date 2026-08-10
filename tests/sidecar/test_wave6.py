"""Wave 6: OLAP, Custom Tables, Multiple Response, Control charts, Bayesian."""
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


def test_olap_total_mean_matches_pandas():
    np.random.seed(13)
    n = 200
    g = np.random.randint(1, 4, n).astype(float)
    y = np.random.randn(n) + g
    df = pd.DataFrame({"y": y, "g": g})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("OLAP y BY g.", reg, ctx))
    total_mean = _col(pt, 1)[-1]
    assert abs(total_mean - y.mean()) < 1e-2


def test_multiresponse_counts():
    np.random.seed(13)
    n = 100
    d1 = np.random.randint(0, 2, n).astype(float)
    d2 = np.random.randint(0, 2, n).astype(float)
    df = pd.DataFrame({"d1": d1, "d2": d2})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("MULTRESPONSE /FREQUENCIES d1 d2 /VALUE=1.", reg, ctx))
    counts = _col(pt, 0)
    assert counts[0] == float(int(d1.sum())) and counts[1] == float(int(d2.sum()))


def test_bayes_normal_posterior_mean_is_sample_mean():
    np.random.seed(13)
    x = np.random.randn(120) + 3.0
    df = pd.DataFrame({"x": x})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("BAYES x /TEST TYPE=NORMAL.", reg, ctx))
    assert abs(_col(pt, 0)[0] - x.mean()) < 1e-3


def test_bayes_binomial_proportion():
    np.random.seed(13)
    x = np.random.binomial(1, 0.35, 200).astype(float)
    df = pd.DataFrame({"x": x})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("BAYES x /TEST TYPE=BINOMIAL.", reg, ctx))
    k = x.sum(); n = len(x)
    post = (1 + k) / (2 + n)  # Beta(1,1) posterior mean
    assert abs(_col(pt, 0)[0] - post) < 1e-3


def test_control_chart_renders():
    np.random.seed(13)
    df = pd.DataFrame({"y": np.random.randn(50) + 10})
    reg, ctx = _ctx(df)
    out = execute_syntax("SPCHART y /TYPE=I.", reg, ctx)
    assert any(o.get("type") == "Chart" and "<svg" in o.get("svg", "") for o in out)

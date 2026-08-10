"""Wave 2b: Probit, PLS, 2SLS, Variance Components, Repeated Measures parity."""
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


def _pt(out):
    return [o for o in out if o["type"] == "PivotTable"][0]


def test_probit_matches_statsmodels():
    np.random.seed(2)
    n = 200
    x = np.random.randn(n)
    y = (x + np.random.randn(n) * 0.5 > 0).astype(float)
    df = pd.DataFrame({"y": y, "x": x})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("PROBIT y WITH x.", reg, ctx))
    import statsmodels.api as sm
    m = sm.Probit(y, sm.add_constant(x.reshape(-1, 1))).fit(disp=0)
    b = _col(pt, 0)
    assert abs(b[0] - m.params[0]) < 1e-2 and abs(b[1] - m.params[1]) < 1e-2


def test_tsls_matches_two_stage_ols():
    np.random.seed(2)
    n = 150
    z = np.random.randn(n); x2 = np.random.randn(n)
    xend = 0.6 * z + 0.4 * np.random.randn(n)
    y = 1.0 + 0.8 * xend + 0.5 * x2 + np.random.randn(n) * 0.5
    df = pd.DataFrame({"y": y, "xend": xend, "x2": x2, "z": z})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("2SLS y WITH xend x2 /INSTRUMENTS z x2.", reg, ctx))
    import statsmodels.api as sm
    xh = sm.OLS(xend, sm.add_constant(np.column_stack([z, x2]))).fit().fittedvalues
    b = sm.OLS(y, sm.add_constant(np.column_stack([xh, x2]))).fit().params
    got = _col(pt, 0)
    assert np.allclose(got, b, atol=1e-2)


def test_varcomp_positive_components():
    np.random.seed(2)
    n = 200
    g = np.random.randint(1, 6, n)
    y = g * 2.0 + np.random.randn(n)
    df = pd.DataFrame({"y": y.astype(float), "g": g.astype(float)})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("VARCOMP y BY g /RANDOM=g.", reg, ctx))
    est = _col(pt, 0)
    assert est[0] > 0 and est[1] > 0  # between-group and residual variance


def test_repeated_measures_matches_anovarm():
    np.random.seed(2)
    n = 40
    df = pd.DataFrame({"t1": np.random.randn(n), "t2": np.random.randn(n) + 0.5, "t3": np.random.randn(n) + 1.0})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("GLMRM t1 t2 t3 /WSFACTOR time 3.", reg, ctx))
    from statsmodels.stats.anova import AnovaRM
    d = df.copy(); d["s"] = np.arange(n)
    long = d.melt(id_vars="s", value_vars=["t1", "t2", "t3"], var_name="time", value_name="y")
    f = float(AnovaRM(long, "y", "s", within=["time"]).fit().anova_table.loc["time", "F Value"])
    got = _col(pt, 0)[0]
    assert abs(got - f) < 1e-2

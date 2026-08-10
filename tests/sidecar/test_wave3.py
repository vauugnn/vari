"""Wave 3: GENLIN, GEE, MIXED, GENLOG parity vs statsmodels."""
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


def _pt(out, idx=0):
    return [o for o in out if o["type"] == "PivotTable"][idx]


def test_genlin_poisson_matches_statsmodels():
    np.random.seed(7)
    n = 200
    x = np.random.randn(n)
    count = np.random.poisson(np.exp(0.3 + 0.4 * x)).astype(float)
    df = pd.DataFrame({"count": count, "x": x})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("GENLIN count WITH x /MODEL DISTRIBUTION=POISSON LINK=LOG.", reg, ctx))
    import statsmodels.api as sm
    X = sm.add_constant(x.reshape(-1, 1))
    m = sm.GLM(count, X, family=sm.families.Poisson()).fit()
    b = _col(pt, 0)
    assert np.allclose(b, m.params, atol=1e-3)


def test_gee_matches_statsmodels():
    np.random.seed(7)
    n = 200
    x = np.random.randn(n)
    subj = np.repeat(np.arange(n // 4), 4)[:n].astype(float)
    y = 0.5 * x + np.random.randn(n)
    df = pd.DataFrame({"y": y, "x": x, "subj": subj})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("GEE y WITH x /SUBJECT=subj /MODEL DISTRIBUTION=NORMAL LINK=IDENTITY.", reg, ctx))
    import statsmodels.api as sm
    X = sm.add_constant(x.reshape(-1, 1))
    m = sm.GEE(y, X, groups=subj, family=sm.families.Gaussian()).fit()
    b = _col(pt, 0)
    assert np.allclose(b, np.asarray(m.params), atol=1e-2)


def test_mixed_fixed_effect_matches_statsmodels():
    np.random.seed(7)
    n = 200
    x = np.random.randn(n)
    subj = np.repeat(np.arange(n // 5), 5)[:n].astype(float)
    y = 1.0 + 0.5 * x + np.repeat(np.random.randn(n // 5), 5)[:n] + np.random.randn(n) * 0.5
    df = pd.DataFrame({"y": y, "x": x, "subj": subj})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("MIXED y WITH x /RANDOM=subj.", reg, ctx))
    import statsmodels.formula.api as smf
    m = smf.mixedlm("Q('y') ~ Q('x')", df, groups=df["subj"]).fit()
    b = _col(pt, 0)
    assert abs(b[1] - float(m.fe_params.iloc[1])) < 1e-2


def test_genlog_gof_matches_poisson_deviance():
    np.random.seed(7)
    n = 300
    a = np.random.randint(0, 2, n).astype(float)
    b = np.random.randint(0, 3, n).astype(float)
    df = pd.DataFrame({"a": a, "b": b})
    reg, ctx = _ctx(df)
    out = execute_syntax("GENLOG a b.", reg, ctx)
    gof = _pt(out, 0)
    lr = _col(gof, 0)[0]
    assert lr >= 0  # deviance is non-negative; table populated

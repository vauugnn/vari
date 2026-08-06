"""REGRESSION / MEANS / NONPAR CORR / NPAR TESTS vs statsmodels & scipy."""
import numpy as np
import pandas as pd
from scipy import stats as sps

from sidecar.data.dataset import Dataset, DatasetRegistry
from sidecar.data.format import Format
from sidecar.data.variable import VariableMeta
from sidecar.procedures.registry import build_registry
from sidecar.syntax.registry import Context, execute_syntax


def make_registry(df):
    variables = [VariableMeta(name=c, print_format=Format("F", 8, 3)) for c in df.columns]
    reg = DatasetRegistry()
    reg.add(Dataset(df.copy(), variables))
    return reg


def run(reg, text):
    return execute_syntax(text, build_registry(), Context(reg))


def cells(t):
    return {(tuple(c["r"]), tuple(c["c"])): c["v"] for c in t["cells"]}


def tables(out):
    return [o for o in out if o["type"] == "PivotTable"]


def test_regression_matches_statsmodels():
    import statsmodels.api as sm

    rng = np.random.RandomState(11)
    x1 = rng.normal(0, 1, 80)
    x2 = rng.normal(0, 1, 80)
    y = 2 + 1.5 * x1 - 0.8 * x2 + rng.normal(0, 1, 80)
    reg = make_registry(pd.DataFrame({"y": y, "x1": x1, "x2": x2}))
    out = run(reg, "REGRESSION /DEPENDENT=y /METHOD=ENTER x1 x2.")
    ts = tables(out)
    model = sm.OLS(y, sm.add_constant(np.column_stack([x1, x2]))).fit()
    ms = [t for t in ts if t["title"] == "Model Summary"][0]
    assert abs(float("0" + cells(ms)[((0,), (1,))]) - model.rsquared) < 0.001
    coef = [t for t in ts if t["title"] == "Coefficients"][0]
    c = cells(coef)
    assert abs(float(c[((0,), (0,))]) - model.params[0]) < 0.01   # constant B
    assert abs(float(c[((1,), (0,))]) - model.params[1]) < 0.01   # x1 B


def test_means_report():
    df = pd.DataFrame({"y": [1.0, 2, 3, 10, 20, 30], "g": [1.0, 1, 1, 2, 2, 2]})
    reg = make_registry(df)
    rep = tables(run(reg, "MEANS TABLES=y BY g /CELLS=MEAN COUNT."))[0]
    c = cells(rep)
    assert c[((0,), (0,))] == "2.00"   # group 1 mean
    assert c[((1,), (0,))] == "20.00"  # group 2 mean


def test_nonpar_corr_spearman_matches_scipy():
    rng = np.random.RandomState(12)
    x = rng.normal(0, 1, 40)
    y = x**2 + rng.normal(0, 0.5, 40)
    reg = make_registry(pd.DataFrame({"x": x, "y": y}))
    out = run(reg, "NONPAR CORR /VARIABLES=x y /PRINT=SPEARMAN.")
    t = tables(out)[0]
    rho, _ = sps.spearmanr(x, y)
    assert abs(float("0" + cells(t)[((0, 0), (1,))].lstrip("-")) * (1 if rho >= 0 else -1) - rho) < 0.01


def test_npar_kruskal_matches_scipy():
    rng = np.random.RandomState(13)
    a, b, c = rng.normal(0, 1, 15), rng.normal(1, 1, 15), rng.normal(2, 1, 15)
    df = pd.DataFrame({"y": np.concatenate([a, b, c]), "g": [1.0] * 15 + [2.0] * 15 + [3.0] * 15})
    reg = make_registry(df)
    out = run(reg, "NPAR TESTS /K-W=y BY g(1 3).")
    ts = [t for t in tables(out) if t["title"] == "Test Statistics"][0]
    h, _ = sps.kruskal(a, b, c)
    assert abs(float(cells(ts)[((0,), (0,))]) - h) < 0.01


def test_npar_mann_whitney_matches_scipy():
    rng = np.random.RandomState(14)
    a, b = rng.normal(0, 1, 20), rng.normal(1, 1, 22)
    df = pd.DataFrame({"y": np.concatenate([a, b]), "g": [1.0] * 20 + [2.0] * 22})
    reg = make_registry(df)
    out = run(reg, "NPAR TESTS /M-W=y BY g(1 2).")
    ts = [t for t in tables(out) if t["title"] == "Test Statistics"][0]
    u = sps.mannwhitneyu(a, b, alternative="two-sided")
    U = min(u.statistic, 20 * 22 - u.statistic)
    assert abs(float(cells(ts)[((0,), (0,))]) - U) < 0.5


def test_npar_chisquare_gof():
    reg = make_registry(pd.DataFrame({"x": [1.0] * 10 + [2.0] * 20 + [3.0] * 30}))
    out = run(reg, "NPAR TESTS /CHISQUARE=x.")
    ts = [t for t in tables(out) if t["title"] == "Test Statistics"][0]
    obs = np.array([10, 20, 30], float)
    exp = np.full(3, 20.0)
    chi = ((obs - exp) ** 2 / exp).sum()
    assert abs(float(cells(ts)[((0,), (0,))]) - chi) < 0.01


def test_npar_friedman():
    rng = np.random.RandomState(21)
    df = pd.DataFrame({"a": rng.normal(0, 1, 20), "b": rng.normal(0.5, 1, 20), "c": rng.normal(1, 1, 20)})
    reg = make_registry(df)
    out = run(reg, "NPAR TESTS /FRIEDMAN=a b c.")
    ts = [t for t in tables(out) if t["title"] == "Test Statistics"][0]
    from scipy import stats as sps2

    stat, _ = sps2.friedmanchisquare(df["a"], df["b"], df["c"])
    assert abs(float(cells(ts)[((1,), (0,))]) - stat) < 0.01

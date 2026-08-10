"""Wave 4: survival (KM/Cox/life table), forecasting (ARIMA/spectra), CS."""
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


def test_cox_matches_statsmodels():
    np.random.seed(9)
    n = 250
    x = np.random.randn(n)
    time = np.random.exponential(np.exp(-0.4 * x))
    status = (np.random.rand(n) > 0.25).astype(float)
    df = pd.DataFrame({"time": time, "x": x, "status": status})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("COXREG time WITH x /STATUS=status(1).", reg, ctx))
    from statsmodels.duration.hazard_regression import PHReg
    m = PHReg(time, x.reshape(-1, 1), status=status.astype(int)).fit()
    b = _col(pt, 0)[0]
    assert abs(b - float(m.params[0])) < 1e-2


def test_km_events_count():
    np.random.seed(9)
    n = 100
    df = pd.DataFrame({"time": np.random.exponential(5, n), "status": (np.random.rand(n) > 0.4).astype(float),
                       "g": np.random.randint(1, 3, n).astype(float)})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("KM time BY g /STATUS=status(1).", reg, ctx))
    events = sum(_col(pt, 1))
    assert events == float(int(df["status"].sum()))


def test_arima_matches_statsmodels():
    np.random.seed(9)
    y = np.cumsum(np.random.randn(150)) + 20
    df = pd.DataFrame({"y": y})
    reg, ctx = _ctx(df)
    out = execute_syntax("TSMODEL y /ARIMA 1 0 0.", reg, ctx)
    fit = _pt(out, 0)  # Model Fit table with AIC
    from statsmodels.tsa.arima.model import ARIMA
    res = ARIMA(y, order=(1, 0, 0)).fit()
    aic = _col(fit, 0)[1]
    assert abs(aic - float(res.aic)) < 1.0


def test_csdescriptives_weighted_mean():
    np.random.seed(9)
    n = 300
    x = np.random.randn(n) + 5
    w = np.random.uniform(0.5, 2, n)
    df = pd.DataFrame({"x": x, "w": w})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("CSDESCRIPTIVES /SUMMARY VARIABLES=x /WEIGHT=w.", reg, ctx))
    mean = _col(pt, 0)[0]
    assert abs(mean - np.average(x, weights=w)) < 1e-3

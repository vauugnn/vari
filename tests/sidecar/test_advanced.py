"""Power, MVA, MI, Mediation, Meta-analysis."""
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
    return reg, Context(dr), dr


def _col(pt, col):
    return [float(c["v"]) for c in sorted(pt["cells"], key=lambda x: x["r"][0]) if c["c"] == [col]]


def _pt(out, i=0):
    return [o for o in out if o["type"] == "PivotTable"][i]


def test_power_ttest_matches_statsmodels():
    reg, ctx, _ = _ctx(pd.DataFrame({"x": [1.0, 2, 3]}))
    pt = _pt(execute_syntax("POWER /TEST=TTEST /EFFECT=0.5 /ALPHA=0.05 /POWER=0.8.", reg, ctx))
    from statsmodels.stats.power import TTestIndPower
    n = TTestIndPower().solve_power(effect_size=0.5, alpha=0.05, power=0.8)
    assert abs(_col(pt, 0)[-1] - n) < 0.5


def test_mva_missing_count():
    x = np.arange(10.0)
    x[::3] = np.nan
    reg, ctx, _ = _ctx(pd.DataFrame({"x": x}))
    pt = _pt(execute_syntax("MVA VARIABLES=x.", reg, ctx))
    assert _col(pt, 2)[0] == float(int(np.isnan(x).sum()))


def test_mi_fills_missing():
    np.random.seed(3)
    x = np.random.randn(60); m = 0.5 * x + np.random.randn(60)
    xm = x.copy(); xm[::7] = np.nan
    reg, ctx, dr = _ctx(pd.DataFrame({"x": x, "m": m, "xm": xm}))
    execute_syntax("MI VARIABLES=x m xm.", reg, ctx)
    assert dr.active.df["xm"].isna().sum() == 0


def test_mediation_indirect_effect():
    np.random.seed(3)
    n = 200
    x = np.random.randn(n); m = 0.6 * x + np.random.randn(n) * 0.5; y = 0.5 * m + 0.2 * x + np.random.randn(n) * 0.5
    reg, ctx, _ = _ctx(pd.DataFrame({"x": x, "m": m, "y": y}))
    pt = _pt(execute_syntax("MEDIATION y WITH x /MED m.", reg, ctx))
    vals = _col(pt, 0)
    # total ~= direct + indirect
    assert abs(vals[0] - (vals[1] + vals[2])) < 1e-6


def test_meta_pooled_between_studies():
    es = np.array([0.3, 0.5, 0.4, 0.6]); se = np.array([0.1, 0.12, 0.09, 0.11])
    n = 10
    df = pd.DataFrame({"es": np.r_[es, [np.nan] * (n - 4)], "se": np.r_[se, [np.nan] * (n - 4)]})
    reg, ctx, _ = _ctx(df)
    pt = _pt(execute_syntax("META EFFECT=es SE=se /MODEL=FIXED.", reg, ctx))
    w = 1 / se ** 2
    pooled = (w * es).sum() / w.sum()
    assert abs(_col(pt, 0)[0] - pooled) < 1e-3

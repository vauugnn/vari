"""Wave 2: GLM multivariate (MANOVA), PROXIMITIES, CANCORR parity."""
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


def _cell(pt, row, col):
    for c in pt["cells"]:
        if c["r"] == [row] and c["c"] == [col]:
            return float(c["v"])
    raise KeyError((row, col))


def test_proximities_matches_scipy():
    np.random.seed(3)
    df = pd.DataFrame({"a": np.random.randn(10), "b": np.random.randn(10), "c": np.random.randn(10)})
    reg, ctx = _ctx(df)
    out = execute_syntax("PROXIMITIES a b c /MEASURE=EUCLID /VIEW=VARIABLE.", reg, ctx)
    pt = [o for o in out if o["type"] == "PivotTable"][0]
    from scipy.spatial.distance import pdist, squareform
    M = squareform(pdist(df.to_numpy().T, metric="euclidean"))
    # cell [0][1] is distance between a and b
    got = _cell(pt, 0, 1)
    assert abs(got - M[0, 1]) < 1e-3


def test_cancorr_matches_sklearn():
    np.random.seed(4)
    n = 80
    x1 = np.random.randn(n); x2 = np.random.randn(n)
    y1 = x1 * 0.8 + np.random.randn(n) * 0.3
    y2 = x2 * 0.6 + np.random.randn(n) * 0.4
    df = pd.DataFrame({"x1": x1, "x2": x2, "y1": y1, "y2": y2})
    reg, ctx = _ctx(df)
    out = execute_syntax("CANCORR y1 y2 WITH x1 x2.", reg, ctx)
    pt = [o for o in out if o["type"] == "PivotTable"][0]
    from sklearn.cross_decomposition import CCA
    cca = CCA(n_components=2, scale=True)
    Xc, Yc = cca.fit_transform(df[["y1", "y2"]], df[["x1", "x2"]])
    r0 = abs(np.corrcoef(Xc[:, 0], Yc[:, 0])[0, 1])
    got = _cell(pt, 0, 0)
    assert abs(got - r0) < 1e-2


def test_manova_wilks_matches_statsmodels():
    np.random.seed(5)
    n = 60
    g = np.random.randint(1, 4, n)
    df = pd.DataFrame({"y1": np.random.randn(n) + g, "y2": np.random.randn(n) + g * 0.5, "g": g.astype(float)})
    reg, ctx = _ctx(df)
    out = execute_syntax("GLM y1 y2 BY g.", reg, ctx)
    pt = [o for o in out if o["type"] == "PivotTable"][0]
    from statsmodels.multivariate.manova import MANOVA
    res = MANOVA.from_formula("Q('y1') + Q('y2') ~ C(Q('g'))", data=df).mv_test()
    # find the effect row for g's Wilks' lambda
    key = [k for k in res.results if k != "Intercept"][0]
    wl = float(res.results[key]["stat"].loc["Wilks' lambda", "Value"])
    # rows: Intercept x4 then g x4; Wilks is 2nd stat -> row index 5, col 0 (Value)
    got = _cell(pt, 5, 0)
    assert abs(got - wl) < 1e-3

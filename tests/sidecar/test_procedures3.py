"""ONEWAY + RELIABILITY verified against scipy / hand computation."""
import numpy as np
import pandas as pd
from scipy import stats as sps

from sidecar.data.dataset import Dataset, DatasetRegistry
from sidecar.data.format import Format
from sidecar.data.variable import VariableMeta
from sidecar.procedures.registry import build_registry
from sidecar.procedures.reliability import cronbach_alpha
from sidecar.syntax.registry import Context, execute_syntax


def make_registry(df):
    variables = [VariableMeta(name=c, print_format=Format("F", 8, 3)) for c in df.columns]
    reg = DatasetRegistry()
    reg.add(Dataset(df.copy(), variables))
    return reg


def run(reg, text):
    return execute_syntax(text, build_registry(), Context(reg))


def cells(table):
    return {(tuple(c["r"]), tuple(c["c"])): c["v"] for c in table["cells"]}


def tables(out):
    return [o for o in out if o["type"] == "PivotTable"]


def test_oneway_anova_matches_scipy():
    rng = np.random.RandomState(7)
    g1 = rng.normal(10, 2, 20)
    g2 = rng.normal(12, 2, 22)
    g3 = rng.normal(11, 2, 18)
    df = pd.DataFrame({"y": np.concatenate([g1, g2, g3]), "grp": [1.0] * 20 + [2.0] * 22 + [3.0] * 18})
    reg = make_registry(df)
    anova = tables(run(reg, "ONEWAY y BY grp."))[0]
    assert anova["caption"] == "ANOVA"
    c = cells(anova)
    f_exp, p_exp = sps.f_oneway(g1, g2, g3)
    assert abs(float(c[((0,), (3,))]) - f_exp) < 0.001  # F
    assert int(c[((0,), (1,))]) == 2                     # df between
    assert int(c[((1,), (1,))]) == 57                    # df within


def test_oneway_homogeneity_levene_on_mean():
    rng = np.random.RandomState(8)
    a, b = rng.normal(0, 1, 30), rng.normal(0, 2, 30)
    df = pd.DataFrame({"y": np.concatenate([a, b]), "grp": [1.0] * 30 + [2.0] * 30})
    reg = make_registry(df)
    out = run(reg, "ONEWAY y BY grp /STATISTICS=HOMOGENEITY.")
    homog = [t for t in tables(out) if t["title"].startswith("Test of Homogeneity")][0]
    lev = sps.levene(a, b, center="mean")
    assert abs(float(cells(homog)[((0,), (0,))]) - lev.statistic) < 0.001


def test_cronbach_alpha_matches_pingouin():
    rng = np.random.RandomState(9)
    latent = rng.normal(0, 1, 200)
    items = {f"q{i}": latent + rng.normal(0, 0.7, 200) for i in range(1, 6)}
    df = pd.DataFrame(items)
    reg = make_registry(df)
    out = run(reg, "RELIABILITY /VARIABLES=q1 q2 q3 q4 q5 /SUMMARY=TOTAL.")
    rs = tables(out)[0]
    ours = float("0" + cells(rs)[((0,), (0,))])  # leading zero stripped
    try:
        import pingouin as pg

        expected = pg.cronbach_alpha(data=df)[0]
    except Exception:
        expected = cronbach_alpha(df.to_numpy(float))
    assert abs(ours - expected) < 0.002


def test_reliability_item_total_present():
    rng = np.random.RandomState(10)
    latent = rng.normal(0, 1, 100)
    df = pd.DataFrame({f"q{i}": latent + rng.normal(0, 0.8, 100) for i in range(1, 4)})
    reg = make_registry(df)
    out = run(reg, "RELIABILITY /VARIABLES=q1 q2 q3 /SUMMARY=TOTAL.")
    it = [t for t in tables(out) if t["title"] == "Item-Total Statistics"][0]
    assert it["rowDims"][0]["categories"] == ["q1", "q2", "q3"]

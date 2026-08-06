"""CORRELATIONS / T-TEST / CROSSTABS verified against scipy on synthetic data."""
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


def cells(table):
    return {(tuple(c["r"]), tuple(c["c"])): c["v"] for c in table["cells"]}


def tables(out):
    return [o for o in out if o["type"] == "PivotTable"]


def test_correlations_matches_scipy():
    rng = np.random.RandomState(1)
    x = rng.normal(0, 1, 50)
    y = 0.6 * x + rng.normal(0, 1, 50)
    reg = make_registry(pd.DataFrame({"x": x, "y": y}))
    out = run(reg, "CORRELATIONS /VARIABLES=x y.")
    t = tables(out)[0]
    c = cells(t)
    r_expected, p_expected = sps.pearsonr(x, y)
    # row [0=x, 0=Pearson], col [1=y]
    assert abs(float(c[((0, 0), (1,))]) - r_expected) < 0.001
    assert float(c[((0, 0), (0,))]) == 1.0  # diagonal
    assert abs(float("0" + c[((0, 1), (1,))]) - p_expected) < 0.001  # sig, leading zero stripped


def test_ttest_one_sample_matches_scipy():
    rng = np.random.RandomState(2)
    y = rng.normal(5, 2, 40)
    reg = make_registry(pd.DataFrame({"y": y}))
    out = run(reg, "T-TEST /TESTVAL=4 /VARIABLES=y.")
    test = tables(out)[1]
    c = cells(test)
    res = sps.ttest_1samp(y, 4)
    assert abs(float(c[((0,), (0,))]) - res.statistic) < 0.001  # t
    assert int(c[((0,), (1,))]) == 39  # df


def test_ttest_independent_levene_on_mean_and_both_rows():
    rng = np.random.RandomState(3)
    a = rng.normal(10, 2, 30)
    b = rng.normal(11.5, 3, 28)
    df = pd.DataFrame({"y": np.concatenate([a, b]), "g": [1.0] * 30 + [2.0] * 28})
    reg = make_registry(df)
    out = run(reg, "T-TEST GROUPS=g(1 2) /VARIABLES=y.")
    test = tables(out)[1]
    c = cells(test)
    teq = sps.ttest_ind(a, b, equal_var=True)
    twe = sps.ttest_ind(a, b, equal_var=False)
    lev = sps.levene(a, b, center="mean")
    # cols: 0 Levene F,1 Levene Sig,2 t,3 df,4 sig,5 mdiff,6 sediff
    assert abs(float(c[((0, 0), (0,))]) - lev.statistic) < 0.001   # Levene F (mean-centered)
    assert abs(float(c[((0, 0), (2,))]) - teq.statistic) < 0.001   # equal-variance t
    assert abs(float(c[((0, 1), (2,))]) - twe.statistic) < 0.001   # Welch t
    assert int(c[((0, 0), (3,))]) == 56                            # pooled df


def test_ttest_paired_matches_scipy():
    rng = np.random.RandomState(4)
    a = rng.normal(20, 4, 25)
    b = a + rng.normal(1, 2, 25)
    reg = make_registry(pd.DataFrame({"pre": a, "post": b}))
    out = run(reg, "T-TEST PAIRS=pre WITH post.")
    test = tables(out)[-1]
    c = cells(test)
    res = sps.ttest_rel(a, b)
    assert abs(float(c[((0,), (3,))]) - res.statistic) < 0.001  # t at col 3


def test_crosstabs_chisquare_matches_scipy():
    # 3x2 table via explicit rows
    r = [1] * 40 + [2] * 40 + [3] * 20
    c = ([1] * 25 + [2] * 15) + ([1] * 20 + [2] * 20) + ([1] * 5 + [2] * 15)
    reg = make_registry(pd.DataFrame({"row": [float(x) for x in r], "col": [float(x) for x in c]}))
    out = run(reg, "CROSSTABS /TABLES=row BY col /STATISTICS=CHISQ.")
    ts = tables(out)
    chi = ts[-1]
    assert chi["title"] == "Chi-Square Tests"
    cc = cells(chi)
    import pandas as pd2

    obs = pd2.crosstab(pd2.Series(r), pd2.Series(c)).to_numpy()
    chi2, p, dof, _ = sps.chi2_contingency(obs, correction=False)
    # Pearson row 0: Value col 0, df col 1
    assert abs(float(cc[((0,), (0,))]) - chi2) < 0.01
    assert int(cc[((0,), (1,))]) == dof

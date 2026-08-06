"""Expression language + COMPUTE/RECODE/IF/COUNT (HLD 7)."""
import numpy as np
import pandas as pd

from sidecar.data.dataset import Dataset, DatasetRegistry
from sidecar.data.format import Format
from sidecar.data.variable import VariableMeta
from sidecar.expr.evaluate import EvalContext, evaluate
from sidecar.expr.parser import parse_expression
from sidecar.procedures.registry import build_registry
from sidecar.syntax.registry import Context, execute_syntax


def ds_from(df):
    variables = [VariableMeta(name=c, print_format=Format("F", 8, 2)) for c in df.columns]
    return Dataset(df.copy(), variables)


def col(ds, name):
    return ds.df[name].to_numpy(dtype=float)


def run(ds, text):
    reg = DatasetRegistry()
    reg.add(ds)
    return execute_syntax(text, build_registry(), Context(reg))


def ev(ds, expr):
    return evaluate(parse_expression(expr), EvalContext(ds))


def test_precedence():
    ds = ds_from(pd.DataFrame({"x": [1.0, 2, 3]}))
    assert list(ev(ds, "2 + 3 * 4")) == [14, 14, 14]
    assert list(ev(ds, "(2 + 3) * 4")) == [20, 20, 20]
    assert list(ev(ds, "2 ** 3")) == [8, 8, 8]
    assert list(ev(ds, "-2 ** 2")) == [-4, -4, -4]  # ** binds tighter than unary minus (SPSS)


def test_missing_propagation():
    ds = ds_from(pd.DataFrame({"x": [1.0, np.nan, 3]}))
    out = ev(ds, "x + 1")
    assert out[0] == 2 and np.isnan(out[1]) and out[2] == 4


def test_logical_short_circuit():
    ds = ds_from(pd.DataFrame({"x": [np.nan]}))
    # FALSE AND missing = FALSE ; TRUE OR missing = TRUE
    assert ev(ds, "0 AND x")[0] == 0.0
    assert ev(ds, "1 OR x")[0] == 1.0
    assert np.isnan(ev(ds, "1 AND x")[0])


def test_mean_dot_n_min_valid():
    ds = ds_from(pd.DataFrame({"q1": [1.0, 1, 1], "q2": [3.0, np.nan, np.nan], "q3": [5.0, np.nan, 5]}))
    out = ev(ds, "MEAN.3(q1 TO q3)")
    # row0: 3 valid -> mean 3; row1: 1 valid (<3) -> missing; row2: 2 valid (<3) -> missing
    assert out[0] == 3.0 and np.isnan(out[1]) and np.isnan(out[2])
    out2 = ev(ds, "MEAN.1(q1 TO q3)")
    assert out2[1] == 1.0


def test_missing_functions():
    ds = ds_from(pd.DataFrame({"x": [1.0, np.nan]}))
    assert list(ev(ds, "SYSMIS(x)")) == [0.0, 1.0]
    assert list(ev(ds, "NVALID(x)")) == [1.0, 0.0]


def test_compute_creates_variable():
    ds = ds_from(pd.DataFrame({"a": [1.0, 2, 3], "b": [10.0, 20, 30]}))
    run(ds, "COMPUTE total = a + b.")
    assert "total" in [v.name for v in ds.variables]
    assert list(col(ds, "total")) == [11, 22, 33]


def test_if_conditional_assignment():
    ds = ds_from(pd.DataFrame({"x": [1.0, 5, 9]}))
    run(ds, "COMPUTE grp = 0.\nIF (x > 4) grp = 1.")
    assert list(col(ds, "grp")) == [0, 1, 1]


def test_recode_into_different():
    ds = ds_from(pd.DataFrame({"age": [15.0, 30, 70]}))
    run(ds, "RECODE age (LO THRU 17=1)(18 THRU 64=2)(65 THRU HI=3) INTO agecat.")
    assert list(col(ds, "agecat")) == [1, 2, 3]


def test_count_values():
    ds = ds_from(pd.DataFrame({"q1": [1.0, 0, 1], "q2": [1.0, 1, 0], "q3": [0.0, 0, 1]}))
    run(ds, "COUNT nyes = q1 q2 q3 (1).")
    assert list(col(ds, "nyes")) == [2, 1, 2]


def test_scale_score_with_missing():
    # survey scale: mean of 5 items requiring at least 3 valid
    rng = np.random.RandomState(3)
    data = pd.DataFrame({f"q{i}": rng.randint(1, 6, 10).astype(float) for i in range(1, 6)})
    data.loc[0, ["q1", "q2", "q3", "q4"]] = np.nan  # only 1 valid -> missing scale
    ds = ds_from(data)
    run(ds, "COMPUTE scale = MEAN.3(q1 TO q5).")
    s = col(ds, "scale")
    assert np.isnan(s[0])
    assert not np.isnan(s[1])

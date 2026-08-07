"""Binary logistic, multinomial, ordinal regression."""
import numpy as np
import pandas as pd

from sidecar.data.dataset import Dataset, DatasetRegistry
from sidecar.data.format import Format
from sidecar.data.variable import VariableMeta
from sidecar.procedures.registry import build_registry
from sidecar.syntax.registry import Context, execute_syntax


def make(df):
    reg = DatasetRegistry()
    reg.add(Dataset(df.copy(), [VariableMeta(name=c, print_format=Format("F", 8, 2)) for c in df.columns]))
    return reg


def run(reg, text):
    return execute_syntax(text, build_registry(), Context(reg))


def tables(out):
    return [o for o in out if o["type"] == "PivotTable"]


def errs(out):
    return [o for o in out if o["type"] == "Error"]


def test_binary_logistic():
    rng = np.random.RandomState(7)
    x = rng.normal(0, 1, 200)
    p = 1 / (1 + np.exp(-(0.5 + 1.5 * x)))
    y = (rng.uniform(size=200) < p).astype(float)
    reg = make(pd.DataFrame({"y": y, "x": x}))
    out = run(reg, "LOGISTIC REGRESSION VARIABLES y WITH x.")
    assert not errs(out), errs(out)
    ve = [t for t in tables(out) if t["title"] == "Variables in the Equation"][0]
    c = {(tuple(cc["r"]), tuple(cc["c"])): cc["v"] for cc in ve["cells"]}
    # Exp(B) for x should be > 1 (positive effect)
    assert float(c[((0,), (5,))]) > 1


def test_multinomial():
    rng = np.random.RandomState(8)
    x = rng.normal(0, 1, 150)
    y = np.select([x < -0.5, x > 0.5], [0.0, 2.0], default=1.0)
    reg = make(pd.DataFrame({"y": y, "x": x}))
    out = run(reg, "NOMREG y WITH x.")
    assert not errs(out), errs(out)
    assert tables(out)[0]["title"] == "Parameter Estimates"


def test_ordinal():
    rng = np.random.RandomState(9)
    x = rng.normal(0, 1, 150)
    y = np.clip(np.round(2 + x + rng.normal(0, 0.5, 150)), 0, 4)
    reg = make(pd.DataFrame({"y": y, "x": x}))
    out = run(reg, "PLUM y WITH x.")
    assert not errs(out), errs(out)
    assert tables(out)[0]["title"] == "Parameter Estimates"

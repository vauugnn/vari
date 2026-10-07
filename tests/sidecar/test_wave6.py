"""Wave 6: OLAP, Custom Tables, Multiple Response, Control charts, Bayesian."""
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


def test_olap_total_mean_matches_pandas():
    np.random.seed(13)
    n = 200
    g = np.random.randint(1, 4, n).astype(float)
    y = np.random.randn(n) + g
    df = pd.DataFrame({"y": y, "g": g})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("OLAP y BY g.", reg, ctx))
    total_mean = _col(pt, 1)[-1]
    assert abs(total_mean - y.mean()) < 1e-2


def test_multiresponse_counts():
    np.random.seed(13)
    n = 100
    d1 = np.random.randint(0, 2, n).astype(float)
    d2 = np.random.randint(0, 2, n).astype(float)
    df = pd.DataFrame({"d1": d1, "d2": d2})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("MULTRESPONSE /FREQUENCIES d1 d2 /VALUE=1.", reg, ctx))
    counts = _col(pt, 0)
    assert counts[0] == float(int(d1.sum())) and counts[1] == float(int(d2.sum()))


def test_bayes_normal_posterior_mean_is_sample_mean():
    np.random.seed(13)
    x = np.random.randn(120) + 3.0
    df = pd.DataFrame({"x": x})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("BAYES x /TEST TYPE=NORMAL.", reg, ctx))
    assert abs(_col(pt, 0)[0] - x.mean()) < 1e-3


def test_bayes_binomial_proportion():
    np.random.seed(13)
    x = np.random.binomial(1, 0.35, 200).astype(float)
    df = pd.DataFrame({"x": x})
    reg, ctx = _ctx(df)
    pt = _pt(execute_syntax("BAYES x /TEST TYPE=BINOMIAL.", reg, ctx))
    k = x.sum(); n = len(x)
    post = (1 + k) / (2 + n)  # Beta(1,1) posterior mean
    assert abs(_col(pt, 0)[0] - post) < 1e-3


def test_control_chart_renders():
    np.random.seed(13)
    df = pd.DataFrame({"y": np.random.randn(50) + 10})
    reg, ctx = _ctx(df)
    out = execute_syntax("SPCHART y /TYPE=I.", reg, ctx)
    assert any(o.get("type") == "Chart" and "<svg" in o.get("svg", "") for o in out)


# ---- Select Cases support: $CASENUM, random functions, USE, SAMPLE, DATASET COPY ----
def _sel_ctx(n=100):
    import pandas as pd
    from sidecar.data.dataset import Dataset, DatasetRegistry
    from sidecar.data.format import Format
    from sidecar.data.variable import VariableMeta
    from sidecar.procedures.registry import build_registry

    df = pd.DataFrame({"x": np.arange(n, dtype=float)})
    reg = DatasetRegistry()
    reg.add(Dataset(df, [VariableMeta(name="x", print_format=Format("F", 8, 0))]))
    return reg, build_registry()


def _run(reg, registry, text):
    return execute_syntax(text, registry, Context(reg))


def test_use_range_filters_by_case_number():
    reg, r = _sel_ctx()
    _run(reg, r, "USE 11 TO 20.")
    ds = reg.active
    assert ds.filter_var == "filter_$"
    assert int(ds.df["filter_$"].sum()) == 10
    _run(reg, r, "USE ALL.")
    assert reg.active.filter_var is None


def test_sample_exact_and_fraction():
    reg, r = _sel_ctx()
    _run(reg, r, "SET SEED=7.")
    _run(reg, r, "SAMPLE 10 FROM 50.")
    assert reg.active.n_rows == 10 and reg.active.df["x"].max() < 50
    reg2, r2 = _sel_ctx(2000)
    _run(reg2, r2, "SET SEED=3.")
    _run(reg2, r2, "SAMPLE .25.")
    assert 400 < reg2.active.n_rows < 600


def test_casenum_and_uniform_in_expressions():
    reg, r = _sel_ctx()
    _run(reg, r, "COMPUTE keep = ($CASENUM <= 5).")
    assert int(reg.active.df["keep"].sum()) == 5
    _run(reg, r, "COMPUTE u = UNIFORM(1).")
    u = reg.active.df["u"]
    assert (u >= 0).all() and (u < 1).all()


def test_dataset_copy_and_activate():
    reg, r = _sel_ctx()
    _run(reg, r, "DATASET COPY sub.")
    assert reg.get("sub") is not None and reg.active.name != "sub"
    _run(reg, r, "DATASET ACTIVATE sub.")
    assert reg.active.name == "sub"
    _run(reg, r, "SELECT IF (x < 10).")
    assert reg.active.n_rows == 10 and reg.get("DataSet1").n_rows == 100


def test_select_if_operator_forms_used_by_the_dialog():
    reg, r = _sel_ctx(20)
    _run(reg, r, "SELECT IF ($CASENUM >= 3 & $CASENUM <= 6).")
    assert reg.active.n_rows == 4
    _run(reg, r, "COMPUTE f = x.")
    _run(reg, r, "SELECT IF (f ~= 3 & ~MISSING(f)).")
    assert reg.active.n_rows == 3


def test_select_cases_dialog_syntax_end_to_end():
    """The exact scripts SelectCasesDialog emits, for every mode/output combination."""
    cond = "x >= 10 & x < 30"
    scripts = {
        "if-filter": ("USE ALL.\nCOMPUTE filter_$=(%s).\nVARIABLE LABELS filter_$ '%s (FILTER)'.\n"
                      "VALUE LABELS filter_$ 0 'Not Selected' 1 'Selected'.\nFORMATS filter_$ (f1.0).\n"
                      "FILTER BY filter_$.\nEXECUTE." % (cond, cond), 100, 20),
        "if-delete": ("SELECT IF (%s).\nEXECUTE." % cond, 20, 20),
        "if-copy": ("DATASET COPY Sel.\nDATASET ACTIVATE Sel.\nFILTER OFF.\nUSE ALL.\nSELECT IF (%s).\nEXECUTE." % cond, 20, 20),
        "range-filter": ("USE ALL.\nUSE 5 THRU 14.\nEXECUTE.", 100, 10),
        "range-delete": ("SELECT IF ($CASENUM >= 5 & $CASENUM <= 14).\nEXECUTE.", 10, 10),
        "exact-delete": ("SAMPLE 10 FROM 50.\nEXECUTE.", 10, 10),
        "approx-filter": ("USE ALL.\nCOMPUTE filter_$=(UNIFORM(1) <= 0.5).\nFORMATS filter_$ (f1.0).\nFILTER BY filter_$.\nEXECUTE.", 100, None),
    }
    for name, (text, rows, selected) in scripts.items():
        reg, r = _sel_ctx(100)
        out = _run(reg, r, "SET SEED=1.\n" + text)
        assert not [o for o in out if o["type"] == "Error"], (name, out)
        ds = reg.active
        assert ds.n_rows == rows, (name, ds.n_rows)
        if selected is not None and ds.filter_var:
            assert int(ds.df[ds.filter_var].sum()) == selected, name
        if name == "approx-filter":
            assert 30 < int(ds.df["filter_$"].sum()) < 70
    # copy leaves the original untouched
    reg, r = _sel_ctx(100)
    _run(reg, r, scripts["if-copy"][0])
    assert reg.get("DataSet1").n_rows == 100

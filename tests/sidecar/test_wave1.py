"""Wave 1: CREATE (shift), SET SEED, and the new GRAPH chart branches."""
import numpy as np
import pandas as pd

from sidecar.data.dataset import Dataset, DatasetRegistry
from sidecar.data.format import Format
from sidecar.data.variable import VariableMeta
from sidecar.procedures.registry import build_registry
from sidecar.syntax.registry import Context, execute_syntax


def _reg_ctx(df):
    reg = build_registry()
    dr = DatasetRegistry()
    vs = [VariableMeta(name=n, print_format=Format("F", 8, 2)) for n in df.columns]
    dr.add(Dataset(df, vs), activate=True)
    return reg, Context(dr), dr


def test_create_lag_lead_diff():
    reg, ctx, dr = _reg_ctx(pd.DataFrame({"x": [1.0, 2, 3, 4, 5]}))
    execute_syntax("CREATE xl = LAG(x,1).", reg, ctx)
    execute_syntax("CREATE xd = DIFF(x,1).", reg, ctx)
    d = dr.active.df
    assert np.isnan(d["xl"].iloc[0]) and d["xl"].iloc[1] == 1.0
    assert list(d["xd"].iloc[1:]) == [1.0, 1.0, 1.0, 1.0]


def test_set_seed_reproducible():
    reg, ctx, _ = _reg_ctx(pd.DataFrame({"x": [1.0, 2, 3]}))
    execute_syntax("SET SEED = 7.", reg, ctx)
    a = np.random.rand(4)
    np.random.seed(7)
    assert np.allclose(a, np.random.rand(4))


def test_new_graph_charts_render_svg():
    np.random.seed(0)
    df = pd.DataFrame({
        "y": np.random.randn(40) * 3 + 10,
        "g": np.random.randint(1, 4, 40),
        "hi": np.random.rand(40) + 2,
        "lo": np.random.rand(40),
    })
    reg, ctx, _ = _reg_ctx(df)
    for cmd in ["GRAPH /BOXPLOT=y BY g.", "GRAPH /PYRAMID=g BY g.",
                "GRAPH /BAR3D=g BY g.", "GRAPH /HILO=hi lo."]:
        out = execute_syntax(cmd, reg, ctx)
        assert any(o.get("type") == "Chart" and "<svg" in o.get("svg", "") for o in out), cmd

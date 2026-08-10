"""Wave 7: restructure (VARSTOCASES/CASESTOVARS) and Visual Binning."""
import numpy as np
import pandas as pd

from sidecar.data.dataset import Dataset, DatasetRegistry
from sidecar.data.format import Format
from sidecar.data.variable import VariableMeta
from sidecar.procedures.registry import build_registry
from sidecar.syntax.registry import Context, execute_syntax


def _reg_dr(df):
    reg = build_registry()
    dr = DatasetRegistry()
    dr.add(Dataset(df, [VariableMeta(name=c, print_format=Format("F", 8, 2)) for c in df.columns]), activate=True)
    return reg, dr


def test_varstocases_wide_to_long():
    reg, dr = _reg_dr(pd.DataFrame({"id": [1.0, 2, 3], "t1": [10.0, 20, 30], "t2": [11.0, 21, 31]}))
    execute_syntax("VARSTOCASES /MAKE score FROM t1 t2 /INDEX=time.", reg, Context(dr))
    assert dr.active.n_rows == 6
    assert set(dr.active.df["score"]) == {10, 20, 30, 11, 21, 31}


def test_casestovars_long_to_wide():
    long = pd.DataFrame({"id": [1.0, 1, 2, 2], "time": [1.0, 2, 1, 2], "score": [10.0, 11, 20, 21]})
    reg, dr = _reg_dr(long)
    execute_syntax("CASESTOVARS /ID=id /INDEX=time.", reg, Context(dr))
    assert dr.active.n_rows == 2
    assert any(v.name.startswith("score.") for v in dr.active.variables)


def test_visual_binning_rank_gives_n_bins():
    reg, dr = _reg_dr(pd.DataFrame({"x": np.arange(1.0, 101)}))
    execute_syntax("VBIN x INTO xb /BINS 4 /METHOD RANK.", reg, Context(dr))
    assert sorted(set(dr.active.df["xb"].dropna())) == [1.0, 2.0, 3.0, 4.0]


def test_visual_binning_equal_width():
    reg, dr = _reg_dr(pd.DataFrame({"x": np.arange(0.0, 100)}))
    execute_syntax("VBIN x INTO xb /BINS 5 /METHOD EQUAL.", reg, Context(dr))
    assert dr.active.df["xb"].max() == 5.0
    assert dr.active.df["xb"].min() == 1.0

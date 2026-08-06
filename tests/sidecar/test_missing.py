"""Missing mask behaviour (PHASE-1 section 3, HLD 3.3)."""
import numpy as np
import pandas as pd

from sidecar.data.missing import MissingSpec, missing_mask
from sidecar.data.variable import VariableMeta


def _meta(spec):
    return VariableMeta(name="x", missing=spec)


def test_discrete_matches():
    s = pd.Series([1.0, 2.0, 9.0, np.nan])
    spec = MissingSpec.discrete([9.0])
    assert list(spec.matches(s)) == [False, False, True, False]


def test_range_matches():
    s = pd.Series([1.0, 5.0, 7.0, 99.0])
    spec = MissingSpec.range(5.0, 9.0)
    assert list(spec.matches(s)) == [False, True, True, False]


def test_range_plus_discrete():
    s = pd.Series([1.0, 6.0, 99.0])
    spec = MissingSpec.range(5.0, 9.0, discrete=99.0)
    assert list(spec.matches(s)) == [False, True, True]


def test_missing_mask_excludes_user_by_default():
    s = pd.Series([1.0, 9.0, np.nan])
    meta = _meta(MissingSpec.discrete([9.0]))
    # system-missing + user-missing both excluded
    assert list(missing_mask(s, meta)) == [False, True, True]


def test_missing_mask_include_user():
    s = pd.Series([1.0, 9.0, np.nan])
    meta = _meta(MissingSpec.discrete([9.0]))
    # MISSING=INCLUDE: only system-missing counts
    assert list(missing_mask(s, meta, include_user_missing=True)) == [False, False, True]


def test_none_matches_nothing():
    s = pd.Series([1.0, 2.0])
    assert list(MissingSpec.none().matches(s)) == [False, False]


def test_json_round_trip():
    spec = MissingSpec.range(1.0, 5.0, discrete=9.0)
    assert MissingSpec.from_json(spec.to_json()).matches(pd.Series([3.0, 9.0])).tolist() == [True, True]

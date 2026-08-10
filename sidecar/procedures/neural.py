"""Neural Networks: Multilayer Perceptron (MLP) and Radial Basis Function
(RBF). sklearn-backed. Auto-detects classification vs regression from whether
the target is integer-coded with few distinct values."""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure

_F3 = Format("F", 8, 3)
_F1 = Format("F", 8, 1)


def _clean(ds: Any, names: list[str]) -> pd.DataFrame:
    frame = {}
    for nm in names:
        s = ds.df[nm]
        frame[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
    return pd.DataFrame(frame).dropna()


def _is_classification(y: np.ndarray) -> bool:
    u = np.unique(y)
    return len(u) <= 10 and np.allclose(u, np.round(u))


def _parse(body, allnames):
    m = re.search(r"(.+?)\bBY\b(.+)", body, re.IGNORECASE)
    covars: list[str] = []
    if m:
        target = expand_varlist(m.group(1), allnames)[0]
        rhs = m.group(2)
        mw = re.search(r"(.+?)\bWITH\b(.+)", rhs, re.IGNORECASE)
        if mw:
            factors = expand_varlist(mw.group(1), allnames)
            covars = expand_varlist(mw.group(2), allnames)
        else:
            factors = expand_varlist(rhs, allnames)
        feats = factors + covars
    else:
        mw = re.search(r"(.+?)\bWITH\b(.+)", body, re.IGNORECASE)
        if not mw:
            return None, []
        target = expand_varlist(mw.group(1), allnames)[0]
        feats = expand_varlist(mw.group(2), allnames)
    return target, feats


def _report(title, target, feats, model_factory, ds):
    data = _clean(ds, [target] + feats)
    X = data[feats].to_numpy(float)
    X = (X - X.mean(0)) / (X.std(0) + 1e-9)
    y = data[target].to_numpy()
    clf = _is_classification(y)
    from sklearn.model_selection import train_test_split

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=0)
    model = model_factory(clf)
    model.fit(Xtr, ytr)
    out = [{"type": "Title", "text": title}]
    if clf:
        acc_tr = float((model.predict(Xtr) == ytr).mean())
        acc_te = float((model.predict(Xte) == yte).mean())
        t = PivotTable("Model Summary", [Dimension("Sample", ["Training", "Testing"])],
                       [Dimension("", ["Percent Correct"])])
        t.set([0], [0], _F1.render(acc_tr * 100))
        t.set([1], [0], _F1.render(acc_te * 100))
    else:
        from sklearn.metrics import r2_score

        r2_tr = float(r2_score(ytr, model.predict(Xtr)))
        r2_te = float(r2_score(yte, model.predict(Xte)))
        t = PivotTable("Model Summary", [Dimension("Sample", ["Training", "Testing"])],
                       [Dimension("", ["R Squared"])])
        t.set([0], [0], _F3.render(r2_tr))
        t.set([1], [0], _F3.render(r2_te))
    out.append(t.to_json())
    return out


class Mlp(DataProcedure):
    """MLP target BY factors WITH covars [/HIDDEN n] — multilayer perceptron."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        target, feats = _parse(body, allnames)
        if target is None or not feats:
            return [{"type": "Error", "text": "MLP needs 'target BY/WITH predictors'."}]
        hidden = 10
        for name, b in subs:
            if name.upper() in ("HIDDEN", "ARCHITECTURE", "CRITERIA"):
                mm = re.search(r"\d+", b)
                if mm:
                    hidden = int(mm.group())

        def factory(clf):
            from sklearn.neural_network import MLPClassifier, MLPRegressor

            kw = dict(hidden_layer_sizes=(hidden,), max_iter=1000, random_state=0)
            return MLPClassifier(**kw) if clf else MLPRegressor(**kw)

        return _report("Multilayer Perceptron", target, feats, factory, ds)


class Rbf(DataProcedure):
    """RBF target BY factors WITH covars — radial basis function network."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        target, feats = _parse(body, allnames)
        if target is None or not feats:
            return [{"type": "Error", "text": "RBF needs 'target BY/WITH predictors'."}]

        def factory(clf):
            from sklearn.kernel_approximation import RBFSampler
            from sklearn.linear_model import LogisticRegression, Ridge
            from sklearn.pipeline import make_pipeline

            head = LogisticRegression(max_iter=1000) if clf else Ridge()
            return make_pipeline(RBFSampler(gamma=0.5, n_components=50, random_state=0), head)

        return _report("Radial Basis Function", target, feats, factory, ds)

"""Remaining Base procedures: PPLOT (P-P / Q-Q), RATIO STATISTICS, KAPPA."""
from __future__ import annotations

import math
import re
from typing import Any

import numpy as np

from ..data.format import Format
from ..data.missing import missing_mask
from ..output import charts as ch
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure
from . import stats
from .base import numeric_valid, strip_leading_zero

_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)


class Pplot(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = ""
        pp = False
        for name, b in subs:
            if name in ("", "VARIABLES"):
                body += " " + re.sub(r"^\s*VARIABLES\s*=?\s*", "", b, flags=re.IGNORECASE)
            elif name == "TYPE":
                pp = "P-P" in b.upper() or "PP" in b.upper()
        names = expand_varlist(body, [v.name for v in ds.variables])
        out: list[dict[str, Any]] = [{"type": "Title", "text": "PP Plots" if pp else "Q-Q Plots"}]
        for nm in names:
            x = numeric_valid(ds, nm)
            title = ("Normal P-P Plot of " if pp else "Normal Q-Q Plot of ") + (ds.variables[ds._index_of(nm)].label or nm)
            out.append(ch.qq(list(x), title=title, normal=not pp))
        return out


class RatioStats(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for n, b in subs if n in ("", "STATISTICS", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        m = re.search(r"(\w+)\s+WITH\s+(\w+)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "RATIO STATISTICS needs 'numerator WITH denominator'."}]
        num = expand_varlist(m.group(1), allnames)[0]
        den = expand_varlist(m.group(2), allnames)[0]
        keep = ~(missing_mask(ds.df[num], ds.variables[ds._index_of(num)]).to_numpy()
                 | missing_mask(ds.df[den], ds.variables[ds._index_of(den)]).to_numpy())
        n_ = ds.df[num].to_numpy(float)[keep]
        d_ = ds.df[den].to_numpy(float)[keep]
        ok = d_ != 0
        ratio = n_[ok] / d_[ok]
        median = float(np.median(ratio))
        mean = float(ratio.mean())
        wmean = float(n_[ok].sum() / d_[ok].sum())
        cod = float(100 * np.mean(np.abs(ratio - median)) / median) if median else float("nan")
        prd = float(mean / wmean) if wmean else float("nan")
        cov = float(100 * ratio.std(ddof=1) / mean) if mean else float("nan")
        t = PivotTable("Ratio Statistics",
                       [Dimension("", ["Median", "Mean", "Weighted Mean", "Minimum", "Maximum",
                                       "Coefficient of Dispersion", "Price Related Differential", "Coefficient of Variation (%)"])],
                       [Dimension("", ["Value"])])
        for i, val in enumerate([median, mean, wmean, float(ratio.min()), float(ratio.max()), cod, prd, cov]):
            t.set([i], [0], _F3.render(val))
        return [{"type": "Title", "text": "Ratio Statistics"}, t.to_json()]


class Kappa(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for n, b in subs if n in ("", "VARIABLES"))
        names = expand_varlist(re.sub(r"WITH", " ", body, flags=re.IGNORECASE), [v.name for v in ds.variables])
        if len(names) < 2:
            return [{"type": "Error", "text": "KAPPA needs two rating variables."}]
        a_name, b_name = names[0], names[1]
        keep = ~(missing_mask(ds.df[a_name], ds.variables[ds._index_of(a_name)]).to_numpy()
                 | missing_mask(ds.df[b_name], ds.variables[ds._index_of(b_name)]).to_numpy())
        a = ds.df[a_name].to_numpy()[keep]
        b = ds.df[b_name].to_numpy()[keep]
        from sklearn.metrics import cohen_kappa_score

        k = float(cohen_kappa_score(a, b))
        kw = float(cohen_kappa_score(a, b, weights="linear"))
        n = len(a)
        t = PivotTable("Symmetric Measures", [Dimension("", ["Cohen's Kappa", "Weighted Kappa (linear)", "N of Valid Cases"])],
                       [Dimension("", ["Value"])])
        t.set([0], [0], _F3.render(k)); t.set([1], [0], _F3.render(kw)); t.set([2], [0], _F0.render(n))
        return [{"type": "Title", "text": "Crosstabs"}, t.to_json()]

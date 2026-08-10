"""Bayesian Statistics (BAYES): one-sample / paired normal (unknown variance,
reference prior), one-sample binomial (Beta prior), one-sample Poisson (Gamma
prior). Reports posterior mean/SD and a 95% credible interval."""
from __future__ import annotations

import re
from typing import Any

import numpy as np

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure

_F3 = Format("F", 8, 3)


def _series(ds: Any, name: str) -> np.ndarray:
    s = ds.df[name]
    s = s.where(~missing_mask(s, ds.variables[ds._index_of(name)]))
    return s.dropna().to_numpy(float)


class Bayes(DataProcedure):
    """BAYES var[ var2] /TEST TYPE=NORMAL|BINOMIAL|POISSON [PAIRED]."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        names = expand_varlist(body, allnames)
        ttype = "NORMAL"
        paired = False
        for name, b in subs:
            if name.upper() in ("TEST", "MODEL"):
                mt = re.search(r"TYPE\s*=?\s*(\w+)", b, re.IGNORECASE)
                if mt:
                    ttype = mt.group(1).upper()
                if re.search(r"PAIRED", b, re.IGNORECASE):
                    paired = True
        if not names:
            return [{"type": "Error", "text": "BAYES needs a variable."}]

        from scipy import stats as sps

        if ttype == "BINOMIAL":
            x = _series(ds, names[0])
            k = float((x == x.max()).sum()) if len(np.unique(x)) <= 2 else float((x > 0).sum())
            n = len(x)
            a, b = 1 + k, 1 + (n - k)  # Beta(1,1) prior
            post_mean = a / (a + b)
            sd = np.sqrt(a * b / ((a + b) ** 2 * (a + b + 1)))
            lo, hi = sps.beta.ppf([0.025, 0.975], a, b)
            param = "Proportion"
        elif ttype == "POISSON":
            x = _series(ds, names[0])
            total = float(x.sum()); n = len(x)
            a, b = 1 + total, 1 + n  # Gamma(1,0) ~ reference; shape/rate
            post_mean = a / b
            sd = np.sqrt(a) / b
            lo, hi = sps.gamma.ppf([0.025, 0.975], a, scale=1 / b)
            param = "Rate"
        else:  # NORMAL mean with reference prior -> Student-t posterior
            if paired and len(names) >= 2:
                x = _series(ds, names[0]) - _series(ds, names[1])[: len(_series(ds, names[0]))]
            else:
                x = _series(ds, names[0])
            n = len(x)
            m = float(x.mean()); s = float(x.std(ddof=1))
            se = s / np.sqrt(n)
            post_mean = m
            sd = se * np.sqrt(n / (n - 2)) if n > 2 else se
            tcrit = sps.t.ppf(0.975, n - 1)
            lo, hi = m - tcrit * se, m + tcrit * se
            param = "Mean"

        t = PivotTable("Bayesian Estimates", [Dimension("", [param])],
                       [Dimension("", ["Posterior Mode/Mean", "Std. Deviation", "95% Lower", "95% Upper"])])
        t.set([0], [0], _F3.render(float(post_mean)))
        t.set([0], [1], _F3.render(float(sd)))
        t.set([0], [2], _F3.render(float(lo)))
        t.set([0], [3], _F3.render(float(hi)))
        return [{"type": "Title", "text": "Bayesian Statistics"}, t.to_json()]

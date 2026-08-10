"""Quality Control: Shewhart control charts (SPCHART) and Pareto charts
(PARETO). Charts are rendered by matplotlib in the sidecar."""
from __future__ import annotations

import re
from typing import Any

import numpy as np

from ..data.missing import missing_mask
from ..output import charts as ch
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure

# Control-chart constants for subgroup ranges (n = 2..10): A2, D3, D4.
_A2 = {2: 1.880, 3: 1.023, 4: 0.729, 5: 0.577, 6: 0.483, 7: 0.419, 8: 0.373, 9: 0.337, 10: 0.308}
_D3 = {2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0, 7: 0.076, 8: 0.136, 9: 0.184, 10: 0.223}
_D4 = {2: 3.267, 3: 2.574, 4: 2.282, 5: 2.114, 6: 2.004, 7: 1.924, 8: 1.864, 9: 1.816, 10: 1.777}


def _series(ds: Any, name: str) -> np.ndarray:
    s = ds.df[name]
    s = s.where(~missing_mask(s, ds.variables[ds._index_of(name)]))
    return s.dropna().to_numpy(float)


class SpChart(DataProcedure):
    """SPCHART var [BY subgroup] [/TYPE=XR|I] — X-bar/R or individuals chart."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        ctype = "I"
        for name, b in subs:
            if name.upper() == "TYPE":
                ctype = b.strip().upper() or "I"
        m = re.search(r"(\w+)\s+BY\s+(\w+)", body, re.IGNORECASE)
        out: list[dict[str, Any]] = [{"type": "Title", "text": "Control Charts"}]
        if m and ctype in ("XR", "XBAR"):
            var, sub = m.group(1), m.group(2)
            data = None
            import pandas as pd

            frame = {var: ds.df[var].where(~missing_mask(ds.df[var], ds.variables[ds._index_of(var)])),
                     sub: ds.df[sub]}
            data = pd.DataFrame(frame).dropna()
            groups = [g[var].to_numpy(float) for _, g in data.groupby(sub)]
            means = np.array([g.mean() for g in groups])
            ranges = np.array([g.max() - g.min() for g in groups])
            n = int(np.median([len(g) for g in groups]))
            n = min(max(n, 2), 10)
            xbar = means.mean(); rbar = ranges.mean()
            ucl = xbar + _A2[n] * rbar
            lcl = xbar - _A2[n] * rbar
            out.append(ch.control_chart(list(range(1, len(means) + 1)), means.tolist(), xbar, ucl, lcl,
                                        title="X-bar Chart", ylabel=f"Mean {var}"))
            out.append(ch.control_chart(list(range(1, len(ranges) + 1)), ranges.tolist(), rbar,
                                        _D4[n] * rbar, _D3[n] * rbar, title="R Chart", ylabel="Range"))
        else:
            var = expand_varlist(body.split(" BY ")[0], allnames)[0]
            x = _series(ds, var)
            cl = x.mean()
            # Moving-range estimate of sigma.
            mr = np.abs(np.diff(x)).mean() if len(x) > 1 else 0.0
            sigma = mr / 1.128 if mr else x.std(ddof=1)
            out.append(ch.control_chart(list(range(1, len(x) + 1)), x.tolist(), cl,
                                        cl + 3 * sigma, cl - 3 * sigma, title="Individuals Chart", ylabel=var))
        return out


class Pareto(DataProcedure):
    """PARETO var [BY category] — Pareto chart (sorted bars + cumulative line)."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        from .base import value_label
        import pandas as pd

        m = re.search(r"(\w+)\s+BY\s+(\w+)", body, re.IGNORECASE)
        if m:
            val, cat = m.group(1), m.group(2)
            frame = pd.DataFrame({val: ds.df[val], cat: ds.df[cat]}).dropna()
            agg = frame.groupby(cat)[val].sum().sort_values(ascending=False)
            labels = [value_label(ds, cat, x) for x in agg.index]
            values = agg.to_numpy(float)
        else:
            var = expand_varlist(body, allnames)[0]
            counts = ds.df[var].dropna().value_counts()
            labels = [value_label(ds, var, x) for x in counts.index]
            values = counts.to_numpy(float)
        return [{"type": "Title", "text": "Pareto Charts"},
                ch.pareto(labels, values.tolist(), title="Pareto Chart")]

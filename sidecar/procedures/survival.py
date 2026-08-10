"""Survival analysis: Life Tables (SURVIVAL), Kaplan-Meier (KM), Cox Regression
(COXREG). statsmodels-backed (no extra dependency)."""
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
from .base import strip_leading_zero

_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)


def _clean(ds: Any, names: list[str]) -> pd.DataFrame:
    frame = {}
    for nm in names:
        s = ds.df[nm]
        frame[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
    return pd.DataFrame(frame).dropna()


def _status(series: pd.Series, event_spec: str) -> np.ndarray:
    """event_spec like '1' — coded 1 == event, else censored."""
    ev = float(re.search(r"-?\d+(\.\d+)?", event_spec).group()) if re.search(r"\d", event_spec) else 1.0
    return (series.to_numpy(float) == ev).astype(int)


class KaplanMeier(DataProcedure):
    """KM time BY factor /STATUS=status(event) — survival table + median."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        status, event = None, "1"
        for name, b in subs:
            if name.upper() == "STATUS":
                m = re.match(r"\s*(\w+)\s*\(([^)]*)\)", b)
                if m:
                    status, event = m.group(1), m.group(2)
                else:
                    status = expand_varlist(b, allnames)[0]
        mby = re.search(r"(.+?)\bBY\b(.+)", body, re.IGNORECASE)
        if mby:
            timev = expand_varlist(mby.group(1), allnames)[0]
            factor = expand_varlist(mby.group(2), allnames)[0]
        else:
            timev = expand_varlist(body, allnames)[0]
            factor = None
        if status is None:
            return [{"type": "Error", "text": "KM needs /STATUS=var(event)."}]
        cols = [timev, status] + ([factor] if factor else [])
        data = _clean(ds, cols)
        from statsmodels.duration.survfunc import SurvfuncRight

        groups = sorted(data[factor].unique()) if factor else [None]
        rows = [str(g) if g is not None else "Overall" for g in groups]
        t = PivotTable("Survival Table", [Dimension("Group", rows)],
                       [Dimension("", ["N", "Events", "Censored", "Median Survival"])])
        for i, g in enumerate(groups):
            sub = data if g is None else data[data[factor] == g]
            time = sub[timev].to_numpy(float)
            evt = _status(sub[status], event)
            sf = SurvfuncRight(time, evt)
            n = len(sub); ev = int(evt.sum())
            # median survival = smallest time with S(t) <= 0.5
            surv = sf.surv_prob
            times = sf.surv_times
            med = float("nan")
            below = np.where(surv <= 0.5)[0]
            if len(below):
                med = float(times[below[0]])
            t.set([i], [0], _F0.render(n))
            t.set([i], [1], _F0.render(ev))
            t.set([i], [2], _F0.render(n - ev))
            t.set([i], [3], _F3.render(med) if med == med else "")

        out = [{"type": "Title", "text": "Kaplan-Meier"}, t.to_json()]
        # Log-rank test across groups.
        if factor and len(groups) > 1:
            from statsmodels.duration.survfunc import survdiff

            chi, p = survdiff(data[timev].to_numpy(float), _status(data[status], event),
                              data[factor].to_numpy())
            lr = PivotTable("Overall Comparisons", [Dimension("", ["Log Rank (Mantel-Cox)"])],
                            [Dimension("", ["Chi-Square", "df", "Sig."])])
            lr.set([0], [0], _F3.render(float(chi)))
            lr.set([0], [1], _F0.render(len(groups) - 1))
            lr.set([0], [2], strip_leading_zero(_F3.render(float(p))))
            out.append(lr.to_json())
        return out


class CoxReg(DataProcedure):
    """COXREG time WITH covars /STATUS=status(event) — Cox proportional hazards."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        status, event = None, "1"
        for name, b in subs:
            if name.upper() == "STATUS":
                m = re.match(r"\s*(\w+)\s*\(([^)]*)\)", b)
                if m:
                    status, event = m.group(1), m.group(2)
                else:
                    status = expand_varlist(b, allnames)[0]
        mw = re.search(r"(.+?)\bWITH\b(.+)", body, re.IGNORECASE)
        if not mw or status is None:
            return [{"type": "Error", "text": "COXREG needs 'time WITH covars /STATUS=var(event)'."}]
        timev = expand_varlist(mw.group(1), allnames)[0]
        covars = expand_varlist(mw.group(2), allnames)
        data = _clean(ds, [timev, status] + covars)
        from statsmodels.duration.hazard_regression import PHReg
        from scipy import stats as sps

        model = PHReg(data[timev].to_numpy(float), data[covars].to_numpy(float),
                      status=_status(data[status], event)).fit()
        b = np.asarray(model.params); se = np.asarray(model.bse)
        t = PivotTable("Variables in the Equation", [Dimension("", covars)],
                       [Dimension("", ["B", "SE", "Wald", "Sig.", "Exp(B)"])])
        for i, _ in enumerate(covars):
            wald = (b[i] / se[i]) ** 2
            t.set([i], [0], _F3.render(float(b[i])))
            t.set([i], [1], _F3.render(float(se[i])))
            t.set([i], [2], _F3.render(float(wald)))
            t.set([i], [3], strip_leading_zero(_F3.render(float(sps.chi2.sf(wald, 1)))))
            t.set([i], [4], _F3.render(float(np.exp(b[i]))))
        return [{"type": "Title", "text": "Cox Regression"}, t.to_json()]


class LifeTable(DataProcedure):
    """SURVIVAL TABLE=time /INTERVAL=THRU hi BY width /STATUS=status(event)
    — actuarial life table."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        allnames = [v.name for v in ds.variables]
        timev = None
        status, event = None, "1"
        hi, width = None, None
        for name, b in subs:
            u = name.upper()
            if u in ("TABLE", "VARIABLES", ""):
                b = re.sub(r"^\s*TABLE\s*=\s*", "", b, flags=re.IGNORECASE)
                got = expand_varlist(b, allnames)
                if got and timev is None:
                    timev = got[0]
            elif u == "STATUS":
                m = re.match(r"\s*(\w+)\s*\(([^)]*)\)", b)
                if m:
                    status, event = m.group(1), m.group(2)
            elif u == "INTERVAL":
                mh = re.search(r"THRU\s+([\d.]+)\s+BY\s+([\d.]+)", b, re.IGNORECASE)
                if mh:
                    hi, width = float(mh.group(1)), float(mh.group(2))
        if timev is None or status is None:
            return [{"type": "Error", "text": "SURVIVAL needs TABLE=time /STATUS=var(event) /INTERVAL=THRU hi BY w."}]
        data = _clean(ds, [timev, status])
        time = data[timev].to_numpy(float)
        evt = _status(data[status], event)
        if hi is None:
            hi = float(time.max())
        if not width:
            width = hi / 10 or 1.0
        edges = np.arange(0, hi + width, width)
        rows = [f"{edges[i]:.0f}–{edges[i+1]:.0f}" for i in range(len(edges) - 1)]
        t = PivotTable("Life Table", [Dimension("Interval Start Time", rows)],
                       [Dimension("", ["Entering", "Terminal Events", "Withdrawn", "Prop. Surviving", "Cum. Surviving"])])
        n_at_risk = len(time)
        cum = 1.0
        for i in range(len(edges) - 1):
            lo, up = edges[i], edges[i + 1]
            in_int = (time >= lo) & (time < up)
            deaths = int(evt[in_int].sum())
            withdrawn = int((~evt.astype(bool) & in_int).sum())
            eff = n_at_risk - withdrawn / 2
            q = deaths / eff if eff else 0.0
            p = 1 - q
            t.set([i], [0], _F0.render(n_at_risk))
            t.set([i], [1], _F0.render(deaths))
            t.set([i], [2], _F0.render(withdrawn))
            t.set([i], [3], _F3.render(p))
            cum *= p
            t.set([i], [4], _F3.render(cum))
            n_at_risk -= int(in_int.sum())
            if n_at_risk <= 0:
                break
        return [{"type": "Title", "text": "Life Tables"}, t.to_json()]

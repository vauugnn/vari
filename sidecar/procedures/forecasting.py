"""Forecasting: ARIMA (TSMODEL), Seasonal Decomposition (SEASON), Spectral
Analysis (SPECTRA). statsmodels/numpy-backed."""
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


def _series(ds: Any, name: str) -> np.ndarray:
    s = ds.df[name]
    s = s.where(~missing_mask(s, ds.variables[ds._index_of(name)]))
    return s.dropna().to_numpy(float)


class Arima(DataProcedure):
    """TSMODEL var /ARIMA p d q [SEASONAL P D Q period] — fits ARIMA."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        var = expand_varlist(body, allnames)[0]
        order = (1, 0, 0)
        for name, b in subs:
            if name.upper() == "ARIMA":
                nums = [int(x) for x in re.findall(r"\d+", b)][:3]
                if len(nums) == 3:
                    order = tuple(nums)
        y = _series(ds, var)
        from statsmodels.tsa.arima.model import ARIMA as SM_ARIMA

        res = SM_ARIMA(y, order=order).fit()
        params = res.params
        names = list(res.param_names)
        se = res.bse
        from scipy import stats as sps

        t = PivotTable("ARIMA Model Parameters", [Dimension("", names)],
                       [Dimension("", ["Estimate", "SE", "t", "Sig."])],
                       caption=f"{var}: ARIMA{order}")
        for i, _ in enumerate(names):
            tv = params[i] / se[i] if se[i] else float("nan")
            t.set([i], [0], _F3.render(float(params[i])))
            t.set([i], [1], _F3.render(float(se[i])))
            t.set([i], [2], _F3.render(float(tv)))
            t.set([i], [3], strip_leading_zero(_F3.render(float(2 * sps.norm.sf(abs(tv))))))
        fit = PivotTable("Model Fit", [Dimension("", ["Log Likelihood", "AIC", "BIC"])],
                         [Dimension("", ["Value"])])
        fit.set([0], [0], _F3.render(float(res.llf)))
        fit.set([1], [0], _F3.render(float(res.aic)))
        fit.set([2], [0], _F3.render(float(res.bic)))
        return [{"type": "Title", "text": "Time Series Modeler"}, fit.to_json(), t.to_json()]


class Season(DataProcedure):
    """SEASON var /PERIOD n — classical seasonal decomposition."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        var = expand_varlist(body, allnames)[0]
        period = 12
        for name, b in subs:
            if name.upper() == "PERIOD":
                m = re.search(r"\d+", b)
                if m:
                    period = int(m.group())
        y = _series(ds, var)
        from statsmodels.tsa.seasonal import seasonal_decompose

        res = seasonal_decompose(y, period=period, model="additive", extrapolate_trend="freq")
        # New series added to the dataset (SPSS SEASON saves SAS_, STC_, etc.).
        from .transforms import _set_column

        n = len(ds.df)

        def _pad(a):
            out = np.full(n, np.nan)
            out[: len(a)] = a
            return out

        _set_column(ds, f"SAS_{var}"[:60], _pad(res.seasonal))
        _set_column(ds, f"STC_{var}"[:60], _pad(res.trend))
        _set_column(ds, f"ERR_{var}"[:60], _pad(res.resid))
        from ..syntax.registry import Context  # noqa: F401

        summary = PivotTable("Seasonal Decomposition", [Dimension("", ["Seasonal (SAS_)", "Trend-Cycle (STC_)", "Error (ERR_)"])],
                             [Dimension("", ["Saved As"])])
        summary.set([0], [0], f"SAS_{var}"[:60])
        summary.set([1], [0], f"STC_{var}"[:60])
        summary.set([2], [0], f"ERR_{var}"[:60])
        return [{"type": "Title", "text": "Seasonal Decomposition"}, summary.to_json(),
                {"type": "_DatasetChanged", "summary": ds_summary(ds)}]


class Spectra(DataProcedure):
    """SPECTRA var — periodogram (top spectral peaks)."""

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for name, b in subs if name in ("", "VARIABLES"))
        allnames = [v.name for v in ds.variables]
        var = expand_varlist(body, allnames)[0]
        y = _series(ds, var)
        y = y - y.mean()
        n = len(y)
        fft = np.fft.rfft(y)
        power = (np.abs(fft) ** 2) / n
        freqs = np.fft.rfftfreq(n, d=1.0)
        # Report the strongest peaks (skip the zero-frequency term).
        idx = np.argsort(power[1:])[::-1][:10] + 1
        rows = [f"{1/freqs[i]:.2f}" if freqs[i] else "inf" for i in idx]
        t = PivotTable("Periodogram (top peaks)", [Dimension("Period", rows)],
                       [Dimension("", ["Frequency", "Periodogram"])])
        for r, i in enumerate(idx):
            t.set([r], [0], _F3.render(float(freqs[i])))
            t.set([r], [1], _F3.render(float(power[i])))
        return [{"type": "Title", "text": "Spectral Analysis"}, t.to_json()]


def ds_summary(ds: Any) -> dict[str, Any]:
    # Local import avoids a circular import at module load.
    from ..server import _dataset_summary

    return _dataset_summary(ds)

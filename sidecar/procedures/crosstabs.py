"""CROSSTABS — contingency table + chi-square tests (HLD 6/9).

SPSS reports Pearson, Likelihood Ratio, and Linear-by-Linear; continuity
correction and Fisher's exact only for 2x2 tables.
"""
from __future__ import annotations

import math
import re
from typing import Any, Optional

import numpy as np
import pandas as pd
from scipy import stats as sps

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.registry import DataProcedure
from .base import get_weights, strip_leading_zero, value_label

_F0 = Format("F", 8, 0)
_F1 = Format("F", 8, 1)
_F3 = Format("F", 8, 3)


class Crosstabs(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        tables_body = ""
        want_chisq = False
        measures: set[str] = set()
        cells = ["COUNT"]
        for name, body in subs:
            if name in ("", "TABLES"):
                tables_body += " " + re.sub(r"^\s*TABLES\s*=?\s*", "", body, flags=re.IGNORECASE)
            elif name == "STATISTICS":
                up = body.upper()
                if "CHISQ" in up or "ALL" in up:
                    want_chisq = True
                for kw in ("PHI", "CC", "GAMMA", "BTAU", "CTAU", "LAMBDA"):
                    if kw in up or "ALL" in up:
                        measures.add(kw)
            elif name == "CELLS":
                up = body.upper().split()
                cells = ["COUNT"] + [c for c in ["EXPECTED", "ROW", "COLUMN", "TOTAL"] if c in up]

        m = re.search(r"(.+?)\bBY\b(.+)", tables_body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "CROSSTABS /TABLES needs 'row BY col'."}]
        rows = _names(ds, m.group(1))
        colv = _names(ds, m.group(2))
        out: list[dict[str, Any]] = [{"type": "Title", "text": "Crosstabs"}]
        for rv in rows:
            for cv in colv:
                out.extend(self._one(ds, rv, cv, cells, want_chisq, measures))
        return out

    def _one(self, ds: Any, rv: str, cv: str, cells: list[str], want_chisq: bool,
             measures: set[str] = frozenset()) -> list[dict[str, Any]]:
        rmeta, cmeta = ds.variables[ds._index_of(rv)], ds.variables[ds._index_of(cv)]
        valid = ~(missing_mask(ds.df[rv], rmeta).to_numpy() | missing_mask(ds.df[cv], cmeta).to_numpy())
        r = ds.df[rv].to_numpy()[valid]
        c = ds.df[cv].to_numpy()[valid]
        w = get_weights(ds)
        if w is not None:
            ct = pd.crosstab(r, c, values=w[valid], aggfunc="sum").fillna(0)
        else:
            ct = pd.crosstab(r, c)
        ct = ct.sort_index(axis=0).sort_index(axis=1)
        row_vals = list(ct.index)
        col_vals = list(ct.columns)
        obs = ct.to_numpy(dtype=float)
        n = obs.sum()
        expected = np.outer(obs.sum(1), obs.sum(0)) / n if n else obs

        rlabels = [value_label(ds, rv, v) for v in row_vals] + ["Total"]
        clabels = [value_label(ds, cv, v) for v in col_vals] + ["Total"]
        stat_names = {"COUNT": "Count", "EXPECTED": "Expected Count", "ROW": "% within " + (rmeta.label or rv),
                      "COLUMN": "% within " + (cmeta.label or cv), "TOTAL": "% of Total"}
        stats = [stat_names[c_] for c_ in cells]

        t = PivotTable(
            f"{rmeta.label or rv} * {cmeta.label or cv} Crosstabulation",
            [Dimension(rmeta.label or rv, rlabels), Dimension("", stats)],
            [Dimension(cmeta.label or cv, clabels)],
            corner=rmeta.label or rv,
        )
        col_tot = obs.sum(0)
        row_tot = obs.sum(1)
        for i in range(len(rlabels)):
            for j in range(len(clabels)):
                for s, cellkind in enumerate(cells):
                    val = _cell_value(cellkind, obs, expected, row_tot, col_tot, n, i, j, len(row_vals), len(col_vals))
                    t.set([i, s], [j], val, "num")
        result = [t.to_json()]
        if want_chisq:
            result.append(self._chisq(obs, n))
        if measures:
            result.append(self._measures(obs, n, measures))
        return result

    def _measures(self, obs: np.ndarray, n: float, want: set[str]) -> dict[str, Any]:
        rws, cls = obs.shape
        chi2, _, dof, _ = sps.chi2_contingency(obs, correction=False)
        p_chi = float(sps.chi2.sf(chi2, dof))
        entries: list[tuple[str, str, float, Optional[float]]] = []  # (group, name, value, sig)
        if "PHI" in want:
            phi = math.sqrt(chi2 / n)
            v = math.sqrt(chi2 / (n * (min(rws, cls) - 1))) if min(rws, cls) > 1 else float("nan")
            entries.append(("Nominal by Nominal", "Phi", phi, p_chi))
            entries.append(("Nominal by Nominal", "Cramer's V", v, p_chi))
        if "CC" in want:
            cc = math.sqrt(chi2 / (chi2 + n))
            entries.append(("Nominal by Nominal", "Contingency Coefficient", cc, p_chi))
        if want & {"GAMMA", "BTAU", "CTAU"}:
            g, tb, tc = _ordinal_measures(obs, n)
            if "GAMMA" in want:
                entries.append(("Ordinal by Ordinal", "Gamma", g, None))
            if "BTAU" in want:
                entries.append(("Ordinal by Ordinal", "Kendall's tau-b", tb, None))
            if "CTAU" in want:
                entries.append(("Ordinal by Ordinal", "Kendall's tau-c", tc, None))

        rowlabels = [f"{grp}|{nm}" for grp, nm, _, _ in entries] + ["N of Valid Cases"]
        t = PivotTable("Symmetric Measures", [Dimension("", rowlabels)],
                       [Dimension("", ["Value", "Approx. Sig."])])
        for i, (_, _, val, sig) in enumerate(entries):
            t.set([i], [0], _F3.render(val) if val == val else ".")
            t.set([i], [1], strip_leading_zero(_F3.render(sig)) if sig is not None else "")
        t.set([len(entries)], [0], _F0.render(int(n)))
        return t.to_json()

    def _chisq(self, obs: np.ndarray, n: float) -> dict[str, Any]:
        is2x2 = obs.shape == (2, 2)
        rows = ["Pearson Chi-Square"]
        if is2x2:
            rows.append("Continuity Correction")
        rows += ["Likelihood Ratio"]
        if is2x2:
            rows.append("Fisher's Exact Test")
        rows += ["Linear-by-Linear Association", "N of Valid Cases"]
        cols = ["Value", "df", "Asymptotic Significance (2-sided)", "Exact Sig. (2-sided)", "Exact Sig. (1-sided)"]
        t = PivotTable("Chi-Square Tests", [Dimension("", rows)], [Dimension("", cols)])

        chi2, p, dof, _ = sps.chi2_contingency(obs, correction=False)
        g2, gp, _, _ = sps.chi2_contingency(obs, lambda_="log-likelihood")
        ri = {name: i for i, name in enumerate(rows)}

        def put(row, col, val):
            t.set([ri[row]], [cols.index(col)], val, "num")

        put("Pearson Chi-Square", "Value", _F3.render(float(chi2)))
        put("Pearson Chi-Square", "df", _F0.render(int(dof)))
        put("Pearson Chi-Square", "Asymptotic Significance (2-sided)", strip_leading_zero(_F3.render(float(p))))
        put("Likelihood Ratio", "Value", _F3.render(float(g2)))
        put("Likelihood Ratio", "df", _F0.render(int(dof)))
        put("Likelihood Ratio", "Asymptotic Significance (2-sided)", strip_leading_zero(_F3.render(float(gp))))
        if is2x2:
            cc, ccp, _, _ = sps.chi2_contingency(obs, correction=True)
            put("Continuity Correction", "Value", _F3.render(float(cc)))
            put("Continuity Correction", "df", _F0.render(1))
            put("Continuity Correction", "Asymptotic Significance (2-sided)", strip_leading_zero(_F3.render(float(ccp))))
            _, fp = sps.fisher_exact(obs)
            put("Fisher's Exact Test", "Exact Sig. (2-sided)", strip_leading_zero(_F3.render(float(fp))))
        # Linear-by-linear: (n-1) r^2 with the numeric category codes
        lbl = _linear_by_linear(obs)
        put("Linear-by-Linear Association", "Value", _F3.render(lbl[0]))
        put("Linear-by-Linear Association", "df", _F0.render(1))
        put("Linear-by-Linear Association", "Asymptotic Significance (2-sided)", strip_leading_zero(_F3.render(lbl[1])))
        put("N of Valid Cases", "Value", _F0.render(int(n)))
        return t.to_json()


def _cell_value(kind, obs, expected, row_tot, col_tot, n, i, j, nr, nc):
    is_row_tot = i == nr
    is_col_tot = j == nc
    if kind == "COUNT":
        if is_row_tot and is_col_tot:
            return _F0.render(int(n))
        if is_row_tot:
            return _F0.render(int(col_tot[j]))
        if is_col_tot:
            return _F0.render(int(row_tot[i]))
        return _F0.render(int(obs[i, j]))
    if kind == "EXPECTED":
        if is_row_tot or is_col_tot:
            return ""
        return _F1.render(float(expected[i, j]))
    if kind == "ROW":
        denom = n if is_row_tot else row_tot[i]
        num = (col_tot[j] if is_row_tot else (row_tot[i] if is_col_tot else obs[i, j]))
        return _F1.render(100.0 * num / denom) if denom else ""
    if kind == "COLUMN":
        denom = n if is_col_tot else col_tot[j]
        num = (row_tot[i] if is_col_tot else (col_tot[j] if is_row_tot else obs[i, j]))
        return _F1.render(100.0 * num / denom) if denom else ""
    if kind == "TOTAL":
        num = n if (is_row_tot and is_col_tot) else (col_tot[j] if is_row_tot else (row_tot[i] if is_col_tot else obs[i, j]))
        return _F1.render(100.0 * num / n) if n else ""
    return ""


def _linear_by_linear(obs: np.ndarray) -> tuple[float, float]:
    rows, cols = obs.shape
    ri = np.arange(1, rows + 1)
    ci = np.arange(1, cols + 1)
    xs, ys, ws = [], [], []
    for i in range(rows):
        for j in range(cols):
            if obs[i, j]:
                xs.append(ri[i])
                ys.append(ci[j])
                ws.append(obs[i, j])
    xs, ys, ws = np.array(xs, float), np.array(ys, float), np.array(ws, float)
    n = ws.sum()
    mx = np.average(xs, weights=ws)
    my = np.average(ys, weights=ws)
    cov = np.sum(ws * (xs - mx) * (ys - my))
    vx = np.sum(ws * (xs - mx) ** 2)
    vy = np.sum(ws * (ys - my) ** 2)
    r = cov / np.sqrt(vx * vy) if vx > 0 and vy > 0 else 0.0
    stat = (n - 1) * r * r
    p = float(sps.chi2.sf(stat, 1))
    return float(stat), p


def _names(ds: Any, body: str) -> list[str]:
    from ..syntax.lexer import expand_varlist

    return expand_varlist(body, [v.name for v in ds.variables])


def _ordinal_measures(obs: np.ndarray, n: float) -> tuple[float, float, float]:
    """Gamma, Kendall's tau-b, tau-c from an ordered contingency table."""
    r, c = obs.shape
    C = D = 0.0
    for i in range(r):
        for j in range(c):
            conc = obs[i + 1 :, j + 1 :].sum() + obs[:i, :j].sum()
            disc = obs[i + 1 :, :j].sum() + obs[:i, j + 1 :].sum()
            C += obs[i, j] * conc
            D += obs[i, j] * disc
    C /= 2.0
    D /= 2.0
    gamma = (C - D) / (C + D) if (C + D) else float("nan")
    row_tot = obs.sum(1)
    col_tot = obs.sum(0)
    n0 = n * (n - 1) / 2.0
    n1 = sum(t * (t - 1) / 2.0 for t in row_tot)
    n2 = sum(t * (t - 1) / 2.0 for t in col_tot)
    denom = math.sqrt((n0 - n1) * (n0 - n2))
    tau_b = (C - D) / denom if denom else float("nan")
    m = min(r, c)
    tau_c = (2 * m * (C - D)) / (n * n * (m - 1)) if m > 1 else float("nan")
    return float(gamma), float(tau_b), float(tau_c)

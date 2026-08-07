"""FACTOR — principal-components extraction with KMO, Bartlett, communalities,
total variance explained, component matrix, and varimax rotation (HLD 6 Tier 2)."""
from __future__ import annotations

import math
import re
from typing import Any

import numpy as np

from ..data.format import Format
from ..data.missing import missing_mask
from ..output.model import Dimension, PivotTable
from ..syntax.lexer import expand_varlist
from ..syntax.registry import DataProcedure
from .base import strip_leading_zero

_F3 = Format("F", 8, 3)
_F0 = Format("F", 8, 0)
_F2 = Format("F", 8, 2)


def _kmo(R: np.ndarray) -> float:
    inv = np.linalg.pinv(R)
    d = np.sqrt(np.diag(inv))
    partial = -inv / np.outer(d, d)
    np.fill_diagonal(partial, 0)
    off = ~np.eye(R.shape[0], dtype=bool)
    sr = (R[off] ** 2).sum()
    sp = (partial[off] ** 2).sum()
    return float(sr / (sr + sp)) if (sr + sp) else float("nan")


def varimax(phi: np.ndarray, q: int = 30, tol: float = 1e-6) -> np.ndarray:
    p, k = phi.shape
    if k < 2:
        return phi
    rot = np.eye(k)
    dsum = 0.0
    for _ in range(q):
        d_old = dsum
        L = phi @ rot
        u, s, vt = np.linalg.svd(phi.T @ (L**3 - (1.0 / p) * L @ np.diag(np.diag(L.T @ L))))
        rot = u @ vt
        dsum = float(s.sum())
        if d_old != 0 and dsum / d_old < 1 + tol:
            break
    return phi @ rot


class Factor(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = ""
        rotate = False
        for name, b in subs:
            if name in ("", "VARIABLES"):
                body += " " + re.sub(r"^\s*VARIABLES\s*=?\s*", "", b, flags=re.IGNORECASE)
            elif name == "ROTATION":
                rotate = "VARIMAX" in b.upper()
        names = expand_varlist(body, [v.name for v in ds.variables])
        if len(names) < 2:
            return [{"type": "Error", "text": "FACTOR requires at least two variables."}]

        cols = {}
        for nm in names:
            s = ds.df[nm]
            cols[nm] = s.where(~missing_mask(s, ds.variables[ds._index_of(nm)]))
        import pandas as pd

        data = pd.DataFrame(cols).dropna()
        X = data.to_numpy(float)
        n, p = X.shape
        R = np.corrcoef(X, rowvar=False)

        eigvals, eigvecs = np.linalg.eigh(R)
        order = np.argsort(eigvals)[::-1]
        eigvals = eigvals[order]
        eigvecs = eigvecs[:, order]
        loadings = eigvecs * np.sqrt(np.clip(eigvals, 0, None))
        retain = int((eigvals > 1).sum()) or 1
        comp = loadings[:, :retain]
        communal = (comp**2).sum(axis=1)

        out: list[dict[str, Any]] = [{"type": "Title", "text": "Factor Analysis"}]

        # KMO and Bartlett
        kmo = _kmo(R)
        det = np.linalg.det(R)
        chi = -(n - 1 - (2 * p + 5) / 6) * math.log(det) if det > 0 else float("nan")
        dfree = p * (p - 1) // 2
        from scipy import stats as sps

        p_bart = float(sps.chi2.sf(chi, dfree)) if chi == chi else float("nan")
        kb = PivotTable("KMO and Bartlett's Test",
                        [Dimension("", ["Kaiser-Meyer-Olkin Measure", "Bartlett Approx. Chi-Square", "Bartlett df", "Bartlett Sig."])],
                        [Dimension("", ["Value"])])
        kb.set([0], [0], _F3.render(kmo)); kb.set([1], [0], _F3.render(float(chi)) if chi == chi else ".")
        kb.set([2], [0], _F0.render(dfree)); kb.set([3], [0], strip_leading_zero(_F3.render(p_bart)))
        out.append(kb.to_json())

        # Communalities
        comm = PivotTable("Communalities", [Dimension("", list(names))], [Dimension("", ["Initial", "Extraction"])])
        for i, nm in enumerate(names):
            comm.set([i], [0], _F3.render(1.0)); comm.set([i], [1], _F3.render(float(communal[i])))
        out.append(comm.to_json())

        # Total Variance Explained
        tve = PivotTable("Total Variance Explained", [Dimension("", [f"{i + 1}" for i in range(p)])],
                         [Dimension("", ["Eigenvalue", "% of Variance", "Cumulative %"])], corner="Component")
        cum = 0.0
        for i in range(p):
            pct = 100.0 * eigvals[i] / p
            cum += pct
            tve.set([i], [0], _F3.render(float(eigvals[i]))); tve.set([i], [1], _F3.render(pct))
            tve.set([i], [2], _F3.render(cum))
        out.append(tve.to_json())

        # Component Matrix
        out.append(self._loading_table("Component Matrix", names, comp, retain))
        if rotate and retain > 1:
            out.append(self._loading_table("Rotated Component Matrix", names, varimax(comp), retain))
        return out

    def _loading_table(self, title, names, mat, retain):
        t = PivotTable(title, [Dimension("", list(names))],
                       [Dimension("Component", [f"{i + 1}" for i in range(retain)])], corner="")
        for i in range(len(names)):
            for j in range(retain):
                t.set([i], [j], _F3.render(float(mat[i, j])))
        return t.to_json()

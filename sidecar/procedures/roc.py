"""ROC — ROC curve + Area Under the Curve (HLD 6, Base)."""
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
from .base import strip_leading_zero

_F3 = Format("F", 8, 3)


class Roc(DataProcedure):
    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        body = " ".join(b for n, b in subs if n in ("", "VARIABLES")) or \
               " ".join(f"{n} {b}" for n, b in subs)
        allnames = [v.name for v in ds.variables]
        m = re.search(r"(.+?)\bBY\b\s*(\w+)\s*\(([^)]*)\)", body, re.IGNORECASE)
        if not m:
            return [{"type": "Error", "text": "ROC needs 'testvar BY state(value)'."}]
        tests = expand_varlist(m.group(1), allnames)
        state = expand_varlist(m.group(2), allnames)[0]
        pos = float(m.group(3).strip())

        from sklearn.metrics import roc_auc_score, roc_curve

        out: list[dict[str, Any]] = [{"type": "Title", "text": "ROC Curve"}]
        auc_t = PivotTable("Area Under the Curve", [Dimension("Test Result Variable(s)", list(tests))],
                           [Dimension("", ["Area", "Std. Error", "Asymptotic Sig.", "Lower Bound", "Upper Bound"])],
                           corner="")
        for i, tv in enumerate(tests):
            keep = ~(missing_mask(ds.df[tv], ds.variables[ds._index_of(tv)]).to_numpy()
                     | missing_mask(ds.df[state], ds.variables[ds._index_of(state)]).to_numpy())
            score = ds.df[tv].to_numpy(float)[keep]
            y = (ds.df[state].to_numpy(float)[keep] == pos).astype(int)
            if y.sum() == 0 or y.sum() == len(y):
                continue
            auc = float(roc_auc_score(y, score))
            se = _auc_se(auc, int(y.sum()), int((1 - y).sum()))
            z = (auc - 0.5) / se if se else float("nan")
            from scipy import stats as sps

            sig = float(2 * sps.norm.sf(abs(z))) if z == z else float("nan")
            lo, hi = auc - 1.96 * se, auc + 1.96 * se
            auc_t.set([i], [0], _F3.render(auc)); auc_t.set([i], [1], _F3.render(se))
            auc_t.set([i], [2], strip_leading_zero(_F3.render(sig)))
            auc_t.set([i], [3], _F3.render(max(0, lo))); auc_t.set([i], [4], _F3.render(min(1, hi)))
            fpr, tpr, _ = roc_curve(y, score)
            out.append(ch.line(list(fpr), list(tpr), title=f"ROC Curve: {tv}", xlabel="1 - Specificity", ylabel="Sensitivity", diagonal=True))
        out.insert(1, auc_t.to_json())
        return out


def _auc_se(auc: float, n_pos: int, n_neg: int) -> float:
    q1 = auc / (2 - auc)
    q2 = 2 * auc * auc / (1 + auc)
    num = auc * (1 - auc) + (n_pos - 1) * (q1 - auc**2) + (n_neg - 1) * (q2 - auc**2)
    return math.sqrt(num / (n_pos * n_neg)) if n_pos and n_neg else float("nan")

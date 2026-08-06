"""Data-menu commands: SORT CASES, SELECT IF, FILTER, WEIGHT, SPLIT FILE.

SELECT IF permanently deletes non-matching cases. FILTER BY marks a filter
variable (cases with 0 or missing are excluded, non-destructively). WEIGHT BY
and SPLIT FILE set dataset state that the procedure base weaves in.
"""
from __future__ import annotations

import re
from typing import Any

import numpy as np

from ..expr.evaluate import EvalContext, evaluate
from ..expr.parser import parse_expression
from ..syntax.lexer import expand_varlist
from ..syntax.registry import Context, Procedure


class SortCases(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        body = re.sub(r"^\s*CASES\s*", "", rest, flags=re.IGNORECASE)
        body = re.sub(r"^\s*BY\s*", "", body, flags=re.IGNORECASE)
        keys, orders = [], []
        # tokens like: var (A)  var2 (D)
        for m in re.finditer(r"([A-Za-z@#$][\w@#$.]*)\s*(\(\s*([ADad])\s*\))?", body):
            nm = m.group(1)
            if not nm:
                continue
            keys.append(nm)
            orders.append((m.group(3) or "A").upper() != "D")
        keys = expand_varlist(" ".join(keys), [v.name for v in ds.variables]) if keys else []
        if keys:
            ds.df = ds.df.sort_values(by=keys, ascending=orders if len(orders) == len(keys) else True,
                                      kind="mergesort").reset_index(drop=True)
            ctx.mark_changed()
        return []


class SelectIf(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        cond = re.sub(r"^\s*IF\s*", "", rest.strip(), flags=re.IGNORECASE)
        cond = re.sub(r"^\s*\(|\)\s*$", "", cond.strip())
        vals = evaluate(parse_expression(cond), EvalContext(ds))
        keep = (vals == 1.0) & ~np.isnan(vals)
        ds.df = ds.df[keep].reset_index(drop=True)
        ctx.mark_changed()
        return []


class Filter(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        if re.search(r"\bOFF\b", rest, re.IGNORECASE):
            ds.filter_var = None
        else:
            m = re.search(r"BY\s+([A-Za-z@#$][\w@#$.]*)", rest, re.IGNORECASE)
            if m:
                ds.filter_var = expand_varlist(m.group(1), [v.name for v in ds.variables])[0]
        ctx.mark_changed()
        return []


class Weight(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        if re.search(r"\bOFF\b", rest, re.IGNORECASE):
            ds.weight_var = None
        else:
            m = re.search(r"BY\s+([A-Za-z@#$][\w@#$.]*)", rest, re.IGNORECASE)
            if m:
                ds.weight_var = expand_varlist(m.group(1), [v.name for v in ds.variables])[0]
        ctx.mark_changed()
        return []


class SplitFile(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        if re.search(r"\bOFF\b", rest, re.IGNORECASE):
            ds.split_vars = []
        else:
            m = re.search(r"BY\s+(.+)$", rest, re.IGNORECASE | re.DOTALL)
            if m:
                ds.split_vars = expand_varlist(m.group(1), [v.name for v in ds.variables])
        ctx.mark_changed()
        return []


class UseCommand(Procedure):
    """USE ALL — clears the filter (temporary-case selection off)."""

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        if re.search(r"\bALL\b", rest, re.IGNORECASE):
            ds.filter_var = None
            ctx.mark_changed()
        return []


def _active(ctx: Context) -> Any:
    ds = ctx.active
    if ds is None:
        raise RuntimeError("No active dataset.")
    return ds

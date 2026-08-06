"""Transformation commands: COMPUTE, IF, RECODE, COUNT (HLD 7).

These mutate the active dataset and emit no output objects. The server appends a
_DatasetChanged signal after any command that alters the active dataset, so the
grid refreshes.
"""
from __future__ import annotations

import math
import re
from typing import Any, Optional

import numpy as np

from ..data.format import Format
from ..data.variable import VariableMeta
from ..expr.evaluate import EvalContext, evaluate
from ..expr.parser import parse_expression
from ..syntax.lexer import expand_varlist
from ..syntax.registry import Context, Procedure

_LOW = -math.inf
_HIGH = math.inf


def _set_column(ds: Any, name: str, arr: np.ndarray) -> None:
    is_string = arr.dtype == object
    if name.lower() in {v.name.lower() for v in ds.variables}:
        idx = ds._index_of(name)
        ds.df[ds.variables[idx].name] = arr
    else:
        if is_string:
            width = max((len(str(x)) for x in arr if x is not None), default=8)
            meta = VariableMeta(name=name, print_format=Format("A", max(width, 1)), measure="nominal", align="left")
        else:
            meta = VariableMeta(name=name, print_format=Format("F", 8, 2))
        ds.variables.append(meta)
        ds.df[name] = arr
        ds._sync_columns()


class Execute(Procedure):
    def execute(self, _rest: str, ctx: Context) -> list[dict[str, Any]]:
        ctx.mark_changed()
        return []


class Compute(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = ctx.active
        if ds is None:
            raise RuntimeError("No active dataset.")
        m = re.match(r"\s*([A-Za-z@#$][A-Za-z0-9@#$._]*)\s*=\s*(.*)$", rest, re.DOTALL)
        if not m:
            return [{"type": "Error", "text": "COMPUTE syntax: target = expression."}]
        target, expr = m.group(1), m.group(2)
        arr = evaluate(parse_expression(expr), EvalContext(ds))
        _set_column(ds, target, np.asarray(arr))
        ctx.mark_changed()
        return []


class If(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = ctx.active
        if ds is None:
            raise RuntimeError("No active dataset.")
        m = re.match(r"\s*\((.*?)\)\s*([A-Za-z@#$][A-Za-z0-9@#$._]*)\s*=\s*(.*)$", rest, re.DOTALL)
        if not m:
            return [{"type": "Error", "text": "IF syntax: (condition) target = expression."}]
        cond_s, target, expr = m.group(1), m.group(2), m.group(3)
        cx = EvalContext(ds)
        cond = evaluate(parse_expression(cond_s), cx)
        new = evaluate(parse_expression(expr), cx)
        mask = (cond == 1.0) & ~np.isnan(cond)
        if target.lower() in {v.name.lower() for v in ds.variables}:
            cur = ds.df[ds.variables[ds._index_of(target)].name].to_numpy().copy()
        else:
            cur = np.full(ds.n_rows, np.nan)
        cur = np.asarray(cur, dtype=object) if new.dtype == object else cur.astype("float64")
        cur[mask] = new[mask]
        _set_column(ds, target, cur)
        ctx.mark_changed()
        return []


class Count(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = ctx.active
        if ds is None:
            raise RuntimeError("No active dataset.")
        m = re.match(r"\s*([A-Za-z@#$][A-Za-z0-9@#$._]*)\s*=\s*(.*?)\(([^)]*)\)\s*$", rest, re.DOTALL)
        if not m:
            return [{"type": "Error", "text": "COUNT syntax: newvar = var list (values)."}]
        target, varbody, valbody = m.group(1), m.group(2), m.group(3)
        names = expand_varlist(varbody, [v.name for v in ds.variables])
        specs = _parse_value_specs(valbody)
        cx = EvalContext(ds)
        total = np.zeros(ds.n_rows)
        for nm in names:
            col = cx.get_var(nm).astype("float64")
            hit = np.zeros(ds.n_rows, dtype=bool)
            for lo, hi in specs:
                hit |= (col >= lo) & (col <= hi)
            total += hit.astype(float)
        _set_column(ds, target, total)
        ctx.mark_changed()
        return []


class Recode(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = ctx.active
        if ds is None:
            raise RuntimeError("No active dataset.")
        into = None
        m = re.search(r"\bINTO\b(.*)$", rest, re.IGNORECASE | re.DOTALL)
        if m:
            into = expand_varlist(m.group(1), [v.name for v in ds.variables] + _bare_names(m.group(1)))
            rest = rest[: m.start()]
        # split "vars (rule)(rule)..."
        first_paren = rest.find("(")
        varbody = rest[:first_paren]
        rules_s = rest[first_paren:]
        names = expand_varlist(varbody, [v.name for v in ds.variables])
        rules = _parse_recode_rules(rules_s)
        cx = EvalContext(ds)
        for k, src in enumerate(names):
            col = cx.get_var(src).astype("float64")
            out = col.copy()
            for i in range(ds.n_rows):
                out[i] = _apply_rules(col[i], rules)
            tgt = into[k] if into else src
            _set_column(ds, tgt, out)
        ctx.mark_changed()
        return []


# ---- helpers ----
def _bare_names(s: str) -> list[str]:
    return re.findall(r"[A-Za-z@#$][A-Za-z0-9@#$._]*", s)


def _token_to_bound(tok: str) -> float:
    up = tok.strip().upper()
    if up in ("LO", "LOWEST"):
        return _LOW
    if up in ("HI", "HIGHEST"):
        return _HIGH
    return float(tok.strip())


def _parse_value_specs(body: str) -> list[tuple[float, float]]:
    specs: list[tuple[float, float]] = []
    for part in re.split(r"[,\s]+", body.strip()):
        if not part:
            continue
        mm = re.match(r"(.+?)THRU(.+)", part, re.IGNORECASE)
        if mm:
            specs.append((_token_to_bound(mm.group(1)), _token_to_bound(mm.group(2))))
        else:
            v = float(part)
            specs.append((v, v))
    return specs


def _parse_recode_rules(s: str) -> list[tuple]:
    rules: list[tuple] = []
    for m in re.finditer(r"\(([^)]*)\)", s):
        body = m.group(1).strip()
        left, _, right = body.partition("=")
        left, right = left.strip(), right.strip()
        target = _rule_target(right)
        lu = left.upper()
        if lu == "ELSE":
            rules.append(("else", target))
        elif lu == "MISSING":
            rules.append(("missing", target))
        elif lu == "SYSMIS":
            rules.append(("sysmis", target))
        else:
            mm = re.match(r"(.+?)THRU(.+)", left, re.IGNORECASE)
            if mm:
                rules.append(("range", _token_to_bound(mm.group(1)), _token_to_bound(mm.group(2)), target))
            else:
                for tok in re.split(r"[,\s]+", left):
                    if tok:
                        rules.append(("value", float(tok), target))
    return rules


def _rule_target(right: str) -> tuple:
    ru = right.upper()
    if ru in ("SYSMIS", "SYSMIS."):
        return ("sysmis",)
    if ru == "COPY":
        return ("copy",)
    return ("value", float(right))


def _apply_rules(x: float, rules: list[tuple]) -> float:
    is_sys = math.isnan(x)
    for rule in rules:
        kind = rule[0]
        if kind == "value" and not is_sys and x == rule[1]:
            return _target_value(rule[2], x)
        if kind == "range" and not is_sys and rule[1] <= x <= rule[2]:
            return _target_value(rule[3], x)
        if kind == "sysmis" and is_sys:
            return _target_value(rule[1], x)
        if kind == "missing" and is_sys:
            return _target_value(rule[1], x)
        if kind == "else":
            return _target_value(rule[1], x)
    return x


def _target_value(target: tuple, x: float) -> float:
    if target[0] == "sysmis":
        return math.nan
    if target[0] == "copy":
        return x
    return target[1]

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


class Rank(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        from scipy import stats as sps

        ds = ctx.active
        if ds is None:
            raise RuntimeError("No active dataset.")
        body = re.sub(r"^\s*VARIABLES?\s*=?\s*", "", rest, flags=re.IGNORECASE)
        body = re.split(r"\bBY\b|/", body, flags=re.IGNORECASE)[0]
        from ..data.missing import missing_mask

        for nm in expand_varlist(body, [v.name for v in ds.variables]):
            mask = missing_mask(ds.df[nm], ds.variables[ds._index_of(nm)]).to_numpy()
            x = ds.df[nm].to_numpy(dtype="float64")
            out = np.full(len(x), np.nan)
            keep = ~mask & ~np.isnan(x)
            out[keep] = sps.rankdata(x[keep], method="average")
            _set_column(ds, ("R" + nm)[:64], out)
        ctx.mark_changed()
        return []


class AutoRecode(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = ctx.active
        if ds is None:
            raise RuntimeError("No active dataset.")
        m = re.search(r"\bINTO\b(.*)$", rest, re.IGNORECASE | re.DOTALL)
        targets = m.group(1).split() if m else []
        body = re.sub(r"\bINTO\b.*$", "", rest, flags=re.IGNORECASE | re.DOTALL)
        body = re.sub(r"^\s*VARIABLES?\s*=?\s*", "", body, flags=re.IGNORECASE)
        srcs = expand_varlist(body.split("/")[0], [v.name for v in ds.variables])
        from ..data.missing import missing_mask
        from ..data.variable import VariableMeta

        for k, src in enumerate(srcs):
            series = ds.df[src]
            mask = missing_mask(series, ds.variables[ds._index_of(src)]).to_numpy()
            valid = series[~mask].dropna()
            uniq = sorted(set(valid.tolist()), key=lambda v: (isinstance(v, str), v))
            mapping = {v: i + 1 for i, v in enumerate(uniq)}
            out = np.full(len(series), np.nan)
            raw = series.to_numpy()
            for i in range(len(series)):
                if not mask[i] and raw[i] in mapping:
                    out[i] = mapping[raw[i]]
            tgt = targets[k] if k < len(targets) else "A" + src
            _set_column(ds, tgt, out)
            meta = ds.variables[ds._index_of(tgt)]
            meta.value_labels = {float(code): str(val) for val, code in mapping.items()}
            meta.measure = "nominal"
        ctx.mark_changed()
        return []


class Rmv(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = ctx.active
        if ds is None:
            raise RuntimeError("No active dataset.")
        from ..data.missing import missing_mask

        for target, src in re.findall(r"([A-Za-z@#$][\w@#$.]*)\s*=\s*SMEAN\(\s*([A-Za-z@#$][\w@#$.]*)\s*\)", rest, re.IGNORECASE):
            mask = missing_mask(ds.df[src], ds.variables[ds._index_of(src)]).to_numpy()
            x = ds.df[src].to_numpy(dtype="float64").copy()
            mean = np.nanmean(np.where(mask, np.nan, x))
            x[mask | np.isnan(x)] = mean
            _set_column(ds, target, x)
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
        cx = EvalContext(ds)
        for k, src in enumerate(names):
            tgt = into[k] if into else src
            if ds.variables[ds._index_of(src)].is_string:
                srules = _parse_recode_rules_str(rules_s)
                col = ds.df[src].astype(object)
                out = np.array([_apply_rules_str(v, srules) for v in col], dtype=object)
                _set_column(ds, tgt, out)
            else:
                rules = _parse_recode_rules(rules_s)
                col = cx.get_var(src).astype("float64")
                out = col.copy()
                for i in range(ds.n_rows):
                    out[i] = _apply_rules(col[i], rules)
                _set_column(ds, tgt, out)
        ctx.mark_changed()
        return []


class Create(Procedure):
    """CREATE newvar = LAG(var[, n])  |  LEAD(var[, n])  — the Shift Values command."""

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = ctx.active
        if ds is None:
            raise RuntimeError("No active dataset.")
        did = False
        for m in re.finditer(
            r"([A-Za-z@#$][\w@#$.]*)\s*=\s*(LAG|LEAD|DIFF)\s*\(\s*([A-Za-z@#$][\w@#$.]*)\s*(?:,\s*(\d+))?\s*\)",
            rest, re.IGNORECASE,
        ):
            tgt, fn, src, n = m.group(1), m.group(2).upper(), m.group(3), int(m.group(4) or 1)
            col = ds.df[src].to_numpy(dtype="float64")
            out = np.full(len(col), np.nan)
            if fn == "LAG":
                out[n:] = col[: len(col) - n]
            elif fn == "LEAD":
                out[: len(col) - n] = col[n:]
            else:  # DIFF: value minus its n-lag
                out[n:] = col[n:] - col[: len(col) - n]
            _set_column(ds, tgt, out)
            did = True
        if not did:
            return [{"type": "Error", "text": "CREATE syntax: newvar = LAG(var, n) | LEAD(var, n) | DIFF(var, n)."}]
        ctx.mark_changed()
        return []


class SetCmd(Procedure):
    """SET SEED = n — makes RV.* / sampling reproducible for later commands."""

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        m = re.search(r"\bSEED\s*=?\s*(\d+)", rest, re.IGNORECASE)
        if m:
            np.random.seed(int(m.group(1)))
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


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] in "'\"" and s[-1] == s[0]:
        return s[1:-1].replace(s[0] * 2, s[0])
    return s


def _parse_recode_rules_str(s: str) -> list[tuple]:
    """Recode rules for STRING variables: value/else with string targets."""
    rules: list[tuple] = []
    for m in re.finditer(r"\(([^)]*)\)", s):
        left, _, right = m.group(1).partition("=")
        lu = left.strip().upper()
        rt = _unquote(right)
        if lu == "ELSE":
            rules.append(("else", rt))
        else:
            for tok in re.findall(r"'[^']*'|\"[^\"]*\"|\S+", left):
                rules.append(("value", _unquote(tok), rt))
    return rules


def _apply_rules_str(x: Any, rules: list[tuple]) -> Any:
    xs = "" if x is None else str(x)
    for rule in rules:
        if rule[0] == "value" and xs == rule[1]:
            return rule[2]
        if rule[0] == "else":
            return rule[1]
    return xs

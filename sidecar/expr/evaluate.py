"""Evaluate an expression AST over all cases (vectorised).

Values are float64 arrays with NaN for system-missing; strings are object
arrays. Missing propagates through arithmetic and comparisons, EXCEPT the
.n across-variable functions, the MISSING/SYSMIS/NMISS/NVALID/VALUE family, and
logical short-circuits (HLD 7.3).
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy import stats as sps

from ..data.missing import missing_mask


class EvalContext:
    def __init__(self, dataset: Any):
        self.ds = dataset
        self.n = dataset.n_rows

    def var_names(self) -> list[str]:
        return [v.name for v in self.ds.variables]

    def get_var(self, name: str) -> np.ndarray:
        idx = self.ds._index_of(name)
        meta = self.ds.variables[idx]
        s = self.ds.df[name]
        if meta.is_string:
            return s.astype(object).to_numpy()
        return s.to_numpy(dtype="float64")

    def is_missing_var(self, name: str) -> np.ndarray:
        idx = self.ds._index_of(name)
        return missing_mask(self.ds.df[name], self.ds.variables[idx]).to_numpy()


def evaluate(node: tuple, ctx: EvalContext) -> np.ndarray:
    kind = node[0]
    if kind == "num":
        return np.full(ctx.n, float(node[1]))
    if kind == "str":
        return np.full(ctx.n, node[1], dtype=object)
    if kind == "var":
        return ctx.get_var(node[1])
    if kind == "neg":
        return -evaluate(node[1], ctx)
    if kind == "not":
        v = evaluate(node[1], ctx)
        return np.where(np.isnan(v), np.nan, np.where(v != 0, 0.0, 1.0))
    if kind == "and":
        return _logic_and(evaluate(node[1], ctx), evaluate(node[2], ctx))
    if kind == "or":
        return _logic_or(evaluate(node[1], ctx), evaluate(node[2], ctx))
    if kind == "bin":
        return _binary(node[1], evaluate(node[2], ctx), evaluate(node[3], ctx))
    if kind == "call":
        return _call(node[1], node[2], ctx)
    if kind == "range":
        raise ValueError("TO range not valid here.")
    raise ValueError(f"Unknown node: {kind}")


def _binary(op: str, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    if op == "+":
        if a.dtype == object or b.dtype == object:
            return np.array([str(x) + str(y) for x, y in zip(a, b)], dtype=object)
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        with np.errstate(divide="ignore", invalid="ignore"):
            return a / b
    if op == "**":
        return a ** b
    # comparisons -> 1.0/0.0, NaN if either missing
    if a.dtype == object or b.dtype == object:
        res = np.array([_cmp_scalar(op, x, y) for x, y in zip(a, b)], dtype="float64")
        return res
    with np.errstate(invalid="ignore"):
        if op == "=":
            r = a == b
        elif op == "~=":
            r = a != b
        elif op == "<":
            r = a < b
        elif op == ">":
            r = a > b
        elif op == "<=":
            r = a <= b
        elif op == ">=":
            r = a >= b
        else:
            raise ValueError(op)
    out = r.astype("float64")
    out[np.isnan(a) | np.isnan(b)] = np.nan
    return out


def _cmp_scalar(op: str, x: Any, y: Any) -> float:
    if op == "=":
        return 1.0 if x == y else 0.0
    if op == "~=":
        return 1.0 if x != y else 0.0
    return float("nan")


def _logic_and(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    out = np.full(a.shape, np.nan)
    fa, fb = a != 0, b != 0
    out[(a == 0) | (b == 0)] = 0.0  # FALSE AND anything = FALSE
    out[(~np.isnan(a)) & (~np.isnan(b)) & fa & fb] = 1.0
    return out


def _logic_or(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    out = np.full(a.shape, np.nan)
    out[(a != 0) & ~np.isnan(a)] = 1.0  # TRUE OR anything = TRUE
    out[(b != 0) & ~np.isnan(b)] = 1.0
    out[(a == 0) & (b == 0)] = 0.0
    return out


# ---- functions ----
def _call(fname: str, args: list[tuple], ctx: EvalContext) -> np.ndarray:
    base = fname.split(".")[0]
    if base in _ACROSS:
        return _across(fname, args, ctx)
    if base in ("MISSING", "SYSMIS", "NMISS", "NVALID", "VALUE"):
        return _missing_family(base, args, ctx)
    if base in _DIST_BASES and "." in fname:
        return _distribution(fname, [evaluate(a, ctx) for a in args])

    vals = [evaluate(a, ctx) for a in args]
    if base in _UNARY:
        return _UNARY[base](vals[0])
    if base == "MOD":
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.remainder(vals[0], vals[1])
    if base in _STRING:
        return _STRING[base](vals)
    raise ValueError(f"Unknown function: {fname}")


_UNARY = {
    "ABS": np.abs,
    "SQRT": np.sqrt,
    "EXP": np.exp,
    "LN": np.log,
    "LG10": np.log10,
    "SIN": np.sin,
    "COS": np.cos,
    "ARSIN": np.arcsin,
    "ARTAN": np.arctan,
    "RND": lambda a: np.sign(a) * np.floor(np.abs(a) + 0.5),
    "TRUNC": np.trunc,
}

_ACROSS = {"SUM", "MEAN", "SD", "VARIANCE", "MIN", "MAX", "CFVAR"}
_DIST_BASES = {"CDF", "IDF", "PDF", "SIG"}


def _expand_args(args: list[tuple], ctx: EvalContext) -> list[np.ndarray]:
    names = ctx.var_names()
    lower = {n.lower(): i for i, n in enumerate(names)}
    cols: list[np.ndarray] = []
    for a in args:
        if a[0] == "range":
            lo = a[1][1] if a[1][0] == "var" else None
            hi = a[2][1] if a[2][0] == "var" else None
            if lo is None or hi is None:
                raise ValueError("TO requires variable names.")
            i0, i1 = lower[lo.lower()], lower[hi.lower()]
            if i0 > i1:
                i0, i1 = i1, i0
            for nm in names[i0 : i1 + 1]:
                cols.append(ctx.get_var(nm))
        else:
            cols.append(evaluate(a, ctx))
    return cols


def _across(fname: str, args: list[tuple], ctx: EvalContext) -> np.ndarray:
    base, _, suffix = fname.partition(".")
    min_valid = int(suffix) if suffix else 1
    cols = _expand_args(args, ctx)
    mat = np.vstack([c.astype("float64") for c in cols])  # (k, n)
    valid = ~np.isnan(mat)
    count = valid.sum(axis=0)
    out = np.full(ctx.n, np.nan)
    ok = count >= min_valid
    with np.errstate(invalid="ignore"):
        masked = np.where(valid, mat, 0.0)
        if base == "SUM":
            res = masked.sum(axis=0)
        elif base == "MEAN":
            res = masked.sum(axis=0) / np.where(count == 0, 1, count)
        elif base == "MIN":
            res = np.where(valid, mat, np.inf).min(axis=0)
        elif base == "MAX":
            res = np.where(valid, mat, -np.inf).max(axis=0)
        else:
            means = masked.sum(axis=0) / np.where(count == 0, 1, count)
            ss = np.where(valid, (mat - means) ** 2, 0.0).sum(axis=0)
            var = ss / np.where(count > 1, count - 1, np.nan)
            if base == "VARIANCE":
                res = var
            elif base == "SD":
                res = np.sqrt(var)
            else:  # CFVAR = SD/MEAN
                res = np.sqrt(var) / means
    out[ok] = res[ok]
    return out


def _missing_family(base: str, args: list[tuple], ctx: EvalContext) -> np.ndarray:
    def is_missing(a: tuple) -> np.ndarray:
        if a[0] == "var":
            return ctx.is_missing_var(a[1])
        v = evaluate(a, ctx)
        return np.isnan(v.astype("float64")) if v.dtype != object else np.array([x is None for x in v])

    if base == "MISSING":
        return is_missing(args[0]).astype("float64")
    if base == "SYSMIS":
        v = evaluate(args[0], ctx)
        return np.isnan(v.astype("float64")).astype("float64")
    if base == "VALUE":
        return evaluate(args[0], ctx)
    # NMISS / NVALID across args (expand ranges)
    cols = _expand_args(args, ctx)
    miss = np.vstack([np.isnan(c.astype("float64")) for c in cols])
    if base == "NMISS":
        return miss.sum(axis=0).astype("float64")
    return (~miss).sum(axis=0).astype("float64")


def _distribution(fname: str, vals: list[np.ndarray]) -> np.ndarray:
    func, _, dist = fname.partition(".")
    x = vals[0]
    if dist == "NORMAL":
        mean = vals[1] if len(vals) > 1 else 0.0
        sd = vals[2] if len(vals) > 2 else 1.0
        d = sps.norm(mean, sd)
    elif dist == "T":
        d = sps.t(vals[1])
    elif dist == "CHISQ":
        d = sps.chi2(vals[1])
    elif dist == "F":
        d = sps.f(vals[1], vals[2])
    else:
        raise ValueError(f"Unsupported distribution: {dist}")
    if func == "CDF":
        return d.cdf(x)
    if func == "IDF":
        return d.ppf(x)
    if func == "PDF":
        return d.pdf(x)
    if func == "SIG":
        return d.sf(x)
    raise ValueError(func)


def _substr(vals: list[np.ndarray]) -> np.ndarray:
    s, pos = vals[0], vals[1]
    ln = vals[2] if len(vals) > 2 else None
    out = []
    for i, x in enumerate(s):
        st = int(pos[i]) - 1
        if ln is None:
            out.append(str(x)[st:])
        else:
            out.append(str(x)[st : st + int(ln[i])])
    return np.array(out, dtype=object)


_STRING = {
    "CONCAT": lambda vs: np.array(["".join(str(v[i]) for v in vs) for i in range(len(vs[0]))], dtype=object),
    "UPCASE": lambda vs: np.array([str(x).upper() for x in vs[0]], dtype=object),
    "LOWER": lambda vs: np.array([str(x).lower() for x in vs[0]], dtype=object),
    "LTRIM": lambda vs: np.array([str(x).lstrip() for x in vs[0]], dtype=object),
    "RTRIM": lambda vs: np.array([str(x).rstrip() for x in vs[0]], dtype=object),
    "LENGTH": lambda vs: np.array([float(len(str(x))) for x in vs[0]], dtype="float64"),
    "SUBSTR": _substr,
    "NUMBER": lambda vs: np.array([_to_num(x) for x in vs[0]], dtype="float64"),
    "STRING": lambda vs: np.array([str(x) for x in vs[0]], dtype=object),
}


def _to_num(x: Any) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan

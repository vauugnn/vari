"""Metadata syntax commands (HLD 8.3): VARIABLE LABELS, VALUE LABELS,
ADD VALUE LABELS, MISSING VALUES, RENAME VARIABLES, FORMATS."""
from __future__ import annotations

import re
from typing import Any

from ..data.format import Format
from ..data.missing import MissingSpec
from ..syntax.lexer import expand_varlist, unquote
from ..syntax.registry import Context, Procedure

_NAME = r"[A-Za-z@#$][\w@#$.]*"


def _active(ctx: Context) -> Any:
    ds = ctx.active
    if ds is None:
        raise RuntimeError("No active dataset.")
    return ds


class VariableCmd(Procedure):
    """Dispatches VARIABLE LABELS / LEVEL / WIDTH."""

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        m = re.match(r"\s*(\w+)(.*)$", rest, re.DOTALL)
        sub, body = (m.group(1).upper(), m.group(2)) if m else ("", rest)
        if sub.startswith("LAB"):
            for name, _, lab in re.findall(rf"({_NAME})\s+(['\"])(.*?)\2", body):
                ds.variables[ds._index_of(name)].label = lab
        elif sub.startswith("LEV"):  # VARIABLE LEVEL var (SCALE|ORDINAL|NOMINAL)
            for names, lvl in re.findall(r"([\w@#$. ]+?)\((\w+)\)", body):
                for nm in names.split():
                    ds.variables[ds._index_of(nm)].measure = {"S": "scale", "O": "ordinal", "N": "nominal"}[lvl.upper()[0]]
        ctx.mark_changed()
        return []


class ValueLabels(Procedure):
    def __init__(self, add: bool = False):
        self.add = add

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        body = re.sub(r"^\s*(ADD\s+)?VALUE\s+LABELS?\s*|^\s*LABELS?\s*", "", rest, flags=re.IGNORECASE)
        toks = re.findall(r"'[^']*'|\"[^\"]*\"|\S+", body)
        names, i = [], 0
        dsnames = {v.name.lower() for v in ds.variables}
        while i < len(toks) and toks[i].lower() in dsnames:
            names.append(toks[i])
            i += 1
        pairs = {}
        while i + 1 < len(toks):
            val = toks[i]
            lab = unquote(toks[i + 1]) or toks[i + 1]
            key = float(val) if re.match(r"^-?[\d.]+$", val) else (unquote(val) or val)
            pairs[key] = lab
            i += 2
        for nm in names:
            meta = ds.variables[ds._index_of(nm)]
            if not self.add:
                meta.value_labels = {}
            meta.value_labels.update(pairs)
        ctx.mark_changed()
        return []


class MissingValues(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        rest = re.sub(r"^\s*VALUES?\s*", "", rest, flags=re.IGNORECASE)
        for names, spec in re.findall(r"([\w@#$. ]+?)\(([^)]*)\)", rest):
            for nm in expand_varlist(names, [v.name for v in ds.variables]):
                ds.variables[ds._index_of(nm)].missing = _parse_missing(spec)
        ctx.mark_changed()
        return []


class RenameVariables(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        body = re.sub(r"^\s*VARIABLES?\s*", "", rest, flags=re.IGNORECASE)
        for grp in re.findall(r"\(([^)]*)\)", body):
            left, _, right = grp.partition("=")
            olds, news = left.split(), right.split()
            for o, n in zip(olds, news):
                ds.rename_variable(ds._index_of(o), n)
        ctx.mark_changed()
        return []


class Formats(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = _active(ctx)
        for names, fmt in re.findall(r"([\w@#$. ]+?)\(([^)]*)\)", rest):
            for nm in expand_varlist(names, [v.name for v in ds.variables]):
                ds.variables[ds._index_of(nm)].print_format = Format.parse(fmt.strip())
        ctx.mark_changed()
        return []


def _parse_missing(spec: str) -> MissingSpec:
    spec = spec.strip()
    rng = re.match(r"(.+?)\bTHRU\b(.+)", spec, re.IGNORECASE)
    if rng:
        lo = -1e300 if rng.group(1).strip().upper() in ("LO", "LOWEST") else float(rng.group(1))
        hi = 1e300 if rng.group(2).strip().upper() in ("HI", "HIGHEST") else float(rng.group(2))
        return MissingSpec.range(lo, hi)
    vals = [t for t in re.split(r"[,\s]+", spec) if t]
    nums = []
    for v in vals:
        try:
            nums.append(float(v))
        except ValueError:
            nums.append(unquote(v) or v)
    return MissingSpec.discrete(nums[:3]) if nums else MissingSpec.none()

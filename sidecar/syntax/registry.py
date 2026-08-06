"""Command registry and procedure base (HLD 8.2).

A command is resolved by its name or any unambiguous prefix (FREQ -> FREQUENCIES).
Procedures implement `execute(rest, subs, ctx)` and return output objects.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from .lexer import command_name, split_subcommands


class Context:
    """What a running command can touch."""

    def __init__(self, ds_registry: Any):
        self.ds_registry = ds_registry
        self.data_changed = False

    @property
    def active(self) -> Any:
        return self.ds_registry.active

    def mark_changed(self) -> None:
        self.data_changed = True


class Procedure:
    command: str = ""

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        raise NotImplementedError


class DataProcedure(Procedure):
    """A procedure that operates on the active dataset. The base weaves in
    FILTER (row subset) and SPLIT FILE (run once per split group), so every
    procedure respects them without per-procedure code."""

    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = ctx.active
        if ds is None:
            raise RuntimeError("There is no active dataset.")
        subs = split_subcommands(rest)

        base_df = ds.df
        fv = getattr(ds, "filter_var", None)
        if fv and fv in ds.df.columns:
            base_df = ds.df[ds.df[fv].fillna(0) != 0]

        split_vars = getattr(ds, "split_vars", None) or []
        if not split_vars:
            return self.run(_make_sub(ds, base_df), subs)

        out: list[dict[str, Any]] = []
        for gkey, gdf in base_df.groupby(split_vars, sort=True):
            vals = gkey if isinstance(gkey, tuple) else (gkey,)
            label = ", ".join(f"{v} = {val}" for v, val in zip(split_vars, vals))
            out.append({"type": "TextBlock", "text": f"Split File group: {label}"})
            out += self.run(_make_sub(ds, gdf), subs)
        return out

    def run(self, ds: Any, subs: list[tuple[str, str]]) -> list[dict[str, Any]]:
        raise NotImplementedError


def _make_sub(ds: Any, df_subset: Any) -> Any:
    """A dataset over a row subset that keeps variable metadata and the weight."""
    from ..data.dataset import Dataset

    if df_subset is ds.df:
        return ds
    sub = Dataset(df_subset.reset_index(drop=True), [v.copy() for v in ds.variables], ds.name)
    sub.weight_var = getattr(ds, "weight_var", None)
    return sub


class Registry:
    def __init__(self) -> None:
        self._commands: dict[str, type[Procedure]] = {}

    def register(self, name: str) -> Callable[[type[Procedure]], type[Procedure]]:
        def deco(cls: type[Procedure]) -> type[Procedure]:
            cls.command = name.upper()
            self._commands[name.upper()] = cls
            return cls

        return deco

    def resolve(self, token: str) -> Optional[type[Procedure]]:
        token = token.upper().replace("-", "")  # T-TEST -> TTEST
        if token in self._commands:
            return self._commands[token]
        matches = [n for n in self._commands if n.startswith(token)]
        if len(matches) == 1:
            return self._commands[matches[0]]
        return None

    def names(self) -> list[str]:
        return sorted(self._commands)


def execute_syntax(text: str, registry: Registry, ctx: Context) -> list[dict[str, Any]]:
    from .lexer import split_commands

    outputs: list[dict[str, Any]] = []
    for cmd in split_commands(text):
        name, rest = command_name(cmd)
        cls = registry.resolve(name)
        if cls is None:
            outputs.append({"type": "Error", "text": f"Unrecognized command: {name or cmd.strip()}"})
            continue
        try:
            outputs.extend(cls().execute(rest, ctx))
        except Exception as exc:  # noqa: BLE001 — surface as an output Error
            outputs.append({"type": "Error", "text": f"{name}: {exc}"})
    return outputs

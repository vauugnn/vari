"""Dataset — a pandas.DataFrame plus a parallel list[VariableMeta] kept in
index-order lockstep, with structural edits that update both atomically
(HLD 3.4). Copy-on-write snapshots support TEMPORARY later (HLD 8.3 / risks).
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from .format import Format
from .variable import VariableMeta, validate_name


class Dataset:
    def __init__(self, df: pd.DataFrame, variables: list[VariableMeta], name: str = "DataSet1",
                 source_path: Optional[str] = None):
        if df.shape[1] != len(variables):
            raise ValueError("Column count and variable count differ.")
        self.df = df.reset_index(drop=True)
        self.variables = variables
        self.name = name
        self.source_path = source_path
        self._sync_columns()

    # ---- internal -----------------------------------------------------
    def _sync_columns(self) -> None:
        self.df.columns = [v.name for v in self.variables]

    def _index_of(self, name: str) -> int:
        lowered = name.lower()
        for i, v in enumerate(self.variables):
            if v.name.lower() == lowered:
                return i
        raise KeyError(f"No variable named {name!r}.")

    @property
    def n_rows(self) -> int:
        return int(self.df.shape[0])

    @property
    def n_vars(self) -> int:
        return len(self.variables)

    # ---- copy-on-write ------------------------------------------------
    def snapshot(self) -> "Dataset":
        """Deep, independent copy — the transaction boundary TEMPORARY needs."""
        return Dataset(
            self.df.copy(deep=True),
            [v.copy() for v in self.variables],
            self.name,
            self.source_path,
        )

    # ---- windowed read (grid) -----------------------------------------
    def get_rows(self, offset: int, limit: int, value_labels: bool = False) -> list[list[str]]:
        offset = max(0, offset)
        end = min(self.n_rows, offset + limit)
        if offset >= end:
            return []
        block = self.df.iloc[offset:end]
        cols: list[list[str]] = []
        for v in self.variables:
            series = block[v.name]
            cols.append([self._render_cell(v, val, value_labels) for val in series])
        # transpose columns -> rows
        return [list(row) for row in zip(*cols)] if cols else []

    def _render_cell(self, v: VariableMeta, val: Any, value_labels: bool) -> str:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return "" if v.is_string else "."
        if value_labels and v.value_labels:
            key = val if v.is_string else _num_key(val)
            if key in v.value_labels:
                return v.value_labels[key]
            if val in v.value_labels:
                return v.value_labels[val]
        return v.print_format.render(val)

    # ---- cell edit ----------------------------------------------------
    def ensure_rows(self, n: int) -> None:
        """Grow the frame to at least n rows, filling new cells with blanks."""
        if n <= self.n_rows:
            return
        extra = n - self.n_rows
        blank = {v.name: ("" if v.is_string else np.nan) for v in self.variables}
        pad = pd.DataFrame([blank] * extra)
        self.df = pd.concat([self.df, pad], ignore_index=True)
        self._sync_columns()

    def set_cell(self, row: int, col: int, raw: str) -> None:
        if col < 0 or col >= self.n_vars:
            raise IndexError("Cell out of range.")
        if row >= self.n_rows:
            self.ensure_rows(row + 1)
        if row < 0:
            raise IndexError("Cell out of range.")
        v = self.variables[col]
        if v.is_string:
            self.df.iat[row, col] = raw
        else:
            parsed = v.print_format.parse_input(raw)
            self.df.iat[row, col] = np.nan if parsed is None else parsed

    def get_cell_raw(self, row: int, col: int) -> Any:
        val = self.df.iat[row, col]
        if isinstance(val, float) and np.isnan(val):
            return None
        return val

    # ---- structural edits ---------------------------------------------
    def insert_variable(self, index: int, meta: VariableMeta) -> None:
        validate_name(meta.name, {v.name for v in self.variables})
        index = max(0, min(index, self.n_vars))
        fill: Any = "" if meta.is_string else np.nan
        self.variables.insert(index, meta)
        self.df.insert(index, meta.name, fill)

    def append_variable(self, meta: VariableMeta) -> None:
        self.insert_variable(self.n_vars, meta)

    def delete_variable(self, index: int) -> None:
        v = self.variables.pop(index)
        self.df.drop(columns=[v.name], inplace=True)

    def rename_variable(self, index: int, new_name: str) -> None:
        others = {v.name for i, v in enumerate(self.variables) if i != index}
        validate_name(new_name, others)
        old = self.variables[index].name
        self.variables[index].name = new_name
        self.df.rename(columns={old: new_name}, inplace=True)

    def set_variable_meta(self, index: int, meta: VariableMeta) -> None:
        if meta.name.lower() != self.variables[index].name.lower():
            others = {v.name for i, v in enumerate(self.variables) if i != index}
            validate_name(meta.name, others)
            self.df.rename(columns={self.variables[index].name: meta.name}, inplace=True)
        self.variables[index] = meta
        self._sync_columns()

    def insert_case(self, index: int) -> None:
        index = max(0, min(index, self.n_rows))
        blank = {v.name: ("" if v.is_string else np.nan) for v in self.variables}
        top = self.df.iloc[:index]
        bottom = self.df.iloc[index:]
        self.df = pd.concat([top, pd.DataFrame([blank]), bottom], ignore_index=True)
        self._sync_columns()

    def delete_case(self, index: int) -> None:
        self.df = self.df.drop(index=index).reset_index(drop=True)

    def append_empty_variable(self) -> VariableMeta:
        """Grid typing into the first empty column creates VAR0000n / F8.2."""
        n = self.n_vars + 1
        name = f"VAR{n:05d}"
        existing = {v.name.upper() for v in self.variables}
        while name.upper() in existing:
            n += 1
            name = f"VAR{n:05d}"
        meta = VariableMeta(name=name, print_format=Format("F", 8, 2))
        self.append_variable(meta)
        return meta


def _num_key(val: Any) -> Any:
    """Value-label maps are keyed by the numeric code; normalise 2.0 -> 2."""
    if isinstance(val, float) and val.is_integer():
        return int(val)
    return val


class DatasetRegistry:
    def __init__(self) -> None:
        self._datasets: dict[str, Dataset] = {}
        self._active: Optional[str] = None
        self._counter = 0

    def next_name(self) -> str:
        self._counter += 1
        return f"DataSet{self._counter}"

    def add(self, ds: Dataset, activate: bool = True) -> str:
        if ds.name in self._datasets:
            ds.name = self.next_name()
        self._datasets[ds.name] = ds
        if activate or self._active is None:
            self._active = ds.name
        return ds.name

    @property
    def active(self) -> Optional[Dataset]:
        return self._datasets.get(self._active) if self._active else None

    def activate(self, name: str) -> None:
        if name not in self._datasets:
            raise KeyError(name)
        self._active = name

    def get(self, name: str) -> Optional[Dataset]:
        return self._datasets.get(name)

    def close(self, name: str) -> None:
        self._datasets.pop(name, None)
        if self._active == name:
            self._active = next(iter(self._datasets), None)

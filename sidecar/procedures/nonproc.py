"""Non-procedure commands: TITLE, GET, SAVE, and the PIVOTDEMO test command."""
from __future__ import annotations

import re
from typing import Any

from ..data.format import Format
from ..io.files import open_file, save_file
from ..output.model import Dimension, PivotTable, simple_table, title as title_obj
from ..syntax.registry import Context, Procedure

_QUOTED = re.compile(r"""(['"])(.*?)\1""", re.DOTALL)


class Title(Procedure):
    def execute(self, rest: str, _ctx: Context) -> list[dict[str, Any]]:
        m = _QUOTED.search(rest)
        text = m.group(2) if m else rest.strip()
        return [{"type": "Title", "text": text}]


class Get(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        m = re.search(r"FILE\s*=?\s*(['\"])(.*?)\1", rest, re.IGNORECASE | re.DOTALL)
        if not m:
            m2 = _QUOTED.search(rest)
            if not m2:
                return [{"type": "Error", "text": "GET FILE requires a quoted path."}]
            path = m2.group(2)
        else:
            path = m.group(2)
        ds = open_file(path, name=ctx.ds_registry.next_name())
        ctx.ds_registry.add(ds, activate=True)
        return []


class Save(Procedure):
    def execute(self, rest: str, ctx: Context) -> list[dict[str, Any]]:
        ds = ctx.active
        if ds is None:
            return [{"type": "Error", "text": "SAVE: no active dataset."}]
        m = re.search(r"OUTFILE\s*=?\s*(['\"])(.*?)\1", rest, re.IGNORECASE | re.DOTALL)
        path = m.group(2) if m else ds.source_path
        if not path:
            return [{"type": "Error", "text": "SAVE OUTFILE requires a path."}]
        save_file(ds, path)
        ds.source_path = path
        return []


class PivotDemo(Procedure):
    def execute(self, _rest: str, _ctx: Context) -> list[dict[str, Any]]:
        desc = simple_table(
            "Descriptive Statistics",
            ["Age", "Annual income", "Satisfaction"],
            ["N", "Minimum", "Maximum", "Mean", "Std. Deviation"],
            [
                [400, 18, 64, 38.42, 11.315],
                [400, 12000, 145000, 51873.25, 21044.7],
                [398, 1, 5, 3.27, 1.041],
            ],
            col_formats=[Format("F", 8, 0), Format("F", 8, 0), Format("F", 8, 0), Format("F", 8, 2), Format("F", 8, 3)],
        )
        ct = PivotTable(
            "Agreement * Gender Crosstabulation",
            row_dims=[Dimension("Agreement", ["Agree", "Neutral", "Disagree"])],
            col_dims=[Dimension("Gender", ["Male", "Female"]), Dimension("", ["Count", "Expected"])],
            corner="Agreement",
        )
        data = [[(80, 74.2), (70, 75.8)], [(30, 28.1), (27, 28.9)], [(20, 27.7), (36, 28.3)]]
        for i, row in enumerate(data):
            for g, (count, exp) in enumerate(row):
                ct.set([i], [g, 0], Format("F", 8, 0).render(count), "num")
                ct.set([i], [g, 1], Format("F", 8, 1).render(exp), "num")
        return [title_obj("Descriptives"), desc.to_json(), ct.to_json()]

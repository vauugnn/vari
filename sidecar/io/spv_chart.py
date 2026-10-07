"""Charts inside IBM .spv files.

A graph is two members: `*_chart.xml` (VizML: what to draw) and
`*_chartData.bin` (the data, legacy binary). We rebuild an equivalent chart
from the data and the VizML's element/bindings with Vari's own chart
primitives. Anything we cannot rebuild falls back to the chart's data as a
table, so no information is dropped silently. The original members ride along
in `spv` for byte-exact re-save.
"""
from __future__ import annotations

import base64
import zipfile
from typing import Any, Optional
from xml.etree import ElementTree as ET

import numpy as np

from ..output import charts as ch
from .spv_legacy import parse_legacy

_ELEMENTS = {"interval", "point", "line", "area", "schema", "edge", "polygon", "contour"}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


class _Viz:
    """The bits of a VizML visualization we need."""

    def __init__(self, xml: bytes) -> None:
        self.root = ET.fromstring(xml)
        self.vars: dict[str, dict[str, Any]] = {}   # sourceName -> {label, categorical, relabel}
        self.ids: dict[str, str] = {}                # variable id -> sourceName
        self.frame_titles: list[str] = []
        self.titles: list[str] = []
        self.axis_labels: list[str] = []
        self.element: Optional[ET.Element] = None
        self.polar = False
        for e in self.root.iter():
            t = _local(e.tag)
            if t == "sourceVariable":
                relabel = {r.get("from"): r.get("to") for r in e.iter() if _local(r.tag) == "relabel"}
                self.ids[e.get("id", "")] = e.get("sourceName", "")
                self.vars[e.get("sourceName", "")] = {
                    "label": e.get("label") or e.get("shortLabel") or e.get("sourceName", ""),
                    "categorical": e.get("categorical") == "true",
                    "relabel": relabel,
                }
            elif t == "polar" or (t == "transform" and e.get("type") == "polar"):
                self.polar = True
        graph = next((e for e in self.root.iter() if _local(e.tag) == "graph"), None)
        if graph is not None:
            for e in graph.iter():
                if _local(e.tag) in _ELEMENTS and self.element is None:
                    self.element = e
        for fr in self.root.iter():
            if _local(fr.tag) == "labelFrame":
                for lab in fr:
                    texts = [t.text or "" for t in lab.iter() if _local(t.tag) == "text"]
                    if len(texts) == 1 and texts[0].strip() and not texts[0].strip().endswith("="):
                        self.frame_titles.append(texts[0].strip())
        for e in self.root.iter():
            if _local(e.tag) == "label":
                text = "".join(t.text or "" for t in e.iter() if _local(t.tag) == "text").strip()
                if not text:
                    continue
                (self.titles if e.get("purpose") == "title" else self.axis_labels).append(text)

    def binding(self, axis: str) -> Optional[str]:
        if self.element is None:
            return None
        for c in self.element:
            if _local(c.tag) == axis:
                ref = c.get("variable")
                return self.ids.get(ref or "", ref)
        return None

    def has_child(self, name: str) -> bool:
        return self.element is not None and any(_local(c.tag) == name for c in self.element)

    def label_of(self, var: Optional[str]) -> str:
        return self.vars.get(var or "", {}).get("label", var or "")

    def display(self, var: str, value: Any) -> str:
        v = self.vars.get(var, {})
        key = f"{value:g}" if isinstance(value, float) else str(value)
        return v.get("relabel", {}).get(key, key)


def _data_table(src: dict[str, list[Any]], viz: _Viz, why: str) -> list[dict[str, Any]]:
    from ..output.model import Dimension, PivotTable

    names = [n for n in src if not n.startswith("$CASENUM") and "_exceptions_" not in n]
    n = len(next(iter(src.values()))) if src else 0
    shown = min(n, 200)
    t = PivotTable("Chart data", [Dimension("", [str(i + 1) for i in range(shown)])],
                   [Dimension("", [viz.label_of(c) for c in names])])
    for ci, c in enumerate(names):
        for ri in range(shown):
            t.set([ri], [ci], viz.display(c, src[c][ri]) if src[c][ri] is not None else ".", "text")
    return [{"type": "Warning", "text": f"[Chart could not be redrawn ({why}); showing its data]"}, t.to_json()]


def chart_from_member(z: zipfile.ZipFile, xml_path: Optional[str], data_path: Optional[str]) -> Any:
    """Return one output object, or a list of objects when falling back."""
    names = set(z.namelist())
    if not xml_path or xml_path not in names or not data_path or data_path not in names:
        return {"type": "Warning", "text": "[Chart members missing from file]"}
    xml, raw = z.read(xml_path), z.read(data_path)
    try:
        viz = _Viz(xml)
        sources = parse_legacy(raw)
    except (ET.ParseError, ValueError) as e:
        return {"type": "Warning", "text": f"[Chart could not be read: {e}]"}
    src = next(iter(sources.values()), {})
    try:
        chart = _rebuild(viz, src)
    except Exception as e:  # noqa: BLE001 - never lose the file over one chart
        return _data_table(src, viz, str(e))
    if chart is None:
        kind = _local(viz.element.tag) if viz.element is not None else "unknown"
        return _data_table(src, viz, f"{kind} chart type not supported yet")
    chart["spv"] = {"xml": base64.b64encode(xml).decode(), "data": base64.b64encode(raw).decode(),
                    "xmlName": xml_path, "dataName": data_path}
    return chart


def _rebuild(viz: _Viz, src: dict[str, list[Any]]) -> Optional[dict[str, Any]]:
    el = viz.element
    if el is None or viz.polar:
        return None
    kind = _local(el.tag)
    x, y = viz.binding("x"), viz.binding("y")
    title = (viz.titles or viz.frame_titles or [""])[0]
    if kind == "interval" and x and x in src and viz.has_child("binStatistic") and not y:
        v = np.array([a for a in src[x] if a is not None], dtype=float)
        if not v.size:
            return None
        return ch.histogram(v, title=title or viz.label_of(x), xlabel=viz.label_of(x),
                            mean=float(v.mean()), sd=float(v.std(ddof=1)) if v.size > 1 else None,
                            n=int(v.size))
    if kind == "interval" and x and y and x in src and y in src:
        labels = [viz.display(x, a) for a in src[x]]
        vals = [0.0 if a is None else float(a) for a in src[y]]
        ylab = viz.axis_labels[1] if len(viz.axis_labels) > 1 else viz.label_of(y)
        return ch.bar_chart(labels, vals, title=title, xlabel=viz.label_of(x), ylabel=ylab)
    if kind == "point" and x and y and x in src and y in src:
        pts = [(a, b) for a, b in zip(src[x], src[y]) if a is not None and b is not None]
        return ch.scatter([p[0] for p in pts], [p[1] for p in pts], title=title,
                          xlabel=viz.label_of(x), ylabel=viz.label_of(y))
    if kind == "line" and x and y and x in src and y in src:
        pts = [(a, b) for a, b in zip(src[x], src[y]) if a is not None and b is not None]
        return ch.line([p[0] for p in pts], [p[1] for p in pts], title=title,
                       xlabel=viz.label_of(x), ylabel=viz.label_of(y))
    return None

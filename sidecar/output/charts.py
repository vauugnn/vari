"""Charts rendered by matplotlib in the sidecar, returned as inline SVG.

A Chart is a peer of PivotTable in the output tree: {"type":"Chart","svg":...}.
The renderer just drops the SVG into the Viewer, and HTML export inlines it.
Only legacy chart types (histogram, bar, pie, scatter, boxplot) — the Chart
Builder is permanently out of scope (HLD 1 non-goals).
"""
from __future__ import annotations

import io
from typing import Any, Optional, Sequence

import numpy as np

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# SPSS-ish chart styling.
_BAR_COLOR = "#4e79c4"
_EDGE = "#2f4f8a"
plt.rcParams.update({"font.size": 9, "font.family": "sans-serif", "axes.edgecolor": "#7f7f7f"})


def _finish(fig: Any, title: str) -> dict[str, Any]:
    if title:
        fig.suptitle(title, fontsize=11, fontweight="bold")
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    svg = buf.getvalue()
    svg = svg[svg.index("<svg") :]  # strip XML/DOCTYPE preamble
    return {"type": "Chart", "svg": svg}


def histogram(values: Sequence[float], title: str = "", xlabel: str = "",
              mean: Optional[float] = None, sd: Optional[float] = None, n: Optional[int] = None) -> dict[str, Any]:
    v = np.asarray([x for x in values if x == x], dtype=float)
    fig, ax = plt.subplots(figsize=(4.4, 3.2))
    if v.size:
        ax.hist(v, bins="auto", color=_BAR_COLOR, edgecolor=_EDGE, linewidth=0.5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Frequency")
    if mean is not None and sd:
        txt = f"Mean = {mean:.2f}\nStd. Dev. = {sd:.3f}" + (f"\nN = {n}" if n else "")
        ax.text(0.98, 0.97, txt, transform=ax.transAxes, ha="right", va="top", fontsize=8)
    return _finish(fig, title)


def bar_chart(labels: Sequence[str], counts: Sequence[float], title: str = "", xlabel: str = "") -> dict[str, Any]:
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    ax.bar([str(x) for x in labels], counts, color=_BAR_COLOR, edgecolor=_EDGE, linewidth=0.5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Frequency")
    fig.autofmt_xdate(rotation=30)
    return _finish(fig, title)


def pie_chart(labels: Sequence[str], counts: Sequence[float], title: str = "") -> dict[str, Any]:
    fig, ax = plt.subplots(figsize=(4.2, 3.4))
    ax.pie(counts, labels=[str(x) for x in labels], autopct="%1.1f%%", startangle=90,
           colors=["#4e79c4", "#e08a2f", "#7ab648", "#d9433f", "#9b6fbf", "#e6a417"])
    ax.axis("equal")
    return _finish(fig, title)


def scatter(x: Sequence[float], y: Sequence[float], title: str = "", xlabel: str = "", ylabel: str = "") -> dict[str, Any]:
    fig, ax = plt.subplots(figsize=(4.4, 3.4))
    ax.scatter(x, y, s=16, color=_BAR_COLOR, edgecolor=_EDGE, linewidth=0.4)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return _finish(fig, title)


def boxplot(groups: Sequence[Sequence[float]], labels: Sequence[str], title: str = "", ylabel: str = "") -> dict[str, Any]:
    fig, ax = plt.subplots(figsize=(4.4, 3.4))
    try:
        ax.boxplot([np.asarray(g, float) for g in groups], tick_labels=[str(x) for x in labels],
                   patch_artist=True, boxprops=dict(facecolor="#cfe0f2", edgecolor=_EDGE))
    except TypeError:  # older matplotlib
        ax.boxplot([np.asarray(g, float) for g in groups], labels=[str(x) for x in labels],
                   patch_artist=True, boxprops=dict(facecolor="#cfe0f2", edgecolor=_EDGE))
    ax.set_ylabel(ylabel)
    return _finish(fig, title)

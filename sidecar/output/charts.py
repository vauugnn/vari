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

# SPSS-ish chart styling.
_BAR_COLOR = "#4e79c4"
_EDGE = "#2f4f8a"

# matplotlib is imported lazily. Importing pyplot at module load triggers a
# first-run font-cache build (several seconds), which is fine in a long-lived
# process but blows past the packaged app's sidecar-ready ping window and shows
# "Processor unavailable". Nothing here touches matplotlib until a chart is
# actually drawn, so a sidecar that never plots never pays the cost.
_PLT: Any = None


def _plt() -> Any:
    global _PLT
    if _PLT is None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.rcParams.update({
            "font.size": 9.5,
            "font.family": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
            "axes.edgecolor": "#8a8a8a",
            "axes.linewidth": 0.8,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "xtick.major.size": 3,
            "ytick.major.size": 3,
        })
        _PLT = plt
    return _PLT


# Shared categorical colour cycle (SPSS-like order: blue, green, tan, red, …).
_PALETTE = ["#4e79c4", "#5aa552", "#d9a441", "#d9433f", "#8c66b5", "#41b2c2", "#e07b39", "#6d6e71"]


def _style_axes(fig: Any) -> None:
    """Apply the SPSS look to every axis: horizontal scale-grid, no top/right
    box, axis labels below the plot."""
    for ax in fig.axes:
        if getattr(ax, "name", "") == "3d":
            continue
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color="#d0d0d0", linewidth=0.6)
        ax.xaxis.grid(False)
        for side in ("top", "right"):
            if side in ax.spines:
                ax.spines[side].set_visible(False)


def _finish(fig: Any, title: str, subtitle: str = "", footnote: str = "") -> dict[str, Any]:
    _style_axes(fig)
    if title:
        fig.suptitle(title, fontsize=11.5, fontweight="bold", y=0.99)
    if subtitle:
        fig.text(0.5, 0.94, subtitle, ha="center", fontsize=9.5, color="#333")
    if footnote:
        fig.text(0.01, 0.005, footnote, ha="left", fontsize=8, color="#555")
    buf = io.StringIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    _plt().close(fig)
    svg = buf.getvalue()
    svg = svg[svg.index("<svg") :]  # strip XML/DOCTYPE preamble
    return {"type": "Chart", "svg": svg}


def histogram(values: Sequence[float], title: str = "", xlabel: str = "",
              mean: Optional[float] = None, sd: Optional[float] = None, n: Optional[int] = None,
              normal: bool = False) -> dict[str, Any]:
    v = np.asarray([x for x in values if x == x], dtype=float)
    fig, ax = _plt().subplots(figsize=(4.4, 3.2))
    if v.size:
        counts, edges, _ = ax.hist(v, bins="auto", color=_BAR_COLOR, edgecolor=_EDGE, linewidth=0.5)
        if normal and v.size > 1:
            m = float(v.mean())
            s = float(v.std(ddof=1)) or 1.0
            width = edges[1] - edges[0] if len(edges) > 1 else 1.0
            xs = np.linspace(v.min(), v.max(), 200)
            ys = (1.0 / (s * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((xs - m) / s) ** 2) * len(v) * width
            ax.plot(xs, ys, color="#2f2f2f", linewidth=1.3)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Frequency")
    if mean is not None and sd:
        txt = f"Mean = {mean:.2f}\nStd. Dev. = {sd:.3f}" + (f"\nN = {n}" if n else "")
        ax.text(0.98, 0.97, txt, transform=ax.transAxes, ha="right", va="top", fontsize=8)
    return _finish(fig, title)


def bar_chart(labels: Sequence[str], counts: Sequence[float], title: str = "", xlabel: str = "") -> dict[str, Any]:
    fig, ax = _plt().subplots(figsize=(4.6, 3.2))
    ax.bar([str(x) for x in labels], counts, color=_BAR_COLOR, edgecolor=_EDGE, linewidth=0.5)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Frequency")
    fig.autofmt_xdate(rotation=30)
    return _finish(fig, title)


def pie_chart(labels: Sequence[str], counts: Sequence[float], title: str = "") -> dict[str, Any]:
    fig, ax = _plt().subplots(figsize=(4.2, 3.4))
    ax.pie(counts, labels=[str(x) for x in labels], autopct="%1.1f%%", startangle=90,
           colors=["#4e79c4", "#e08a2f", "#7ab648", "#d9433f", "#9b6fbf", "#e6a417"])
    ax.axis("equal")
    return _finish(fig, title)


def scatter(x: Sequence[float], y: Sequence[float], title: str = "", xlabel: str = "", ylabel: str = "",
            fit: str = "") -> dict[str, Any]:
    fig, ax = _plt().subplots(figsize=(4.4, 3.4))
    xv = np.asarray(x, float)
    yv = np.asarray(y, float)
    ax.scatter(xv, yv, s=16, color=_BAR_COLOR, edgecolor=_EDGE, linewidth=0.4)
    if fit and xv.size > 2:
        deg = {"LINEAR": 1, "QUADRATIC": 2, "CUBIC": 3}.get(fit.upper(), 1)
        coef = np.polyfit(xv, yv, deg)
        xs = np.linspace(xv.min(), xv.max(), 200)
        ax.plot(xs, np.polyval(coef, xs), color="#d9433f", linewidth=1.4)
        # R² of the fit.
        resid = yv - np.polyval(coef, xv)
        ss_res = float((resid**2).sum())
        ss_tot = float(((yv - yv.mean()) ** 2).sum()) or 1.0
        r2 = 1 - ss_res / ss_tot
        ax.text(0.98, 0.02, f"R² Linear = {r2:.3f}" if deg == 1 else f"R² = {r2:.3f}",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=8, color="#a33")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return _finish(fig, title)


def line(x: Sequence[float], y: Sequence[float], title: str = "", xlabel: str = "", ylabel: str = "",
         diagonal: bool = False) -> dict[str, Any]:
    fig, ax = _plt().subplots(figsize=(4.4, 3.4))
    ax.plot(x, y, color=_BAR_COLOR, linewidth=1.6)
    if diagonal:
        ax.plot([0, 1], [0, 1], color="#999", linewidth=0.8, linestyle="--")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return _finish(fig, title)


def area(labels: Sequence[str], values: Sequence[float], title: str = "", xlabel: str = "", ylabel: str = "") -> dict[str, Any]:
    fig, ax = _plt().subplots(figsize=(4.6, 3.2))
    xs = list(range(len(labels)))
    ax.fill_between(xs, values, color=_BAR_COLOR, alpha=0.5)
    ax.plot(xs, values, color=_EDGE, linewidth=1.2)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(x) for x in labels], rotation=30)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return _finish(fig, title)


def error_bar(labels: Sequence[str], means: Sequence[float], errors: Sequence[float],
              title: str = "", xlabel: str = "", ylabel: str = "") -> dict[str, Any]:
    fig, ax = _plt().subplots(figsize=(4.6, 3.2))
    xs = list(range(len(labels)))
    ax.errorbar(xs, means, yerr=errors, fmt="o", color=_BAR_COLOR, ecolor=_EDGE, capsize=4)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(x) for x in labels], rotation=30)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return _finish(fig, title)


def qq(values: Sequence[float], title: str = "", normal: bool = True) -> dict[str, Any]:
    from scipy import stats as sps

    v = np.sort(np.asarray([x for x in values if x == x], dtype=float))
    n = v.size
    fig, ax = _plt().subplots(figsize=(4.2, 3.6))
    if n:
        probs = (np.arange(1, n + 1) - 0.5) / n
        theo = sps.norm.ppf(probs, loc=v.mean(), scale=v.std(ddof=1) or 1)
        if normal:
            ax.scatter(theo, v, s=14, color=_BAR_COLOR, edgecolor=_EDGE, linewidth=0.4)
            lo, hi = min(theo.min(), v.min()), max(theo.max(), v.max())
            ax.plot([lo, hi], [lo, hi], color="#999", linewidth=0.8)
            ax.set_xlabel("Expected Normal Value")
            ax.set_ylabel("Observed Value")
        else:  # P-P
            ecdf = probs
            tcdf = sps.norm.cdf((v - v.mean()) / (v.std(ddof=1) or 1))
            ax.scatter(tcdf, ecdf, s=14, color=_BAR_COLOR, edgecolor=_EDGE, linewidth=0.4)
            ax.plot([0, 1], [0, 1], color="#999", linewidth=0.8)
            ax.set_xlabel("Expected Cum Prob")
            ax.set_ylabel("Observed Cum Prob")
    return _finish(fig, title)


def boxplot(groups: Sequence[Sequence[float]], labels: Sequence[str], title: str = "", ylabel: str = "") -> dict[str, Any]:
    fig, ax = _plt().subplots(figsize=(4.4, 3.4))
    try:
        ax.boxplot([np.asarray(g, float) for g in groups], tick_labels=[str(x) for x in labels],
                   patch_artist=True, boxprops=dict(facecolor="#cfe0f2", edgecolor=_EDGE))
    except TypeError:  # older matplotlib
        ax.boxplot([np.asarray(g, float) for g in groups], labels=[str(x) for x in labels],
                   patch_artist=True, boxprops=dict(facecolor="#cfe0f2", edgecolor=_EDGE))
    ax.set_ylabel(ylabel)
    return _finish(fig, title)


def high_low(categories: Sequence[str], highs: Sequence[float], lows: Sequence[float],
             closes: Optional[Sequence[float]] = None, title: str = "", ylabel: str = "") -> dict[str, Any]:
    fig, ax = _plt().subplots(figsize=(4.6, 3.4))
    xs = list(range(len(categories)))
    for i in xs:
        ax.plot([i, i], [lows[i], highs[i]], color=_EDGE, linewidth=1.4)
        ax.plot([i - 0.15, i], [highs[i], highs[i]], color=_EDGE, linewidth=1.4)
        ax.plot([i, i + 0.15], [lows[i], lows[i]], color=_EDGE, linewidth=1.4)
        if closes is not None:
            ax.plot([i, i + 0.15], [closes[i], closes[i]], color=_BAR_COLOR, linewidth=1.6)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(c) for c in categories], rotation=30)
    ax.set_ylabel(ylabel)
    return _finish(fig, title)


def population_pyramid(labels: Sequence[str], left: Sequence[float], right: Sequence[float],
                       side_labels: Sequence[str], title: str = "", xlabel: str = "") -> dict[str, Any]:
    fig, ax = _plt().subplots(figsize=(4.8, 3.6))
    ys = list(range(len(labels)))
    ax.barh(ys, [-v for v in left], color=_BAR_COLOR, edgecolor=_EDGE, linewidth=0.5, label=str(side_labels[0]))
    ax.barh(ys, list(right), color="#e08a2f", edgecolor="#a75f16", linewidth=0.5, label=str(side_labels[1]))
    ax.set_yticks(ys)
    ax.set_yticklabels([str(x) for x in labels])
    ax.set_ylabel(xlabel)
    ticks = ax.get_xticks()
    ax.set_xticks(ticks)
    ax.set_xticklabels([str(int(abs(t))) for t in ticks])
    ax.legend(fontsize=8)
    return _finish(fig, title)


def control_chart(x: Sequence[float], y: Sequence[float], center: float, ucl: float, lcl: float,
                  title: str = "", ylabel: str = "") -> dict[str, Any]:
    fig, ax = _plt().subplots(figsize=(5.0, 3.2))
    ax.plot(x, y, marker="o", markersize=3, color=_BAR_COLOR, linewidth=1.0)
    ax.axhline(center, color="#2f7f2f", linewidth=1.0)
    ax.axhline(ucl, color="#d9433f", linewidth=1.0, linestyle="--")
    ax.axhline(lcl, color="#d9433f", linewidth=1.0, linestyle="--")
    for xi, yi in zip(x, y):
        if yi > ucl or yi < lcl:
            ax.plot([xi], [yi], marker="o", markersize=5, color="#d9433f")
    ax.text(x[-1] if len(x) else 0, ucl, " UCL", va="center", fontsize=7, color="#d9433f")
    ax.text(x[-1] if len(x) else 0, lcl, " LCL", va="center", fontsize=7, color="#d9433f")
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Sample")
    return _finish(fig, title)


def pareto(labels: Sequence[str], values: Sequence[float], title: str = "") -> dict[str, Any]:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(5.0, 3.4))
    xs = list(range(len(labels)))
    ax.bar(xs, values, color=_BAR_COLOR, edgecolor=_EDGE, linewidth=0.5)
    ax.set_xticks(xs)
    ax.set_xticklabels([str(x) for x in labels], rotation=30, ha="right", fontsize=7)
    total = float(sum(values)) or 1.0
    cum = np.cumsum(values) / total * 100.0
    ax2 = ax.twinx()
    ax2.plot(xs, cum, color="#d9433f", marker="o", markersize=3, linewidth=1.2)
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("Cumulative %")
    ax.set_ylabel("Count")
    return _finish(fig, title)


def bar3d(row_labels: Sequence[str], col_labels: Sequence[str], grid: Sequence[Sequence[float]],
          title: str = "", xlabel: str = "") -> dict[str, Any]:
    plt = _plt()
    fig = plt.figure(figsize=(4.8, 3.8))
    ax = fig.add_subplot(111, projection="3d")
    palette = ["#4e79c4", "#e08a2f", "#7ab648", "#d9433f", "#9b6fbf", "#e6a417"]
    for ci in range(len(col_labels)):
        xs = list(range(len(row_labels)))
        ys = [ci] * len(row_labels)
        zs = [0] * len(row_labels)
        heights = [grid[ri][ci] for ri in range(len(row_labels))]
        ax.bar3d(xs, ys, zs, 0.6, 0.6, heights, color=palette[ci % len(palette)], shade=True)
    ax.set_xticks(list(range(len(row_labels))))
    ax.set_xticklabels([str(x) for x in row_labels], fontsize=7)
    ax.set_yticks(list(range(len(col_labels))))
    ax.set_yticklabels([str(x) for x in col_labels], fontsize=7)
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_zlabel("Count", fontsize=8)
    return _finish(fig, title)

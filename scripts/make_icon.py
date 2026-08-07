import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch
import matplotlib.patheffects as pe

fig = plt.figure(figsize=(10.24, 10.24), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

# Dark rounded tile with a faint vertical sheen.
ax.add_patch(FancyBboxPatch((0.06, 0.05), 0.88, 0.90, boxstyle="round,pad=0,rounding_size=0.19",
                            linewidth=0, facecolor="#17171d"))
ax.add_patch(FancyBboxPatch((0.06, 0.52), 0.88, 0.43, boxstyle="round,pad=0,rounding_size=0.19",
                            linewidth=0, facecolor="#20212b", alpha=0.85))

# Sigma (Σ) as a node-and-edge network, blue -> purple gradient.
TL, TR, C, BL, BR = (0.33, 0.71), (0.67, 0.71), (0.50, 0.50), (0.33, 0.29), (0.67, 0.29)
edges = [(TR, TL), (TL, C), (C, BL), (BL, BR)]
cols = ["#4f7cf0", "#6a63ea", "#8455de", "#a441d4", "#c23fce"]
nodes = [TR, TL, C, BL, BR]

for a, b in edges:
    ln = FancyArrowPatch(a, b, arrowstyle="-", mutation_scale=1, linewidth=26,
                         color="#6f66e8", alpha=0.95, capstyle="round")
    ln.set_path_effects([pe.Stroke(linewidth=34, foreground="#2a2b3a"), pe.Normal()])
    ax.add_patch(ln)

for (x, y), col in zip(nodes, cols):
    ax.add_patch(Circle((x, y), 0.075, facecolor="#1a1b24", edgecolor="none", zorder=4))
    ax.add_patch(Circle((x, y), 0.062, facecolor=col, edgecolor="#ffffff", linewidth=3, zorder=5))
    ax.add_patch(Circle((x - 0.018, y + 0.018), 0.020, facecolor="#ffffff", alpha=0.55, edgecolor="none", zorder=6))

fig.savefig("build/icon.png", dpi=100, transparent=True)
print("wrote build/icon.png")

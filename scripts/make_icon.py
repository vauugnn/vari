import matplotlib
matplotlib.use("Agg")
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.collections import LineCollection
from matplotlib.colors import to_rgb

fig = plt.figure(figsize=(10.24, 10.24), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

# Rounded tile.
ax.add_patch(FancyBboxPatch((0.06, 0.06), 0.88, 0.88, boxstyle="round,pad=0,rounding_size=0.20",
                            linewidth=0, facecolor="#12294a"))
ax.add_patch(FancyBboxPatch((0.06, 0.52), 0.88, 0.42, boxstyle="round,pad=0,rounding_size=0.20",
                            linewidth=0, facecolor="#1c3f6f", alpha=0.7))

# Summation sigma as one thick gradient polyline: TR -> TL -> C -> BL -> BR.
pts = np.array([(0.70, 0.72), (0.32, 0.72), (0.52, 0.50), (0.32, 0.28), (0.70, 0.28)])
# densify
path = []
for i in range(len(pts) - 1):
    for t in np.linspace(0, 1, 60):
        path.append(pts[i] * (1 - t) + pts[i + 1] * t)
path = np.array(path)
segs = np.stack([path[:-1], path[1:]], axis=1)

c0, c1 = np.array(to_rgb("#4f9bff")), np.array(to_rgb("#b45cff"))
tt = np.linspace(0, 1, len(segs))[:, None]
colors = c0 * (1 - tt) + c1 * tt

lc = LineCollection(segs, colors=colors, linewidths=40, capstyle="round", joinstyle="round", zorder=5)
ax.add_collection(lc)
# rounded end caps + subtle glow
for (x, y), col in [(pts[0], "#4f9bff"), (pts[-1], "#b45cff")]:
    ax.add_patch(plt.Circle((x, y), 0.02, color=col, zorder=6))

fig.savefig("build/icon.png", dpi=100, transparent=True)
print("ok")

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

# Radical sign (square root): small lead-in, down to the vee, up to the top,
# then the horizontal vinculum bar.
pts = np.array([(0.22, 0.55), (0.30, 0.48), (0.38, 0.28), (0.50, 0.74), (0.80, 0.74)])
path = []
for i in range(len(pts) - 1):
    for t in np.linspace(0, 1, 60):
        path.append(pts[i] * (1 - t) + pts[i + 1] * t)
path = np.array(path)
segs = np.stack([path[:-1], path[1:]], axis=1)

c0, c1 = np.array(to_rgb("#4f9bff")), np.array(to_rgb("#b45cff"))
tt = np.linspace(0, 1, len(segs))[:, None]
colors = c0 * (1 - tt) + c1 * tt
ax.add_collection(LineCollection(segs, colors=colors, linewidths=38, capstyle="round", joinstyle="round", zorder=5))

fig.savefig("build/icon.png", dpi=100, transparent=True)
print("ok")

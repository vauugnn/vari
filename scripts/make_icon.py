import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle

fig = plt.figure(figsize=(10.24, 10.24), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

# Rounded tile background with a subtle vertical shade (two stacked rounds).
ax.add_patch(FancyBboxPatch((0.06, 0.05), 0.88, 0.90, boxstyle="round,pad=0,rounding_size=0.16",
                            linewidth=0, facecolor="#0f4c85"))
ax.add_patch(FancyBboxPatch((0.06, 0.30), 0.88, 0.65, boxstyle="round,pad=0,rounding_size=0.16",
                            linewidth=0, facecolor="#1e78c8"))

# White output panel.
ax.add_patch(FancyBboxPatch((0.19, 0.17), 0.62, 0.66, boxstyle="round,pad=0,rounding_size=0.05",
                            linewidth=0, facecolor="#ffffff"))

# Pivot-table header + grid (top of panel).
tx, ty, tw = 0.235, 0.66, 0.53
ax.add_patch(Rectangle((tx, ty), tw, 0.055, facecolor="#2f6fb0", edgecolor="none"))
for i in range(4):
    ax.add_patch(Rectangle((tx + i * tw / 4, ty), tw / 4 - 0.004, 0.05,
                           facecolor=["#d9433f", "#e6a417", "#7ab648", "#4e79c4"][i], edgecolor="none"))
for r in range(3):
    yy = ty - 0.05 * (r + 1)
    for c in range(4):
        ax.add_patch(Rectangle((tx + c * tw / 4, yy), tw / 4 - 0.004, 0.045,
                               facecolor="#eef2f7", edgecolor="#c9d6e6", linewidth=1))

# Ascending bar chart (bottom of panel).
bx, by = 0.255, 0.215
for i, (h, col) in enumerate([(0.10, "#d9433f"), (0.16, "#e6a417"), (0.22, "#7ab648"), (0.28, "#4e79c4")]):
    ax.add_patch(Rectangle((bx + i * 0.115, by), 0.075, h, facecolor=col, edgecolor="#ffffff", linewidth=2))

fig.savefig("build/icon.png", dpi=100, transparent=True)
print("wrote build/icon.png")

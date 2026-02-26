"""
Graph 5: Complete Heatmap — model × (SS levels + AG levels + overalls).

Shows every benchmark result in a single view: SS L0–L2, AG L0–L2,
plus SS Overall and AG Overall columns.
Sections separated by background-colored gaps.

Data loaded dynamically from result JSON files.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import numpy as np

from _load_results import load_from_cli

# ── Load data ─────────────────────────────────────────────────────────────────
data = load_from_cli()
models_data = data["models"]
sorted_models = data["sorted_models"]

n = len(sorted_models)
labels = [models_data[m]["label"] for m in sorted_models]

# Build the data: 8 logical columns grouped into 3 sections
col_labels = [
    "SS L0", "SS L1", "SS L2",
    "AG L0", "AG L1", "AG L2",
    "SS\nOverall", "AG\nOverall",
]

values = np.zeros((n, 8))
for i, m in enumerate(sorted_models):
    md = models_data[m]
    ss = md["ss"]
    ag = md["ag"]
    values[i, 0] = ss.get(0, {}).get("avg_score", 0.0) * 100
    values[i, 1] = ss.get(1, {}).get("avg_score", 0.0) * 100
    values[i, 2] = ss.get(2, {}).get("avg_score", 0.0) * 100
    values[i, 3] = ag.get(0, {}).get("avg_score", 0.0) * 100
    values[i, 4] = ag.get(1, {}).get("avg_score", 0.0) * 100
    values[i, 5] = ag.get(2, {}).get("avg_score", 0.0) * 100
    values[i, 6] = md["ss_overall"]
    values[i, 7] = md["ag_overall"]

# ── Layout: x-positions with gaps between sections ───────────────────────────
GAP = 0.4   # gap width between sections (cell width = 1.0)
CELL = 1.0

# Section groups: [0,1,2], gap, [3,4,5], gap, [6,7]
x_positions = []
x = 0.0
for j in range(8):
    x_positions.append(x)
    x += CELL
    if j in (2, 5):  # after SS L2 and AG L2
        x += GAP

# ── Figure setup ──────────────────────────────────────────────────────────────
BG = "#0d1117"
CELL_BG = "#161b22"

fig, ax = plt.subplots(figsize=(14, 12))
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)
plt.subplots_adjust(left=0.24, bottom=0.06, right=0.92, top=0.89)

# Custom colormap
cmap = mcolors.LinearSegmentedColormap.from_list(
    "bench", [CELL_BG, "#1a3a5c", "#2d6a4f", "#52b788", "#d9ed92", "#f4e285"])
norm = mcolors.Normalize(vmin=0, vmax=100)

# ── Draw cells as rectangles ─────────────────────────────────────────────────
for i in range(n):
    for j in range(8):
        val = values[i, j]
        color = cmap(norm(val))
        rect = mpatches.FancyBboxPatch(
            (x_positions[j], i - 0.5), CELL, 1.0,
            boxstyle="square,pad=0", facecolor=color, edgecolor="#30363d",
            linewidth=0.5)
        ax.add_patch(rect)
        text_color = "#0d1117" if val > 60 else "#e6edf3"
        ax.text(x_positions[j] + CELL / 2, i, f"{val:.0f}%",
                ha="center", va="center", fontsize=7.5, color=text_color,
                fontweight="bold")

# Set axis limits
total_width = x_positions[-1] + CELL
ax.set_xlim(-0.05, total_width + 0.05)
ax.set_ylim(n - 0.5, -0.5)

# ── Column labels (top) ─────────────────────────────────────────────────────
col_x_centers = [xp + CELL / 2 for xp in x_positions]
ax.set_xticks(col_x_centers)
ax.set_xticklabels(col_labels, fontsize=9, ha="center")
ax.xaxis.set_ticks_position("top")
ax.xaxis.set_label_position("top")

# ── Row labels (left) ───────────────────────────────────────────────────────
ax.set_yticks(np.arange(n))
ax.set_yticklabels(labels, fontsize=8.5, color="#c9d1d9")

for i, m in enumerate(sorted_models):
    if not models_data[m]["tool_trained"]:
        ax.get_yticklabels()[i].set_color("#8b949e")

ax.tick_params(colors="#8b949e", labelsize=9, length=0)

# Color column headers AFTER tick_params
C_SS       = "#648FFF"
C_AG       = "#FE6100"
C_SS_DARK  = "#4a6fbf"
C_AG_DARK  = "#c04d00"
col_colors = [C_SS, C_SS, C_SS, C_AG, C_AG, C_AG, C_SS_DARK, C_AG_DARK]
for tick_label, color in zip(ax.xaxis.get_ticklabels(), col_colors):
    tick_label.set_color(color)

# Remove axis spines (gaps handle visual separation)
for spine in ax.spines.values():
    spine.set_visible(False)

# ── Section headers ──────────────────────────────────────────────────────────
# Compute figure-coordinate centers for each section
fig.canvas.draw()
inv = fig.transFigure.inverted()

def section_center_x(col_indices):
    xs = []
    for c in col_indices:
        disp = ax.transData.transform((col_x_centers[c], 0))
        xs.append(inv.transform(disp)[0])
    return sum(xs) / len(xs)

ss_cx = section_center_x([0, 1, 2])
ag_cx = section_center_x([3, 4, 5])
ov_cx = section_center_x([6, 7])

fig.text(ss_cx, 0.913, "Single-shot", fontsize=10, color="#648FFF",
         ha="center", va="center", fontweight="bold")
fig.text(ag_cx, 0.913, "Agentic Loop", fontsize=10, color="#FE6100",
         ha="center", va="center", fontweight="bold")
fig.text(ov_cx, 0.913, "Overall", fontsize=10, color="#c9d1d9",
         ha="center", va="center", fontweight="bold")

ax.set_title(f"Complete Benchmark Heatmap — Avg Score by Model × Level × Methodology\n"
             f"{n} models · sorted by AG Overall descending",
             fontsize=12, color="#e6edf3", pad=42, fontweight="bold")

# ── Colorbar ─────────────────────────────────────────────────────────────────
sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, shrink=0.5, pad=0.02)
cbar.set_label("Score (%)", color="#8b949e", fontsize=9)
cbar.ax.tick_params(colors="#8b949e", labelsize=8)
cbar.outline.set_edgecolor("#30363d")

fig.text(0.10, 0.005, "\u2717 = not trained for tool calling (per LM Studio metadata)",
         ha="left", fontsize=7.5, color="#8b949e", style="italic")
fig.text(0.92, 0.005, "github.com/3615-computer/workunit-benchmarks",
         ha="right", fontsize=7.5, color="#484f58", style="italic")

output = "graph5_heatmap.png"
plt.savefig(output, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {output}")

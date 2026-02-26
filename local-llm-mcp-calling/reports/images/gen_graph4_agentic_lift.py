"""
Graph 4: Agentic Lift — how much does agentic looping improve over single-shot?

Horizontal bar chart of (AG_overall - SS_overall) per model, sorted by delta.
Positive bars = agentic helps, negative bars = agentic hurts.

Data loaded dynamically from result JSON files.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from _load_results import load_from_cli

# ── Load data ─────────────────────────────────────────────────────────────────
data = load_from_cli()
models_data = data["models"]
sorted_models = data["sorted_models"]

# Compute deltas and sort by delta descending
deltas = []
for m in sorted_models:
    md = models_data[m]
    ss = md["ss_overall"]
    ag = md["ag_overall"]
    delta = ag - ss
    deltas.append({
        "model": m,
        "label": md["label"],
        "tool_trained": md["tool_trained"],
        "ss": round(ss, 1),
        "ag": round(ag, 1),
        "delta": round(delta, 1),
    })

# Sort by delta descending (biggest improvement first)
deltas.sort(key=lambda d: d["delta"], reverse=True)

n = len(deltas)
labels = [d["label"] for d in deltas]
delta_vals = [d["delta"] for d in deltas]
tool_flags = [d["tool_trained"] for d in deltas]

y = np.arange(n)
bar_h = 0.6

fig, ax = plt.subplots(figsize=(13, 10))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#161b22")
plt.subplots_adjust(bottom=0.12, right=0.88)

# Colors: positive = green tones, negative = red tones
# Tool-trained vs not: solid vs hatched
C_POS_TOOL = "#3fb950"   # green
C_POS_CTRL = "#56d364"   # light green
C_NEG_TOOL = "#f85149"   # red
C_NEG_CTRL = "#ff7b72"   # light red

bar_colors = []
for d in deltas:
    if d["delta"] >= 0:
        bar_colors.append(C_POS_TOOL if d["tool_trained"] else C_POS_CTRL)
    else:
        bar_colors.append(C_NEG_TOOL if d["tool_trained"] else C_NEG_CTRL)

bars = ax.barh(y, delta_vals, bar_h, color=bar_colors, alpha=0.90,
               edgecolor="#c9d1d9", linewidth=0.4)

# Hatching for not-tool-trained
for i, d in enumerate(deltas):
    if not d["tool_trained"]:
        bars[i].set_hatch("//")
        bars[i].set_edgecolor("#c9d1d9")

# Value labels with SS→AG annotation
for i, (bar, d) in enumerate(zip(bars, deltas)):
    val = d["delta"]
    sign = "+" if val > 0 else ""
    # Place label at end of bar
    if val >= 0:
        x = val + 0.8
        ha = "left"
    else:
        x = val - 0.8
        ha = "right"
    ax.text(x, bar.get_y() + bar.get_height()/2,
            f"{sign}{val:.0f}pp  ({d['ss']:.0f}%→{d['ag']:.0f}%)",
            va="center", ha=ha, fontsize=7.5, color="#e6edf3", fontweight="bold")

# Zero line
ax.axvline(0, color="#8b949e", linewidth=0.8, zorder=1)

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=8.5, color="#c9d1d9")
for tick, flag in zip(ax.get_yticklabels(), tool_flags):
    if not flag:
        tick.set_color("#8b949e")

ax.set_xlabel("Agentic Lift (percentage points)", fontsize=10, color="#8b949e", labelpad=8)
ax.set_title(f"Agentic Lift — How Much Does Agentic Looping Improve Over Single-shot?\n"
             f"{n} models · AG Overall − SS Overall (percentage points)",
             fontsize=12, color="#e6edf3", pad=14, fontweight="bold")

# Dynamic x-axis limits with padding
min_delta = min(delta_vals)
max_delta = max(delta_vals)
ax.set_xlim(min(min_delta - 15, -10), max(max_delta + 20, 10))
ax.set_ylim(-0.7, n - 0.3)
ax.tick_params(colors="#8b949e", labelsize=9)
for spine in ax.spines.values():
    spine.set_edgecolor("#30363d")
ax.xaxis.grid(True, color="#21262d", linewidth=0.8, linestyle="--")
ax.set_axisbelow(True)

# Legend
patches = [
    mpatches.Patch(facecolor=C_POS_TOOL, label="Positive lift · tool-trained",
                   edgecolor="#c9d1d9", linewidth=0.6),
    mpatches.Patch(facecolor=C_POS_CTRL, label="Positive lift · not tool-trained",
                   hatch="//", edgecolor="#c9d1d9", linewidth=0.6),
    mpatches.Patch(facecolor=C_NEG_TOOL, label="Negative lift · tool-trained",
                   edgecolor="#c9d1d9", linewidth=0.6),
    mpatches.Patch(facecolor=C_NEG_CTRL, label="Negative lift · not tool-trained",
                   hatch="//", edgecolor="#c9d1d9", linewidth=0.6),
]
fig.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.45, 0.01),
           ncol=4, fontsize=8.5, framealpha=0.25, edgecolor="#30363d",
           facecolor="#161b22", labelcolor="#c9d1d9")

fig.text(0.99, 0.005, "github.com/3615-computer/workunit-benchmarks",
         ha="right", fontsize=7.5, color="#484f58", style="italic")

output = "graph4_agentic_lift.png"
plt.savefig(output, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {output}")

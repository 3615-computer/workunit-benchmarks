"""
Graph 2: L0 / L1 / L2 pass rates (agentic loop) — grouped bars per model.
Hero image for reddit_post_AIToolsPerformance.md

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

labels     = [models_data[m]["label"] for m in sorted_models]
tool_flags = [models_data[m]["tool_trained"] for m in sorted_models]

# Extract per-level agentic pass rates (as percentage)
l0_vals = []
l1_vals = []
l2_vals = []
for m in sorted_models:
    ag = models_data[m]["ag"]
    l0_vals.append(round(ag.get(0, {}).get("pass_rate", 0.0) * 100))
    l1_vals.append(round(ag.get(1, {}).get("pass_rate", 0.0) * 100))
    l2_vals.append(round(ag.get(2, {}).get("pass_rate", 0.0) * 100))

n = len(sorted_models)
y = np.arange(n)
bar_h = 0.24

fig, ax = plt.subplots(figsize=(13, 12))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#161b22")
# Bottom margin: enough for legend (3 rows) + footnote
# Right margin: enough for inline annotations
plt.subplots_adjust(bottom=0.20, right=0.84)

# IBM Design Library colorblind-safe palette
C_L0 = "#648FFF"   # blue
C_L1 = "#FE6100"   # orange
C_L2 = "#FFB000"   # yellow

bars_l0 = ax.barh(y + bar_h,  l0_vals, bar_h, color=C_L0, alpha=0.90)
bars_l1 = ax.barh(y,          l1_vals, bar_h, color=C_L1, alpha=0.90)
bars_l2 = ax.barh(y - bar_h,  l2_vals, bar_h, color=C_L2, alpha=0.90)

# Value labels — always shown including 0%, bold
for bars, vals in [(bars_l0, l0_vals), (bars_l1, l1_vals), (bars_l2, l2_vals)]:
    for bar, val in zip(bars, vals):
        x = val + 0.8 if val > 0 else 1.2
        ax.text(x, bar.get_y() + bar.get_height()/2,
                f"{val}%", va="center", ha="left", fontsize=7,
                color="#e6edf3", fontweight="bold")

# ── Dynamic inline annotations for anomalies ──────────────────────────────────
annotations = []
for i in range(n):
    l0, l1, l2 = l0_vals[i], l1_vals[i], l2_vals[i]
    # Skip models with all zeros (no meaningful anomaly)
    if l0 == 0 and l1 == 0 and l2 == 0:
        continue
    # L2 > L0 and L2 > L1 (anomalous: higher score on hardest level)
    if l2 > l0 and l2 > l1:
        annotations.append(
            (i, f"\u2190 L2 ({l2}%) > L0 & L1  anomaly", "#ffa657"))
    # L2 > L0 only
    elif l2 > l0 and l0 > 0:
        annotations.append(
            (i, f"\u2190 L2 ({l2}%) > L0 ({l0}%)  anomaly", "#ffa657"))
    # L0 < L1 (inverted difficulty)
    elif l0 < l1 and l0 > 0:
        annotations.append(
            (i, f"\u2190 {l0}% L0 but {l1}% L1  inverted", "#ff6b6b"))

for ypos, txt, col in annotations:
    t = ax.text(102, ypos, txt, va="center", ha="left", fontsize=7.5, color=col)
    t.set_clip_on(False)

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=8.5, color="#c9d1d9")
for tick, flag in zip(ax.get_yticklabels(), tool_flags):
    if not flag:
        tick.set_color("#8b949e")

ax.set_xlabel("Pass Rate (%)", fontsize=10, color="#8b949e", labelpad=8)
ax.set_title(f"Agentic Loop \u2014 Pass Rate by Difficulty Level\n"
             f"{n} models \u00b7 L0 Explicit / L1 Natural language / L2 Reasoning",
             fontsize=12, color="#e6edf3", pad=14, fontweight="bold")

ax.set_xlim(0, 102)
ax.set_ylim(-0.8, n - 0.2)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}%"))
ax.tick_params(colors="#8b949e", labelsize=9)
for spine in ax.spines.values():
    spine.set_edgecolor("#30363d")
ax.xaxis.grid(True, color="#21262d", linewidth=0.8, linestyle="--")
ax.set_axisbelow(True)

# Legend placed below chart via fig.legend, well clear of x-axis label
patches = [
    mpatches.Patch(color=C_L0, label="L0 \u2014 Explicit (11 tasks): exact tool + params given"),
    mpatches.Patch(color=C_L1, label="L1 \u2014 Natural language (10 tasks): model picks tool + maps params"),
    mpatches.Patch(color=C_L2, label="L2 \u2014 Reasoning (7 tasks): high-level goal, must chain IDs"),
]
fig.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.42, 0.07),
           ncol=1, fontsize=8.5, framealpha=0.25, edgecolor="#30363d",
           facecolor="#161b22", labelcolor="#c9d1d9")

fig.text(0.13, 0.005, "\u2717 = not trained for tool calling (per LM Studio metadata)",
         ha="left", fontsize=7.5, color="#8b949e", style="italic")
fig.text(0.99, 0.005, "github.com/3615-computer/workunit-benchmarks",
         ha="right", fontsize=7.5, color="#484f58", style="italic")

output = "graph2_level_breakdown_agentic.png"
plt.savefig(output, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {output}")

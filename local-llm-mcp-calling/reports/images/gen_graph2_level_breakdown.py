"""
Graph 2: L0 / L1 / L2 pass rates (agentic loop) — grouped bars per model.
Hero image for reddit_post_AIToolsPerformance.md
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Data: (label, L0, L1, L2, tool_trained)
# Sorted by AG Overall descending
models = [
    ("granite-4-h-tiny 7B",         100, 100, 57, True),
    ("qwen3-coder-30b 30B",         100,  90, 57, True),
    ("magistral-small 24B",         100, 100, 43, True),
    ("qwen3-4b-thinking 4B",        100,  80, 57, True),
    ("gpt-oss-20b 20B",             100,  80, 43, True),
    ("ministral-14b-reasoning 14B", 100,  90, 29, True),
    ("ernie-4.5-21b 21B ✗",         100, 100, 29, False),
    ("ministral-3-3b 3B",            91,  90, 29, True),
    ("gemma-3-12b 12B ✗",            91,  80, 29, False),
    ("rnj-1 8.3B",                  100,  80,  0, True),
    ("nemotron-3-nano 30B",         100,  60, 14, True),
    ("glm-4.6v-flash 9.4B",          91,  60, 14, True),
    ("phi-4-reasoning-plus 15B ✗",   46,  80, 43, False),
    ("glm-4.7-flash 30B",            55,  50, 71, True),
    ("qwen2.5-coder-32b 32B ✗",      91,  50, 14, False),
    ("deepseek-r1-qwen3-8b 8B ✗",    18,   0,  0, False),
    ("seed-oss-36b 36B",              0,   0,  0, True),
]

labels     = [m[0] for m in models]
l0_vals    = [m[1] for m in models]
l1_vals    = [m[2] for m in models]
l2_vals    = [m[3] for m in models]
tool_flags = [m[4] for m in models]

n = len(models)
y = np.arange(n)
bar_h = 0.24

fig, ax = plt.subplots(figsize=(13, 10))
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

# Inline annotations — no arrows, placed in the right margin at the model's row
glm47_idx = next(i for i, m in enumerate(models) if "glm-4.7" in m[0])
phi_idx   = next(i for i, m in enumerate(models) if "phi-4"   in m[0])

for ypos, txt, col in [
    (glm47_idx, "← L2 (71%) > L0 & L1  anomaly", "#ffa657"),
    (phi_idx,   "← 46% L0 but 80% L1  inverted",  "#ff6b6b"),
]:
    t = ax.text(102, ypos, txt, va="center", ha="left", fontsize=7.5, color=col)
    t.set_clip_on(False)

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=8.5, color="#c9d1d9")
for tick, flag in zip(ax.get_yticklabels(), tool_flags):
    if not flag:
        tick.set_color("#8b949e")

ax.set_xlabel("Pass Rate (%)", fontsize=10, color="#8b949e", labelpad=8)
ax.set_title("Agentic Loop — Pass Rate by Difficulty Level\n"
             "17 models · L0 Explicit / L1 Natural language / L2 Reasoning",
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
    mpatches.Patch(color=C_L0, label="L0 — Explicit (11 tasks): exact tool + params given"),
    mpatches.Patch(color=C_L1, label="L1 — Natural language (10 tasks): model picks tool + maps params"),
    mpatches.Patch(color=C_L2, label="L2 — Reasoning (7 tasks): high-level goal, must chain IDs"),
]
fig.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.42, 0.07),
           ncol=1, fontsize=8.5, framealpha=0.25, edgecolor="#30363d",
           facecolor="#161b22", labelcolor="#c9d1d9")

fig.text(0.13, 0.005, "✗ = not trained for tool calling (per LM Studio metadata)",
         ha="left", fontsize=7.5, color="#8b949e", style="italic")
fig.text(0.99, 0.005, "workunit.app · github.com/3615-computer/workunit-benchmarks",
         ha="right", fontsize=7.5, color="#484f58", style="italic")

output = "graph2_level_breakdown_agentic.png"
plt.savefig(output, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {output}")

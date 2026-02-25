"""
Graph 1: Single-shot Overall vs Agentic Overall — side-by-side horizontal bars.
Hero image for reddit_post_LocalLLaMA.md
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Data: (label, ss_overall, ag_overall, tool_trained)
# Sorted by AG Overall descending
models = [
    ("qwen3-coder-30b 30B",              73,  92, True),
    ("qwen3-coder-next 80B",             81,  92, True),
    ("ernie-4.5-21b 21B ✗",               0,  85, False),
    ("qwen3-4b-thinking 4B",             37,  85, True),
    ("granite-4-h-tiny 7B",              73,  85, True),
    ("gpt-oss-20b 20B",                  76,  85, True),
    ("ministral-14b-reasoning 14B",      78,  84, True),
    ("magistral-small 24B",              78,  82, True),
    ("devstral-small 24B",               79,  82, True),
    ("ministral-3-3b 3B",                76,  81, True),
    ("gemma-3-12b 12B ✗",                 0,  80, False),
    ("qwen3.5-35b 35B",                  65,  77, True),
    ("nemotron-3-nano 30B",              51,  77, True),
    ("essentialai/rnj-1 8.3B",           74,  77, True),
    ("lfm2-24b 24B",                     78,  73, True),
    ("glm-4.6v-flash 9.4B",             61,  70, True),
    ("glm-4.7-flash 30B",               44,  63, True),
    ("phi-4-reasoning-plus 15B ✗",       38,  62, False),
    ("qwen2.5-coder-32b 32B ✗",          38,  58, False),
    ("deepseek-r1-qwen3-8b 8B ✗",        3,   0, False),
    ("seed-oss-36b 36B",                 71,   0, True),
]

labels      = [m[0] for m in models]
ss_vals     = [m[1] for m in models]
ag_vals     = [m[2] for m in models]
tool_flags  = [m[3] for m in models]

n = len(models)
y = np.arange(n)
bar_h = 0.35

fig, ax = plt.subplots(figsize=(13, 12))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#161b22")
# Extra bottom margin for legend, right margin for inline annotations
plt.subplots_adjust(bottom=0.14, right=0.84)

# IBM Design Library colorblind-safe palette
# Color + hatching for maximum accessibility (protanopia, deuteranopia, tritanopia)
SS_TOOL = "#648FFF"   # blue
SS_CTRL = "#785EF0"   # purple
AG_TOOL = "#FE6100"   # orange
AG_CTRL = "#FFB000"   # yellow

ss_colors = [SS_TOOL if t else SS_CTRL for t in tool_flags]
ag_colors = [AG_TOOL if t else AG_CTRL for t in tool_flags]

bars_ss = ax.barh(y + bar_h/2, ss_vals, bar_h, color=ss_colors, alpha=0.85,
                  edgecolor="#c9d1d9", linewidth=0.4)
bars_ag = ax.barh(y - bar_h/2, ag_vals, bar_h, color=ag_colors, alpha=0.95,
                  edgecolor="#c9d1d9", linewidth=0.4)

# Apply hatching: tool-trained = no hatch, not-tool-trained = hatched
for i, t in enumerate(tool_flags):
    if not t:
        bars_ss[i].set_hatch("//")
        bars_ag[i].set_hatch("//")
        bars_ss[i].set_edgecolor("#c9d1d9")
        bars_ag[i].set_edgecolor("#c9d1d9")

# Value labels — always shown, including 0%.
# SS: regular weight, placed just right of bar (or at x=1.5 for zero)
# AG: bold, placed just right of bar (or at x=1.5 for zero)
for bar, val in zip(bars_ss, ss_vals):
    x = val + 1.2 if val > 0 else 1.5
    ax.text(x, bar.get_y() + bar.get_height()/2,
            f"{val}%", va="center", ha="left", fontsize=7.5, color="#c9d1d9")

for bar, val in zip(bars_ag, ag_vals):
    x = val + 1.2 if val > 0 else 1.5
    ax.text(x, bar.get_y() + bar.get_height()/2,
            f"{val}%", va="center", ha="left", fontsize=7.5,
            color="#e6edf3", fontweight="bold")

# Inline text annotations — no arrows, placed to the right of the value labels
seed_idx  = next(i for i, m in enumerate(models) if "seed"  in m[0])
ernie_idx = next(i for i, m in enumerate(models) if "ernie" in m[0])
gemma_idx = next(i for i, m in enumerate(models) if "gemma" in m[0])

for ypos, txt, col in [
    (seed_idx,  "← 71% SS but 0% AG (paradox)",         "#ff6b6b"),
    (ernie_idx, "← 0% SS but 85% AG (not tool-trained)", "#a8f0a8"),
    (gemma_idx, "← 0% SS but 80% AG (not tool-trained)", "#a8f0a8"),
]:
    t = ax.text(102, ypos, txt, va="center", ha="left", fontsize=7.5, color=col)
    t.set_clip_on(False)

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=9, color="#c9d1d9")
ax.set_xlabel("Overall Score (%)", fontsize=10, color="#8b949e", labelpad=8)
ax.set_title("Local LLM MCP Tool Calling — Single-shot vs Agentic Overall Score\n"
             "21 models · 28 tasks · 3 difficulty levels",
             fontsize=12, color="#e6edf3", pad=14, fontweight="bold")

ax.set_xlim(0, 102)
ax.set_ylim(-0.7, n - 0.3)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}%"))
ax.tick_params(colors="#8b949e", labelsize=9)
for spine in ax.spines.values():
    spine.set_edgecolor("#30363d")
ax.xaxis.grid(True, color="#21262d", linewidth=0.8, linestyle="--")
ax.set_axisbelow(True)

# Legend below the chart, 4 columns (hatched patches for not-tool-trained)
patches = [
    mpatches.Patch(facecolor=SS_TOOL, label="Single-shot · tool-trained",
                   edgecolor="#c9d1d9", linewidth=0.6),
    mpatches.Patch(facecolor=SS_CTRL, label="Single-shot · not tool-trained",
                   hatch="//", edgecolor="#c9d1d9", linewidth=0.6),
    mpatches.Patch(facecolor=AG_TOOL, label="Agentic loop · tool-trained",
                   edgecolor="#c9d1d9", linewidth=0.6),
    mpatches.Patch(facecolor=AG_CTRL, label="Agentic loop · not tool-trained",
                   hatch="//", edgecolor="#c9d1d9", linewidth=0.6),
]
fig.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.42, 0.01),
           ncol=4, fontsize=8.5, framealpha=0.25, edgecolor="#30363d",
           facecolor="#161b22", labelcolor="#c9d1d9")

fig.text(0.99, 0.005, "github.com/3615-computer/workunit-benchmarks",
         ha="right", fontsize=7.5, color="#484f58", style="italic")

output = "graph1_ss_vs_ag_overall.png"
plt.savefig(output, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {output}")

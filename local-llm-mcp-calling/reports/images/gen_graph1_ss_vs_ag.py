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
    ("granite-4-h-tiny 7B",              60,  89, True),
    ("qwen3-coder-30b 30B",              60,  88, True),
    ("magistral-small 24B",              63,  85, True),
    ("qwen3-4b-thinking 4B",             60,  85, True),
    ("gpt-oss-20b 20B",                  57,  85, True),
    ("ministral-14b-reasoning 14B",      63,  84, True),
    ("ernie-4.5-21b 21B ✗",              0,   83, False),
    ("ministral-3-3b 3B",                82,  81, True),
    ("gemma-3-12b 12B ✗",                0,   78, False),
    ("rnj-1 8.3B",                       60,  77, True),
    ("nemotron-3-nano 30B",              50,  71, True),
    ("glm-4.6v-flash 9.4B",             54,  68, True),
    ("phi-4-reasoning-plus 15B ✗",       42,  64, False),
    ("glm-4.7-flash 30B",               35,  61, True),
    ("qwen2.5-coder-32b 32B ✗",          35,  58, False),
    ("deepseek-r1-qwen3-8b 8B ✗",        3,    6, False),
    ("seed-oss-36b 36B",                 60,   0, True),
]

labels      = [m[0] for m in models]
ss_vals     = [m[1] for m in models]
ag_vals     = [m[2] for m in models]
tool_flags  = [m[3] for m in models]

n = len(models)
y = np.arange(n)
bar_h = 0.35

fig, ax = plt.subplots(figsize=(13, 10))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#161b22")
# Extra bottom margin for legend, right margin for inline annotations
plt.subplots_adjust(bottom=0.14, right=0.84)

# Four clearly distinct colors
# SS tool-trained:  steel blue
# SS not-tool-trained: violet
# AG tool-trained:  orange
# AG not-tool-trained: red
SS_TOOL = "#4a9eff"   # steel blue
SS_CTRL = "#b57bee"   # violet
AG_TOOL = "#f97316"   # orange
AG_CTRL = "#ef4444"   # red

ss_colors = [SS_TOOL if t else SS_CTRL for t in tool_flags]
ag_colors = [AG_TOOL if t else AG_CTRL for t in tool_flags]

bars_ss = ax.barh(y + bar_h/2, ss_vals, bar_h, color=ss_colors, alpha=0.85)
bars_ag = ax.barh(y - bar_h/2, ag_vals, bar_h, color=ag_colors, alpha=0.95)

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
# seed paradox: sits at the top (index 0 when reversed = bottom of chart = last row)
seed_idx  = next(i for i, m in enumerate(models) if "seed"  in m[0])
ernie_idx = next(i for i, m in enumerate(models) if "ernie" in m[0])
gemma_idx = next(i for i, m in enumerate(models) if "gemma" in m[0])

# These go in the right margin beyond x=100, no arrow needed — the row position
# already links the text to the model
for ypos, txt, col in [
    (seed_idx,  "← 60% SS but 0% AG (paradox)",         "#ff6b6b"),
    (ernie_idx, "← 0% SS but 83% AG (not tool-trained)", "#a8f0a8"),
    (gemma_idx, "← 0% SS but 78% AG (not tool-trained)", "#a8f0a8"),
]:
    t = ax.text(102, ypos, txt, va="center", ha="left", fontsize=7.5, color=col)
    t.set_clip_on(False)

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=9, color="#c9d1d9")
ax.set_xlabel("Overall Score (%)", fontsize=10, color="#8b949e", labelpad=8)
ax.set_title("Local LLM MCP Tool Calling — Single-shot vs Agentic Overall Score\n"
             "17 models · 28 tasks · 3 difficulty levels",
             fontsize=12, color="#e6edf3", pad=14, fontweight="bold")

ax.set_xlim(0, 102)
ax.set_ylim(-0.7, n - 0.3)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}%"))
ax.tick_params(colors="#8b949e", labelsize=9)
for spine in ax.spines.values():
    spine.set_edgecolor("#30363d")
ax.xaxis.grid(True, color="#21262d", linewidth=0.8, linestyle="--")
ax.set_axisbelow(True)

# Legend below the chart, 4 columns
patches = [
    mpatches.Patch(color=SS_TOOL, label="Single-shot · tool-trained"),
    mpatches.Patch(color=SS_CTRL, label="Single-shot · not tool-trained"),
    mpatches.Patch(color=AG_TOOL, label="Agentic loop · tool-trained"),
    mpatches.Patch(color=AG_CTRL, label="Agentic loop · not tool-trained"),
]
fig.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.42, 0.01),
           ncol=4, fontsize=8.5, framealpha=0.25, edgecolor="#30363d",
           facecolor="#161b22", labelcolor="#c9d1d9")

fig.text(0.99, 0.005, "workunit.app · github.com/3615-computer/workunit-benchmarks",
         ha="right", fontsize=7.5, color="#484f58", style="italic")

output = "graph1_ss_vs_ag_overall.png"
plt.savefig(output, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {output}")

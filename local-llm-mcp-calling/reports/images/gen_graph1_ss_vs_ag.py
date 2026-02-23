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

# Leave right margin for annotations, extra bottom margin for legend
fig, ax = plt.subplots(figsize=(13, 10))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#161b22")
plt.subplots_adjust(bottom=0.14, right=0.88)

# Four clearly distinct colors
# SS tool-trained:  steel blue
# SS control:       purple / violet
# AG tool-trained:  orange
# AG control:       red / crimson
SS_TOOL = "#4a9eff"   # steel blue
SS_CTRL = "#b57bee"   # violet
AG_TOOL = "#f97316"   # orange
AG_CTRL = "#ef4444"   # red

ss_colors = [SS_TOOL if t else SS_CTRL for t in tool_flags]
ag_colors = [AG_TOOL if t else AG_CTRL for t in tool_flags]

bars_ss = ax.barh(y + bar_h/2, ss_vals, bar_h, color=ss_colors, alpha=0.85, label="_ss")
bars_ag = ax.barh(y - bar_h/2, ag_vals, bar_h, color=ag_colors, alpha=0.95, label="_ag")

# Value labels
for bar, val in zip(bars_ss, ss_vals):
    if val > 0:
        ax.text(val + 1, bar.get_y() + bar.get_height()/2, f"{val}%",
                va="center", ha="left", fontsize=7.5, color="#c9d1d9")

for bar, val in zip(bars_ag, ag_vals):
    if val > 0:
        ax.text(val + 1, bar.get_y() + bar.get_height()/2, f"{val}%",
                va="center", ha="left", fontsize=7.5, color="#c9d1d9", fontweight="bold")

# Annotations — placed in the right margin (x > 100), clear of bars
seed_idx  = next(i for i, m in enumerate(models) if "seed"  in m[0])
ernie_idx = next(i for i, m in enumerate(models) if "ernie" in m[0])
gemma_idx = next(i for i, m in enumerate(models) if "gemma" in m[0])

ax.annotate("60% SS → 0% AG\n(paradox)",
            xy=(1, seed_idx - bar_h/2),
            xytext=(105, seed_idx),
            fontsize=7.5, color="#ff6b6b",
            arrowprops=dict(arrowstyle="->", color="#ff6b6b", lw=1,
                            connectionstyle="arc3,rad=0.0"),
            ha="left", va="center",
            annotation_clip=False)

ax.annotate("0% SS → 83% AG\n(control flip)",
            xy=(1, ernie_idx - bar_h/2),
            xytext=(105, ernie_idx),
            fontsize=7.5, color="#a8f0a8",
            arrowprops=dict(arrowstyle="->", color="#a8f0a8", lw=1,
                            connectionstyle="arc3,rad=0.0"),
            ha="left", va="center",
            annotation_clip=False)

ax.annotate("0% SS → 78% AG\n(control flip)",
            xy=(1, gemma_idx - bar_h/2),
            xytext=(105, gemma_idx),
            fontsize=7.5, color="#a8f0a8",
            arrowprops=dict(arrowstyle="->", color="#a8f0a8", lw=1,
                            connectionstyle="arc3,rad=0.0"),
            ha="left", va="center",
            annotation_clip=False)

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=9, color="#c9d1d9")
ax.set_xlabel("Overall Score (%)", fontsize=10, color="#8b949e", labelpad=8)
ax.set_title("Local LLM MCP Tool Calling — Single-shot vs Agentic Overall Score\n17 models · 28 tasks · 3 difficulty levels",
             fontsize=12, color="#e6edf3", pad=14, fontweight="bold")

ax.set_xlim(0, 102)
ax.set_ylim(-0.7, n - 0.3)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}%"))
ax.tick_params(colors="#8b949e", labelsize=9)
for spine in ax.spines.values():
    spine.set_edgecolor("#30363d")
ax.xaxis.grid(True, color="#21262d", linewidth=0.8, linestyle="--")
ax.set_axisbelow(True)

# Legend below the chart
patches = [
    mpatches.Patch(color=SS_TOOL, label="Single-shot · tool-trained"),
    mpatches.Patch(color=SS_CTRL, label="Single-shot · control group"),
    mpatches.Patch(color=AG_TOOL, label="Agentic loop · tool-trained"),
    mpatches.Patch(color=AG_CTRL, label="Agentic loop · control group"),
]
ax.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.42, -0.11),
          ncol=4, fontsize=8.5, framealpha=0.25, edgecolor="#30363d",
          facecolor="#161b22", labelcolor="#c9d1d9")

fig.text(0.99, 0.005, "workunit.app · github.com/3615-computer/workunit-benchmarks",
         ha="right", fontsize=7.5, color="#484f58", style="italic")

output = "graph1_ss_vs_ag_overall.png"
plt.savefig(output, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {output}")

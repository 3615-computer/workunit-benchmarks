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
# SS Overall = round((L0 + L1 + L2) / 3), AG Overall from aggregated report
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

fig, ax = plt.subplots(figsize=(12, 9))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#161b22")

# Colors
SS_TOOL    = "#4a9eff"   # blue  — tool-trained, single-shot
SS_CTRL    = "#7db8ff"   # light blue — control, single-shot
AG_TOOL    = "#f97316"   # orange — tool-trained, agentic
AG_CTRL    = "#fbbf7c"   # light orange — control, agentic

ss_colors = [SS_TOOL if t else SS_CTRL for t in tool_flags]
ag_colors = [AG_TOOL if t else AG_CTRL for t in tool_flags]

bars_ss = ax.barh(y + bar_h/2, ss_vals, bar_h, color=ss_colors, label="Single-shot", alpha=0.85)
bars_ag = ax.barh(y - bar_h/2, ag_vals, bar_h, color=ag_colors, label="Agentic loop", alpha=0.95)

# Value labels
for bar, val in zip(bars_ss, ss_vals):
    if val > 0:
        ax.text(val + 1, bar.get_y() + bar.get_height()/2, f"{val}%",
                va="center", ha="left", fontsize=7.5, color="#c9d1d9")

for bar, val in zip(bars_ag, ag_vals):
    if val > 0:
        ax.text(val + 1, bar.get_y() + bar.get_height()/2, f"{val}%",
                va="center", ha="left", fontsize=7.5, color="#c9d1d9", fontweight="bold")

# Highlight the seed anomaly with annotation
seed_idx = next(i for i, m in enumerate(models) if "seed" in m[0])
ax.annotate("60% SS → 0% AG paradox",
            xy=(3, seed_idx - bar_h/2),
            xytext=(38, seed_idx - bar_h/2 - 2.8),
            fontsize=7.5, color="#ff6b6b",
            arrowprops=dict(arrowstyle="->", color="#ff6b6b", lw=1, connectionstyle="arc3,rad=0.2"),
            ha="left")

# Annotate the control group flip (ernie)
ernie_idx = next(i for i, m in enumerate(models) if "ernie" in m[0])
ax.annotate("0% SS → 83% AG\ncontrol group flip",
            xy=(3, ernie_idx - bar_h/2),
            xytext=(38, ernie_idx + 2.2),
            fontsize=7.5, color="#a8f0a8",
            arrowprops=dict(arrowstyle="->", color="#a8f0a8", lw=1, connectionstyle="arc3,rad=-0.2"),
            ha="left")

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=9, color="#c9d1d9")
ax.set_xlabel("Overall Score (%)", fontsize=10, color="#8b949e", labelpad=8)
ax.set_title("Local LLM MCP Tool Calling — Single-shot vs Agentic Overall Score\n17 models · 28 tasks · 3 difficulty levels",
             fontsize=12, color="#e6edf3", pad=14, fontweight="bold")

ax.set_xlim(0, 115)
ax.set_ylim(-0.7, n - 0.3)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}%"))
ax.tick_params(colors="#8b949e", labelsize=9)
for spine in ax.spines.values():
    spine.set_edgecolor("#30363d")
ax.xaxis.grid(True, color="#21262d", linewidth=0.8, linestyle="--")
ax.set_axisbelow(True)

# Legend
patches = [
    mpatches.Patch(color=SS_TOOL, label="Single-shot · tool-trained"),
    mpatches.Patch(color=SS_CTRL, label="Single-shot · control group"),
    mpatches.Patch(color=AG_TOOL, label="Agentic loop · tool-trained"),
    mpatches.Patch(color=AG_CTRL, label="Agentic loop · control group"),
]
ax.legend(handles=patches, loc="lower right", fontsize=8.5,
          framealpha=0.25, edgecolor="#30363d",
          facecolor="#161b22", labelcolor="#c9d1d9")

# Footnote
fig.text(0.99, 0.005, "workunit.app · github.com/3615-computer/workunit-benchmarks",
         ha="right", fontsize=7.5, color="#484f58", style="italic")

plt.tight_layout()
output = "graph1_ss_vs_ag_overall.png"
plt.savefig(output, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {output}")

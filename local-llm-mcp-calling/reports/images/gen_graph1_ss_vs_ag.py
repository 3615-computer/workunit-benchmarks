"""
Graph 1: Single-shot Overall vs Agentic Overall — side-by-side horizontal bars.
Hero image for reddit_post_LocalLLaMA.md

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
ss_vals    = [round(models_data[m]["ss_overall"]) for m in sorted_models]
ag_vals    = [round(models_data[m]["ag_overall"]) for m in sorted_models]
tool_flags = [models_data[m]["tool_trained"] for m in sorted_models]

n = len(sorted_models)
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

# ── Dynamic inline annotations for outliers ───────────────────────────────────
annotations = []
for i, m in enumerate(sorted_models):
    ss = ss_vals[i]
    ag = ag_vals[i]
    tt = tool_flags[i]
    diff = abs(ss - ag)

    # Models with 0% SS but >70% AG
    if ss == 0 and ag > 70:
        suffix = " (not tool-trained)" if not tt else ""
        annotations.append((i, f"\u2190 0% SS but {ag}% AG{suffix}", "#a8f0a8"))
    # Models with >50% SS but 0% AG (paradox)
    elif ag == 0 and ss > 50:
        annotations.append((i, f"\u2190 {ss}% SS but 0% AG (paradox)", "#ff6b6b"))
    # Any model where |SS - AG| > 30
    elif diff > 30:
        if ag > ss:
            annotations.append((i, f"\u2190 {ss}% SS vs {ag}% AG (\u0394{diff})", "#ffa657"))
        else:
            annotations.append((i, f"\u2190 {ss}% SS vs {ag}% AG (\u0394{diff})", "#ff6b6b"))

for ypos, txt, col in annotations:
    t = ax.text(102, ypos, txt, va="center", ha="left", fontsize=7.5, color=col)
    t.set_clip_on(False)

ax.set_yticks(y)
ax.set_yticklabels(labels, fontsize=9, color="#c9d1d9")
ax.set_xlabel("Overall Score (%)", fontsize=10, color="#8b949e", labelpad=8)
ax.set_title(f"Local LLM MCP Tool Calling \u2014 Single-shot vs Agentic Overall Score\n"
             f"{n} models \u00b7 28 tasks \u00b7 3 difficulty levels",
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
    mpatches.Patch(facecolor=SS_TOOL, label="Single-shot \u00b7 tool-trained",
                   edgecolor="#c9d1d9", linewidth=0.6),
    mpatches.Patch(facecolor=SS_CTRL, label="Single-shot \u00b7 not tool-trained",
                   hatch="//", edgecolor="#c9d1d9", linewidth=0.6),
    mpatches.Patch(facecolor=AG_TOOL, label="Agentic loop \u00b7 tool-trained",
                   edgecolor="#c9d1d9", linewidth=0.6),
    mpatches.Patch(facecolor=AG_CTRL, label="Agentic loop \u00b7 not tool-trained",
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

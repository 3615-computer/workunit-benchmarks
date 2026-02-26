"""
Graph 3: Tool-trained vs not-tool-trained — grouped bar comparison.

Single panel showing average pass rate by group × level × methodology.
Answers: "Does tool-training metadata predict benchmark performance?"

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

# Split models by tool-trained flag
trained_models = [m for m in sorted_models if models_data[m]["tool_trained"]]
control_models = [m for m in sorted_models if not models_data[m]["tool_trained"]]

n_trained = len(trained_models)
n_control = len(control_models)

# IBM Design Library colorblind-safe palette
C_SS_TOOL = "#648FFF"   # blue
C_AG_TOOL = "#FE6100"   # orange
C_SS_CTRL = "#785EF0"   # purple
C_AG_CTRL = "#FFB000"   # yellow

# ── Collect per-level pass rates for each group ──────────────────────────────
trained_ss = {0: [], 1: [], 2: []}
trained_ag = {0: [], 1: [], 2: []}
ctrl_ss    = {0: [], 1: [], 2: []}
ctrl_ag    = {0: [], 1: [], 2: []}

for m in sorted_models:
    md = models_data[m]
    is_trained = md["tool_trained"]
    for level in (0, 1, 2):
        ss_pr = md["ss"].get(level, {}).get("pass_rate", 0.0) * 100
        ag_pr = md["ag"].get(level, {}).get("pass_rate", 0.0) * 100
        if is_trained:
            trained_ss[level].append(ss_pr)
            trained_ag[level].append(ag_pr)
        else:
            ctrl_ss[level].append(ss_pr)
            ctrl_ag[level].append(ag_pr)

def avg(lst):
    return sum(lst) / len(lst) if lst else 0.0

# ── Build figure ──────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 7))
fig.patch.set_facecolor("#0d1117")
ax.set_facecolor("#161b22")
plt.subplots_adjust(bottom=0.18, left=0.10, right=0.95, top=0.88)

xpos = np.arange(3)
bw = 0.18

ss_trained_means = [avg(trained_ss[l]) for l in (0, 1, 2)]
ag_trained_means = [avg(trained_ag[l]) for l in (0, 1, 2)]
ss_ctrl_means    = [avg(ctrl_ss[l])    for l in (0, 1, 2)]
ag_ctrl_means    = [avg(ctrl_ag[l])    for l in (0, 1, 2)]

b1 = ax.bar(xpos - 1.5*bw, ss_trained_means, bw, color=C_SS_TOOL, alpha=0.90,
            edgecolor="#c9d1d9", linewidth=0.4)
b2 = ax.bar(xpos - 0.5*bw, ag_trained_means, bw, color=C_AG_TOOL, alpha=0.95,
            edgecolor="#c9d1d9", linewidth=0.4)
b3 = ax.bar(xpos + 0.5*bw, ss_ctrl_means,    bw, color=C_SS_CTRL, alpha=0.90,
            hatch="//", edgecolor="#c9d1d9", linewidth=0.4)
b4 = ax.bar(xpos + 1.5*bw, ag_ctrl_means,    bw, color=C_AG_CTRL, alpha=0.95,
            hatch="//", edgecolor="#c9d1d9", linewidth=0.4)

for bars in [b1, b2, b3, b4]:
    for bar in bars:
        h = bar.get_height()
        if h > 1:
            ax.text(bar.get_x() + bar.get_width()/2, h + 1.2,
                    f"{h:.0f}%", ha="center", va="bottom", fontsize=8.5, color="#c9d1d9")

ax.set_xticks(xpos)
ax.set_xticklabels(["L0\nExplicit", "L1\nNatural language", "L2\nReasoning"],
                   fontsize=10.5, color="#c9d1d9")
ax.set_ylabel("Average Pass Rate (%)", fontsize=10, color="#8b949e", labelpad=8)
ax.set_title(f"Tool-trained vs Not Tool-trained — Avg Pass Rate by Level & Methodology\n"
             f"tool-trained n={n_trained}, not tool-trained n={n_control}",
             fontsize=12, color="#e6edf3", fontweight="bold", pad=14)
ax.set_ylim(0, 115)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}%"))
ax.tick_params(colors="#8b949e", labelsize=9)
for spine in ax.spines.values():
    spine.set_edgecolor("#30363d")
ax.yaxis.grid(True, color="#21262d", linewidth=0.6, linestyle="--")
ax.set_axisbelow(True)

# Legend below chart
patches = [
    mpatches.Patch(facecolor=C_SS_TOOL, label="Single-shot \u00b7 tool-trained",
                   edgecolor="#c9d1d9", linewidth=0.6),
    mpatches.Patch(facecolor=C_AG_TOOL, label="Agentic loop \u00b7 tool-trained",
                   edgecolor="#c9d1d9", linewidth=0.6),
    mpatches.Patch(facecolor=C_SS_CTRL, label="Single-shot \u00b7 not tool-trained",
                   hatch="//", edgecolor="#c9d1d9", linewidth=0.6),
    mpatches.Patch(facecolor=C_AG_CTRL, label="Agentic loop \u00b7 not tool-trained",
                   hatch="//", edgecolor="#c9d1d9", linewidth=0.6),
]
fig.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.52, 0.01),
           ncol=4, fontsize=8.5, framealpha=0.25, edgecolor="#30363d",
           facecolor="#161b22", labelcolor="#c9d1d9")

fig.text(0.95, 0.005, "github.com/3615-computer/workunit-benchmarks",
         ha="right", fontsize=7.5, color="#484f58", style="italic")

output = "graph3_trained_vs_control.png"
plt.savefig(output, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {output}")

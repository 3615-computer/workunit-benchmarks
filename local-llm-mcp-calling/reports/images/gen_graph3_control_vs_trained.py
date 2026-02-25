"""
Graph 3: Tool-trained vs not-tool-trained — SS and Agentic scores side by side.

Two panels:
  Panel A: Scatter plot of SS Overall vs AG Overall
  Panel B: Grouped vertical bars showing avg pass rate by group x level x methodology

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

# Build individual model tuples: (ss_overall, ag_overall, tool_trained, short_label)
individual = []
for m in sorted_models:
    md = models_data[m]
    individual.append((
        round(md["ss_overall"]),
        round(md["ag_overall"]),
        md["tool_trained"],
        md["short_label"],
    ))

trained = [(d[0], d[1], d[3]) for d in individual if d[2]]
control = [(d[0], d[1], d[3]) for d in individual if not d[2]]

# IBM Design Library colorblind-safe palette (consistent with Graph 1)
C_SS_TOOL = "#648FFF"   # blue
C_AG_TOOL = "#FE6100"   # orange
C_SS_CTRL = "#785EF0"   # purple
C_AG_CTRL = "#FFB000"   # yellow

fig, axes = plt.subplots(1, 2, figsize=(15, 7))
fig.patch.set_facecolor("#0d1117")
for ax in axes:
    ax.set_facecolor("#161b22")
plt.subplots_adjust(bottom=0.16, wspace=0.32)

# ── Panel A: Scatter SS Overall vs AG Overall ────────────────────────────────
ax = axes[0]

tx = [d[0] for d in trained]
ty = [d[1] for d in trained]
ax.scatter(tx, ty, s=90, color=C_AG_TOOL, zorder=5, alpha=0.9,
           label=f"Tool-trained ({len(trained)})")

# Dynamic label offset heuristic to reduce overlap:
# Sort points by position, alternate left/right offsets, shift vertically
# when points are close together.
def _compute_offsets(points):
    """
    Compute label offsets for a list of (x, y, label) tuples.

    Uses a simple heuristic: alternate left/right based on index,
    and shift vertically when two points are close together.
    """
    offsets = {}
    # Sort by y descending, then x ascending for consistent placement
    indexed = sorted(enumerate(points), key=lambda p: (-p[1][1], p[1][0]))

    prev_x, prev_y = None, None
    for rank, (idx, (x, y, label)) in enumerate(indexed):
        # Base: alternate left/right
        if rank % 2 == 0:
            dx, dy = 5, 3
        else:
            dx, dy = -50, -4

        # If close to previous point, add extra vertical shift
        if prev_x is not None:
            dist = ((x - prev_x) ** 2 + (y - prev_y) ** 2) ** 0.5
            if dist < 8:
                # Points are very close, push further apart vertically
                dy += 8 if rank % 2 == 0 else -8

        offsets[idx] = (dx, dy)
        prev_x, prev_y = x, y

    return offsets

trained_offsets = _compute_offsets(trained)
for idx, (ss, ag, label) in enumerate(trained):
    offset = trained_offsets.get(idx, (3, 3))
    ax.annotate(label, (ss, ag), fontsize=5.5, color="#c9d1d9",
                xytext=offset, textcoords="offset points", zorder=6)

cx = [d[0] for d in control]
cy = [d[1] for d in control]
ax.scatter(cx, cy, s=90, color=C_SS_CTRL, marker="D", zorder=5, alpha=0.9,
           label=f"Not tool-trained ({len(control)})")

control_offsets = _compute_offsets(control)
for idx, (ss, ag, label) in enumerate(control):
    offset = control_offsets.get(idx, (3, 3))
    ax.annotate(label, (ss, ag), fontsize=5.5, color="#c9d1d9",
                xytext=offset, textcoords="offset points", zorder=6)

ax.plot([0, 100], [0, 100], color="#30363d", linewidth=1, linestyle="--", zorder=1)
ax.text(72, 68, "SS = AG", fontsize=7.5, color="#484f58", rotation=45, ha="center")
ax.fill_between([0, 100], [0, 100], [100, 100], alpha=0.04, color="#3fb950")
ax.text(15, 90, "Agentic loop\nsignificantly better", fontsize=7.5, color="#3fb950",
        alpha=0.7, ha="center")

ax.set_xlabel("Single-shot Overall (%)", fontsize=9, color="#8b949e", labelpad=6)
ax.set_ylabel("Agentic Loop Overall (%)", fontsize=9, color="#8b949e", labelpad=6)
ax.set_title("Single-shot vs Agentic Overall\n(each dot = one model)", fontsize=10,
             color="#e6edf3", fontweight="bold", pad=10)
ax.set_xlim(-5, 105)
ax.set_ylim(-5, 105)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}%"))
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}%"))
ax.tick_params(colors="#8b949e", labelsize=8)
for spine in ax.spines.values():
    spine.set_edgecolor("#30363d")
ax.xaxis.grid(True, color="#21262d", linewidth=0.6, linestyle="--")
ax.yaxis.grid(True, color="#21262d", linewidth=0.6, linestyle="--")
ax.set_axisbelow(True)
ax.legend(fontsize=8, framealpha=0.25, edgecolor="#30363d",
          facecolor="#161b22", labelcolor="#c9d1d9", loc="lower right")

# ── Panel B: Grouped bars — avg by group x methodology x level ───────────────
ax = axes[1]

# Collect per-level pass rates for each group
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

n_trained = len(trained)
n_control = len(control)

xpos = np.arange(3)
bw = 0.18

ss_trained_means = [avg(trained_ss[l]) for l in (0, 1, 2)]
ag_trained_means = [avg(trained_ag[l]) for l in (0, 1, 2)]
ss_ctrl_means    = [avg(ctrl_ss[l])    for l in (0, 1, 2)]
ag_ctrl_means    = [avg(ctrl_ag[l])    for l in (0, 1, 2)]

b1 = ax.bar(xpos - 1.5*bw, ss_trained_means, bw, color=C_SS_TOOL, alpha=0.90,
            label="SS \u00b7 tool-trained", edgecolor="#c9d1d9", linewidth=0.4)
b2 = ax.bar(xpos - 0.5*bw, ag_trained_means, bw, color=C_AG_TOOL, alpha=0.95,
            label="AG \u00b7 tool-trained", edgecolor="#c9d1d9", linewidth=0.4)
b3 = ax.bar(xpos + 0.5*bw, ss_ctrl_means,    bw, color=C_SS_CTRL, alpha=0.90,
            label="SS \u00b7 not tool-trained", hatch="//", edgecolor="#c9d1d9", linewidth=0.4)
b4 = ax.bar(xpos + 1.5*bw, ag_ctrl_means,    bw, color=C_AG_CTRL, alpha=0.95,
            label="AG \u00b7 not tool-trained", hatch="//", edgecolor="#c9d1d9", linewidth=0.4)

for bars in [b1, b2, b3, b4]:
    for bar in bars:
        h = bar.get_height()
        if h > 1:
            ax.text(bar.get_x() + bar.get_width()/2, h + 1.2,
                    f"{h:.0f}%", ha="center", va="bottom", fontsize=7.5, color="#c9d1d9")

ax.set_xticks(xpos)
ax.set_xticklabels(["L0\nExplicit", "L1\nNatural\nlanguage", "L2\nReasoning"],
                   fontsize=9.5, color="#c9d1d9")
ax.set_ylabel("Average Pass Rate (%)", fontsize=9, color="#8b949e", labelpad=6)
ax.set_title(f"Avg Pass Rate by Group, Level & Method\n"
             f"(tool-trained n={n_trained}, not tool-trained n={n_control})",
             fontsize=10, color="#e6edf3", fontweight="bold", pad=10)
ax.set_ylim(0, 110)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}%"))
ax.tick_params(colors="#8b949e", labelsize=9)
for spine in ax.spines.values():
    spine.set_edgecolor("#30363d")
ax.yaxis.grid(True, color="#21262d", linewidth=0.6, linestyle="--")
ax.set_axisbelow(True)

# Legend below both panels
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
fig.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.5, 0.01),
           ncol=4, fontsize=8.5, framealpha=0.25, edgecolor="#30363d",
           facecolor="#161b22", labelcolor="#c9d1d9")

fig.suptitle("Tool-trained vs Not Tool-trained \u2014 Single-shot and Agentic Performance",
             fontsize=12, color="#e6edf3", fontweight="bold", y=1.01)

fig.text(0.99, -0.02, "github.com/3615-computer/workunit-benchmarks",
         ha="right", fontsize=7.5, color="#484f58", style="italic")

output = "graph3_trained_vs_control.png"
plt.savefig(output, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {output}")

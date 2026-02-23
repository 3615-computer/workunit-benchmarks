"""
Graph 3: Tool-trained vs control group — SS and Agentic scores side by side.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Individual model data
# (ss_overall, ag_overall, tool_trained, short_label)
individual = [
    (60,  89, True,  "granite\n7B"),
    (60,  88, True,  "qwen3-coder\n30B"),
    (63,  85, True,  "magistral\n24B"),
    (60,  85, True,  "qwen3-4b\n4B"),
    (57,  85, True,  "gpt-oss\n20B"),
    (63,  84, True,  "ministral-14b\n14B"),
    ( 0,  83, False, "ernie-4.5\n21B"),
    (82,  81, True,  "ministral-3b\n3B"),
    ( 0,  78, False, "gemma-3\n12B"),
    (60,  77, True,  "rnj-1\n8.3B"),
    (50,  71, True,  "nemotron\n30B"),
    (54,  68, True,  "glm-4.6v\n9.4B"),
    (42,  64, False, "phi-4-rplus\n15B"),
    (35,  61, True,  "glm-4.7\n30B"),
    (35,  58, False, "qwen2.5-coder\n32B"),
    ( 3,   6, False, "deepseek-r1\n8B"),
    (60,   0, True,  "seed-oss\n36B"),
]

trained = [(d[0], d[1], d[3]) for d in individual if d[2]]
control = [(d[0], d[1], d[3]) for d in individual if not d[2]]

# Four clearly distinct colors for the right panel bars
# SS · tool-trained  → steel blue
# AG · tool-trained  → orange
# SS · control       → magenta / hot pink
# AG · control       → lime green
C_SS_TOOL = "#4a9eff"   # steel blue
C_AG_TOOL = "#f97316"   # orange
C_SS_CTRL = "#e040fb"   # magenta
C_AG_CTRL = "#69e06e"   # lime green

fig, axes = plt.subplots(1, 2, figsize=(15, 7))
fig.patch.set_facecolor("#0d1117")
for ax in axes:
    ax.set_facecolor("#161b22")
plt.subplots_adjust(bottom=0.16, wspace=0.32)

# ── Panel A: Scatter SS Overall vs AG Overall ────────────────────────────────
ax = axes[0]

tx = [d[0] for d in trained]
ty = [d[1] for d in trained]
ax.scatter(tx, ty, s=90, color=C_AG_TOOL, zorder=5, alpha=0.9, label="Tool-trained (12)")
for (ss, ag, label) in trained:
    ax.annotate(label, (ss, ag), fontsize=5.5, color="#c9d1d9",
                xytext=(3, 3), textcoords="offset points", zorder=6)

cx = [d[0] for d in control]
cy = [d[1] for d in control]
ax.scatter(cx, cy, s=90, color=C_SS_CTRL, marker="D", zorder=5, alpha=0.9, label="Control group (5)")
for (ss, ag, label) in control:
    ax.annotate(label, (ss, ag), fontsize=5.5, color="#c9d1d9",
                xytext=(3, 3), textcoords="offset points", zorder=6)

ax.plot([0, 100], [0, 100], color="#30363d", linewidth=1, linestyle="--", zorder=1)
ax.text(72, 68, "SS = AG", fontsize=7.5, color="#484f58", rotation=45, ha="center")
ax.fill_between([0, 100], [0, 100], [100, 100], alpha=0.04, color="#3fb950")
ax.text(15, 90, "Agentic loop\nsignificantly better", fontsize=7.5, color="#3fb950", alpha=0.7, ha="center")

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
          facecolor="#161b22", labelcolor="#c9d1d9",
          loc="lower right")

# ── Panel B: Grouped bars — avg by group × methodology × level ───────────────
ax = axes[1]

# Per-level agentic pass rates, tool-trained (12 models)
trained_ag_L0 = [100,100,100,100,100,100, 91,100,100, 91, 55,  0]
trained_ag_L1 = [100, 90,100, 80, 80, 90, 90, 80, 60, 60, 50,  0]
trained_ag_L2 = [ 57, 57, 43, 57, 43, 29, 29,  0, 14, 14, 71,  0]
# Control (5): ernie, gemma, phi4, qwen2.5, deepseek
ctrl_ag_L0    = [100, 91, 46, 91, 18]
ctrl_ag_L1    = [100, 80, 80, 50,  0]
ctrl_ag_L2    = [ 29, 29, 43, 14,  0]

# Single-shot
trained_ss_L0 = [100,100,100,100,100,100,100,100, 91, 82, 64,100]
trained_ss_L1 = [ 80, 80, 90, 80, 70, 90, 90, 80, 60, 80, 40, 80]
trained_ss_L2 = [  0,  0,  0,  0,  0,  0, 57,  0,  0,  0,  0,  0]

ctrl_ss_L0    = [  0,  0, 55, 64,  9]
ctrl_ss_L1    = [  0,  0, 70, 40,  0]
ctrl_ss_L2    = [  0,  0,  0,  0,  0]

def avg(lst): return sum(lst) / len(lst)

xpos = np.arange(3)
bw = 0.18

ss_trained_means = [avg(trained_ss_L0), avg(trained_ss_L1), avg(trained_ss_L2)]
ag_trained_means = [avg(trained_ag_L0), avg(trained_ag_L1), avg(trained_ag_L2)]
ss_ctrl_means    = [avg(ctrl_ss_L0),    avg(ctrl_ss_L1),    avg(ctrl_ss_L2)]
ag_ctrl_means    = [avg(ctrl_ag_L0),    avg(ctrl_ag_L1),    avg(ctrl_ag_L2)]

b1 = ax.bar(xpos - 1.5*bw, ss_trained_means, bw, color=C_SS_TOOL, alpha=0.90, label="SS · tool-trained")
b2 = ax.bar(xpos - 0.5*bw, ag_trained_means, bw, color=C_AG_TOOL, alpha=0.95, label="AG · tool-trained")
b3 = ax.bar(xpos + 0.5*bw, ss_ctrl_means,    bw, color=C_SS_CTRL, alpha=0.90, label="SS · control group")
b4 = ax.bar(xpos + 1.5*bw, ag_ctrl_means,    bw, color=C_AG_CTRL, alpha=0.95, label="AG · control group")

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
ax.set_title("Avg Pass Rate by Group, Level & Method\n(tool-trained n=12, control n=5)",
             fontsize=10, color="#e6edf3", fontweight="bold", pad=10)
ax.set_ylim(0, 120)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}%"))
ax.tick_params(colors="#8b949e", labelsize=9)
for spine in ax.spines.values():
    spine.set_edgecolor("#30363d")
ax.yaxis.grid(True, color="#21262d", linewidth=0.6, linestyle="--")
ax.set_axisbelow(True)

# Annotate L2 control AG bar
l2_ctrl_ag_h = ag_ctrl_means[2]
ax.annotate(f"Control group\ncompetitive at L2\nin agentic loop",
            xy=(xpos[2] + 1.5*bw, l2_ctrl_ag_h),
            xytext=(xpos[2] + 1.5*bw + 0.35, l2_ctrl_ag_h + 28),
            fontsize=7.5, color="#a8f0a8",
            arrowprops=dict(arrowstyle="->", color="#a8f0a8", lw=1),
            ha="left")

# Legend below both panels, spanning figure width
patches = [
    mpatches.Patch(color=C_SS_TOOL, label="Single-shot · tool-trained"),
    mpatches.Patch(color=C_AG_TOOL, label="Agentic loop · tool-trained"),
    mpatches.Patch(color=C_SS_CTRL, label="Single-shot · control group"),
    mpatches.Patch(color=C_AG_CTRL, label="Agentic loop · control group"),
]
fig.legend(handles=patches, loc="lower center", bbox_to_anchor=(0.5, 0.01),
           ncol=4, fontsize=8.5, framealpha=0.25, edgecolor="#30363d",
           facecolor="#161b22", labelcolor="#c9d1d9")

fig.suptitle("Tool-trained vs Control Group — Single-shot and Agentic Performance",
             fontsize=12, color="#e6edf3", fontweight="bold", y=1.01)

fig.text(0.99, -0.02, "workunit.app · github.com/3615-computer/workunit-benchmarks",
         ha="right", fontsize=7.5, color="#484f58", style="italic")

output = "graph3_trained_vs_control.png"
plt.savefig(output, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {output}")

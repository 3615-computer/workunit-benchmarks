"""
Graph 3: Tool-trained vs control group — SS and Agentic scores side by side.
Shows how the two groups compare across methodologies and levels.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Individual model data for scatter overlay
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

# --- Figure: two-panel side by side ---
fig, axes = plt.subplots(1, 2, figsize=(14, 7))
fig.patch.set_facecolor("#0d1117")
for ax in axes:
    ax.set_facecolor("#161b22")

# ---- Panel A: Scatter SS Overall vs AG Overall ----
ax = axes[0]

# Tool-trained scatter
tx = [d[0] for d in trained]
ty = [d[1] for d in trained]
ax.scatter(tx, ty, s=90, color="#f97316", zorder=5, alpha=0.9, label="Tool-trained (12 models)")
for (ss, ag, label) in trained:
    ax.annotate(label, (ss, ag), fontsize=6, color="#c9d1d9",
                xytext=(3, 3), textcoords="offset points", zorder=6)

# Control scatter
cx = [d[0] for d in control]
cy = [d[1] for d in control]
ax.scatter(cx, cy, s=90, color="#4a9eff", marker="D", zorder=5, alpha=0.9, label="Control group (5 models)")
for (ss, ag, label) in control:
    ax.annotate(label, (ss, ag), fontsize=6, color="#8b949e",
                xytext=(3, 3), textcoords="offset points", zorder=6)

# Diagonal y=x reference
ax.plot([0, 100], [0, 100], color="#30363d", linewidth=1, linestyle="--", zorder=1)
ax.text(72, 68, "SS = AG", fontsize=7.5, color="#484f58", rotation=45, ha="center")

ax.fill_between([0, 100], [0, 100], [100, 100], alpha=0.04, color="#3fb950")  # above diagonal = agentic wins
ax.text(15, 88, "Agentic loop\nsignificantly better", fontsize=7.5, color="#3fb950", alpha=0.7, ha="center")

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
          facecolor="#161b22", labelcolor="#c9d1d9")

# ---- Panel B: Grouped bars — avg by group, SS vs AG, per level ----
ax = axes[1]

# Per-level pass rates from raw data
# Tool-trained (12 models): L0, L1, L2 — agentic
trained_ag_L0 = [100,100,100,100,100,100,91,100,100,91,55,0]   # all 12 tool-trained AG L0
trained_ag_L1 = [100,90,100,80,80,90,90,80,60,60,50,0]
trained_ag_L2 = [57,57,43,57,43,29,29,0,14,14,71,0]
# Control (5): ernie, gemma, phi4, qwen2.5, deepseek
ctrl_ag_L0    = [100,91,46,91,18]
ctrl_ag_L1    = [100,80,80,50,0]
ctrl_ag_L2    = [29,29,43,14,0]

# Single-shot
trained_ss_L0 = [100,100,100,100,100,100,100,100,91,82,64,100]
trained_ss_L1 = [80,80,90,80,70,90,90,80,60,80,40,80]
trained_ss_L2 = [0,0,0,0,0,0,57,0,0,0,0,0]

ctrl_ss_L0    = [0,0,55,64,9]
ctrl_ss_L1    = [0,0,70,40,0]
ctrl_ss_L2    = [0,0,0,0,0]

def avg(lst): return sum(lst) / len(lst)

groups = ["L0\nExplicit", "L1\nNatural\nlanguage", "L2\nReasoning"]
xpos = np.arange(3)
bw = 0.2

ss_trained_means = [avg(trained_ss_L0), avg(trained_ss_L1), avg(trained_ss_L2)]
ag_trained_means = [avg(trained_ag_L0), avg(trained_ag_L1), avg(trained_ag_L2)]
ss_ctrl_means    = [avg(ctrl_ss_L0),    avg(ctrl_ss_L1),    avg(ctrl_ss_L2)]
ag_ctrl_means    = [avg(ctrl_ag_L0),    avg(ctrl_ag_L1),    avg(ctrl_ag_L2)]

b1 = ax.bar(xpos - 1.5*bw, ss_trained_means, bw, color="#4a9eff", alpha=0.85, label="SS · tool-trained")
b2 = ax.bar(xpos - 0.5*bw, ag_trained_means, bw, color="#f97316", alpha=0.95, label="AG · tool-trained")
b3 = ax.bar(xpos + 0.5*bw, ss_ctrl_means,    bw, color="#7db8ff", alpha=0.85, label="SS · control group")
b4 = ax.bar(xpos + 1.5*bw, ag_ctrl_means,    bw, color="#fbbf7c", alpha=0.95, label="AG · control group")

for bars in [b1, b2, b3, b4]:
    for bar in bars:
        h = bar.get_height()
        if h > 1:
            ax.text(bar.get_x() + bar.get_width()/2, h + 1,
                    f"{h:.0f}%", ha="center", va="bottom", fontsize=7.5, color="#c9d1d9")

ax.set_xticks(xpos)
ax.set_xticklabels(groups, fontsize=9.5, color="#c9d1d9")
ax.set_ylabel("Average Pass Rate (%)", fontsize=9, color="#8b949e", labelpad=6)
ax.set_title("Avg Pass Rate by Group, Level & Methodology\n(tool-trained n=12, control n=5)",
             fontsize=10, color="#e6edf3", fontweight="bold", pad=10)
ax.set_ylim(0, 118)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x)}%"))
ax.tick_params(colors="#8b949e", labelsize=9)
for spine in ax.spines.values():
    spine.set_edgecolor("#30363d")
ax.yaxis.grid(True, color="#21262d", linewidth=0.6, linestyle="--")
ax.set_axisbelow(True)
ax.legend(fontsize=7.5, framealpha=0.25, edgecolor="#30363d",
          facecolor="#161b22", labelcolor="#c9d1d9", ncol=2)

# Annotate L2 control AG bar — the surprising result
l2_ctrl_ag_h = ag_ctrl_means[2]
ax.annotate(f"Control group\nfinally competitive\nat L2 in agentic",
            xy=(xpos[2] + 1.5*bw, l2_ctrl_ag_h),
            xytext=(xpos[2] + 2.0*bw + 0.05, l2_ctrl_ag_h + 20),
            fontsize=7, color="#a8f0a8",
            arrowprops=dict(arrowstyle="->", color="#a8f0a8", lw=1),
            ha="left")

fig.suptitle("Tool-trained vs Control Group — Single-shot and Agentic Performance",
             fontsize=12, color="#e6edf3", fontweight="bold", y=1.01)

fig.text(0.99, -0.015, "workunit.app · github.com/3615-computer/workunit-benchmarks",
         ha="right", fontsize=7.5, color="#484f58", style="italic")

plt.tight_layout()
output = "graph3_trained_vs_control.png"
plt.savefig(output, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved: {output}")

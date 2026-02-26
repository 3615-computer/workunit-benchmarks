#!/usr/bin/env python3
"""
Verify all published statistics from benchmark results.

Computes every statistic that appears in the three reports (research_paper.md,
reddit_post_LocalLLaMA.md, reddit_post_AIToolsPerformance.md) from raw data,
writes published_stats.json as the authoritative reference, and prints a
human-readable summary.

Usage:
    python verify_stats.py [--run TIMESTAMP]
"""

import json
import math
import sys
from pathlib import Path

# Add images/ to path so we can import _load_results
sys.path.insert(0, str(Path(__file__).parent / "images"))
from _load_results import load_results, parse_run_arg


# --- Size tier definitions ---
# Maps model keys to tiers based on models.txt groupings
TIER_DEFINITIONS = {
    "Tiny (3-4B)": [],
    "Small (7-9.4B)": [],
    "Medium (12-15B)": [],
    "Large (20-24B)": [],
    "XL (30-36B)": [],
    "XXL (80B)": [],
}

TIER_PARAM_RANGES = {
    "Tiny (3-4B)": (0, 4.9),
    "Small (7-9.4B)": (5, 10),
    "Medium (12-15B)": (10.1, 15.9),
    "Large (20-24B)": (16, 24.9),
    "XL (30-36B)": (25, 39),
    "XXL (80B)": (40, 999),
}


def parse_params(params_string: str) -> float:
    """Parse params_string to numeric value (in billions).

    Examples:
        '35B-A3B' -> 35.0
        '64x1.3B' -> 24.0 (LFM2 has 24B total params; '64x1.3B' describes expert topology)
        '30B-A3B' -> 30.0
        '80B' -> 80.0
        '8.3B' -> 8.3

    Note: LM Studio's params_string for lfm2-24b-a2b is '64x1.3B' which describes
    the MoE expert structure (64 experts × 1.3B each), but the model's actual total
    parameter count is 24B per Liquid AI's documentation. We use the model key's
    stated 24B as the authoritative total, not the arithmetic product 64*1.3=83.2B.
    """
    s = params_string.upper().strip()
    # Handle MoE expert topology notation like '64x1.3B'.
    # LM Studio reports expert structure, not total params. For lfm2-24b-a2b,
    # '64x1.3B' means 64 experts of 1.3B each, but the model's total parameter
    # count is 24B per Liquid AI's official documentation (shared layers, routing
    # weights, etc. mean total != experts × per-expert). We use a lookup for
    # models where the params_string describes topology rather than total params.
    MOE_TOTAL_PARAMS = {
        "64X1.3B": 24.0,  # liquid/lfm2-24b-a2b: 24B total, 2B active
    }
    if "X" in s and "B" in s:
        if s in MOE_TOTAL_PARAMS:
            return MOE_TOTAL_PARAMS[s]
        # Fallback: multiply for unknown MoE notations
        parts = s.split("X")
        try:
            count = float(parts[0])
            per = float(parts[1].replace("B", "").split("-")[0])
            return count * per
        except (ValueError, IndexError):
            pass
    # Handle 'NB-AMB' (MoE with active params) like '35B-A3B' -> 35
    if "-A" in s:
        main = s.split("-A")[0]
        return float(main.replace("B", ""))
    # Simple 'NB' like '80B', '8.3B'
    return float(s.replace("B", ""))


def assign_tier(model_key: str, params_string: str) -> str:
    """Assign a model to a size tier based on models.txt groupings."""
    # Hardcoded from models.txt for accuracy
    tier_map = {
        "mistralai/ministral-3-3b": "Tiny (3-4B)",
        "qwen/qwen3-4b-thinking-2507": "Tiny (3-4B)",
        "ibm/granite-4-h-tiny": "Small (7-9.4B)",
        "deepseek/deepseek-r1-0528-qwen3-8b": "Small (7-9.4B)",
        "essentialai/rnj-1": "Small (7-9.4B)",
        "zai-org/glm-4.6v-flash": "Small (7-9.4B)",
        "google/gemma-3-12b": "Medium (12-15B)",
        "microsoft/phi-4-reasoning-plus": "Medium (12-15B)",
        "mistralai/ministral-3-14b-reasoning": "Medium (12-15B)",
        "openai/gpt-oss-20b": "Large (20-24B)",
        "baidu/ernie-4.5-21b-a3b": "Large (20-24B)",
        "mistralai/magistral-small-2509": "Large (20-24B)",
        "mistralai/devstral-small-2-2512": "Large (20-24B)",
        "qwen/qwen2.5-coder-32b": "XL (30-36B)",
        "qwen/qwen3.5-35b-a3b": "XL (30-36B)",
        "zai-org/glm-4.7-flash": "XL (30-36B)",
        "qwen/qwen3-coder-30b": "XL (30-36B)",
        "nvidia/nemotron-3-nano": "XL (30-36B)",
        "bytedance/seed-oss-36b": "XL (30-36B)",
        "liquid/lfm2-24b-a2b": "Large (20-24B)",
        "qwen/qwen3-coder-next": "XXL (80B)",
    }
    return tier_map.get(model_key, "Unknown")


def r1(x: float) -> float:
    """Round to 1 decimal place."""
    return round(x, 1)


def std_dev(values: list[float]) -> float:
    """Sample standard deviation."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    return math.sqrt(variance)


def load_lmstudio_metadata() -> dict:
    """Load LM Studio API metadata for model details."""
    meta_path = Path(__file__).parent / "lmstudio_models_api.json"
    with open(meta_path) as f:
        data = json.load(f)
    # Index by key
    return {m["key"]: m for m in data["models"]}


def compute_all_stats(data: dict, meta: dict) -> dict:
    """Compute every published statistic from raw data."""
    models = data["models"]
    sorted_models = data["sorted_models"]

    stats = {}

    # =========================================================================
    # §3.1 / §3.2: Per-model scores and rankings
    # =========================================================================
    ag_rankings = []
    ss_rankings = []

    for model_key in sorted_models:
        m = models[model_key]
        short = model_key.split("/")[-1] if "/" in model_key else model_key

        ag_l0 = r1(m["ag"].get(0, {}).get("avg_score", 0) * 100)
        ag_l1 = r1(m["ag"].get(1, {}).get("avg_score", 0) * 100)
        ag_l2 = r1(m["ag"].get(2, {}).get("avg_score", 0) * 100)
        ag_overall = r1(m["ag_overall"])

        ss_l0 = r1(m["ss"].get(0, {}).get("avg_score", 0) * 100)
        ss_l1 = r1(m["ss"].get(1, {}).get("avg_score", 0) * 100)
        ss_l2 = r1(m["ss"].get(2, {}).get("avg_score", 0) * 100)
        ss_overall = r1(m["ss_overall"])

        tool_trained = m["tool_trained"]

        # Get metadata
        model_meta = meta.get(model_key, {})
        params_string = model_meta.get("params_string", "")
        size_bytes = model_meta.get("size_bytes", 0)
        disk_gb = r1(size_bytes / (1024 ** 3))

        ag_rankings.append({
            "model": model_key,
            "short_name": short,
            "params_string": params_string,
            "disk_gb": disk_gb,
            "tool_trained": tool_trained,
            "ag_l0": ag_l0,
            "ag_l1": ag_l1,
            "ag_l2": ag_l2,
            "ag_overall": ag_overall,
            "ss_l0": ss_l0,
            "ss_l1": ss_l1,
            "ss_l2": ss_l2,
            "ss_overall": ss_overall,
        })

    # Sort by ag_overall descending for rankings
    ag_rankings.sort(key=lambda x: x["ag_overall"], reverse=True)

    # Assign ranks with ties
    rank = 1
    for i, entry in enumerate(ag_rankings):
        if i > 0 and ag_rankings[i - 1]["ag_overall"] != entry["ag_overall"]:
            rank = i + 1
        entry["ag_rank"] = rank

    # Sort by ss_overall for SS rankings
    ss_sorted = sorted(ag_rankings, key=lambda x: x["ss_overall"], reverse=True)
    rank = 1
    for i, entry in enumerate(ss_sorted):
        if i > 0 and ss_sorted[i - 1]["ss_overall"] != entry["ss_overall"]:
            rank = i + 1
        entry["ss_rank"] = rank

    stats["model_rankings"] = ag_rankings

    # =========================================================================
    # §3.3: SS vs AG comparison - level means and lifts
    # =========================================================================
    all_ag_l0 = [e["ag_l0"] for e in ag_rankings]
    all_ag_l1 = [e["ag_l1"] for e in ag_rankings]
    all_ag_l2 = [e["ag_l2"] for e in ag_rankings]
    all_ss_l0 = [e["ss_l0"] for e in ag_rankings]
    all_ss_l1 = [e["ss_l1"] for e in ag_rankings]
    all_ss_l2 = [e["ss_l2"] for e in ag_rankings]
    all_ag_overall = [e["ag_overall"] for e in ag_rankings]
    all_ss_overall = [e["ss_overall"] for e in ag_rankings]

    # Pass rates
    all_ag_l0_pr = [models[e["model"]]["ag"].get(0, {}).get("pass_rate", 0) * 100 for e in ag_rankings]
    all_ag_l1_pr = [models[e["model"]]["ag"].get(1, {}).get("pass_rate", 0) * 100 for e in ag_rankings]
    all_ag_l2_pr = [models[e["model"]]["ag"].get(2, {}).get("pass_rate", 0) * 100 for e in ag_rankings]
    all_ss_l0_pr = [models[e["model"]]["ss"].get(0, {}).get("pass_rate", 0) * 100 for e in ag_rankings]
    all_ss_l1_pr = [models[e["model"]]["ss"].get(1, {}).get("pass_rate", 0) * 100 for e in ag_rankings]
    all_ss_l2_pr = [models[e["model"]]["ss"].get(2, {}).get("pass_rate", 0) * 100 for e in ag_rankings]

    level_comparison = {
        "L0": {
            "ss_score_mean": r1(sum(all_ss_l0) / len(all_ss_l0)),
            "ag_score_mean": r1(sum(all_ag_l0) / len(all_ag_l0)),
            "lift": r1(sum(all_ag_l0) / len(all_ag_l0) - sum(all_ss_l0) / len(all_ss_l0)),
            "ss_pass_rate_mean": r1(sum(all_ss_l0_pr) / len(all_ss_l0_pr)),
            "ag_pass_rate_mean": r1(sum(all_ag_l0_pr) / len(all_ag_l0_pr)),
        },
        "L1": {
            "ss_score_mean": r1(sum(all_ss_l1) / len(all_ss_l1)),
            "ag_score_mean": r1(sum(all_ag_l1) / len(all_ag_l1)),
            "lift": r1(sum(all_ag_l1) / len(all_ag_l1) - sum(all_ss_l1) / len(all_ss_l1)),
            "ss_pass_rate_mean": r1(sum(all_ss_l1_pr) / len(all_ss_l1_pr)),
            "ag_pass_rate_mean": r1(sum(all_ag_l1_pr) / len(all_ag_l1_pr)),
        },
        "L2": {
            "ss_score_mean": r1(sum(all_ss_l2) / len(all_ss_l2)),
            "ag_score_mean": r1(sum(all_ag_l2) / len(all_ag_l2)),
            "lift": r1(sum(all_ag_l2) / len(all_ag_l2) - sum(all_ss_l2) / len(all_ss_l2)),
            "ss_pass_rate_mean": r1(sum(all_ss_l2_pr) / len(all_ss_l2_pr)),
            "ag_pass_rate_mean": r1(sum(all_ag_l2_pr) / len(all_ag_l2_pr)),
        },
    }
    stats["level_comparison"] = level_comparison

    # Overall lift stats
    lifts = [e["ag_overall"] - e["ss_overall"] for e in ag_rankings]
    lifts_sorted = sorted(lifts)
    n = len(lifts)
    median_lift = lifts_sorted[n // 2] if n % 2 == 1 else (lifts_sorted[n // 2 - 1] + lifts_sorted[n // 2]) / 2

    stats["overall_lift"] = {
        "mean": r1(sum(lifts) / len(lifts)),
        "median": r1(median_lift),
    }

    # Per-model lift table (sorted by magnitude descending)
    per_model_lift = []
    for e in ag_rankings:
        lift = r1(e["ag_overall"] - e["ss_overall"])
        per_model_lift.append({
            "model": e["model"],
            "short_name": e["short_name"],
            "ss_overall": e["ss_overall"],
            "ag_overall": e["ag_overall"],
            "lift": lift,
        })
    per_model_lift.sort(key=lambda x: x["lift"], reverse=True)
    stats["per_model_lift"] = per_model_lift

    # =========================================================================
    # §3.4: Per-level analysis
    # =========================================================================
    ag_l0_100_count = sum(1 for x in all_ag_l0 if x == 100.0)
    ag_l1_100_count = sum(1 for x in all_ag_l1 if x == 100.0)

    ag_l1_sorted = sorted(all_ag_l1)
    ag_l2_sorted = sorted(all_ag_l2)
    ag_l1_median = ag_l1_sorted[n // 2] if n % 2 == 1 else (ag_l1_sorted[n // 2 - 1] + ag_l1_sorted[n // 2]) / 2
    ag_l2_median = ag_l2_sorted[n // 2] if n % 2 == 1 else (ag_l2_sorted[n // 2 - 1] + ag_l2_sorted[n // 2]) / 2

    ag_l2_range = r1(max(all_ag_l2) - min(all_ag_l2))
    ag_l2_above_85 = sum(1 for x in all_ag_l2 if x > 85.0)

    # L2 SS pass rate
    l2_ss_pass_rate_mean = r1(sum(all_ss_l2_pr) / len(all_ss_l2_pr))

    # Which models pass any L2 in single-shot?
    l2_ss_passers = []
    for e in ag_rankings:
        m = models[e["model"]]
        ss_l2_pr = m["ss"].get(2, {}).get("pass_rate", 0) * 100
        if ss_l2_pr > 0:
            l2_ss_passers.append({
                "model": e["model"],
                "short_name": e["short_name"],
                "ss_l2_pass_rate": r1(ss_l2_pr),
            })

    stats["per_level_analysis"] = {
        "ag_l0_100_count": ag_l0_100_count,
        "ag_l1_100_count": ag_l1_100_count,
        "ag_l1_median": r1(ag_l1_median),
        "ag_l2_median": r1(ag_l2_median),
        "ag_l2_range_pp": ag_l2_range,
        "ag_l2_above_85_count": ag_l2_above_85,
        "l2_ss_pass_rate_mean": l2_ss_pass_rate_mean,
        "l2_ss_passers": l2_ss_passers,
    }

    # =========================================================================
    # §3.5 / §4.3: Tool-trained vs control group
    # =========================================================================
    tool_trained_ag = [e["ag_overall"] for e in ag_rankings if e["tool_trained"]]
    control_ag = [e["ag_overall"] for e in ag_rankings if not e["tool_trained"]]
    tool_trained_ss = [e["ss_overall"] for e in ag_rankings if e["tool_trained"]]
    control_ss = [e["ss_overall"] for e in ag_rankings if not e["tool_trained"]]

    stats["tool_trained_vs_control"] = {
        "tool_trained": {
            "n": len(tool_trained_ag),
            "ag_mean": r1(sum(tool_trained_ag) / len(tool_trained_ag)),
            "ag_range_min": r1(min(tool_trained_ag)),
            "ag_range_max": r1(max(tool_trained_ag)),
            "ag_std_dev": r1(std_dev(tool_trained_ag)),
            "ss_mean": r1(sum(tool_trained_ss) / len(tool_trained_ss)),
        },
        "control": {
            "n": len(control_ag),
            "ag_mean": r1(sum(control_ag) / len(control_ag)),
            "ag_range_min": r1(min(control_ag)),
            "ag_range_max": r1(max(control_ag)),
            "ag_std_dev": r1(std_dev(control_ag)),
            "ss_mean": r1(sum(control_ss) / len(control_ss)),
        },
        "ag_delta": r1(sum(tool_trained_ag) / len(tool_trained_ag) - sum(control_ag) / len(control_ag)),
        "ss_delta": r1(sum(tool_trained_ss) / len(tool_trained_ss) - sum(control_ss) / len(control_ss)),
    }

    # =========================================================================
    # §3.6: Size tiers
    # =========================================================================
    tiers = {}
    for e in ag_rankings:
        tier = assign_tier(e["model"], e.get("params_string", ""))
        if tier not in tiers:
            tiers[tier] = []
        tiers[tier].append(e)

    tier_stats = {}
    tier_order = ["Tiny (3-4B)", "Small (7-9.4B)", "Medium (12-15B)",
                  "Large (20-24B)", "XL (30-36B)", "XXL (80B)"]
    for tier_name in tier_order:
        entries = tiers.get(tier_name, [])
        if not entries:
            continue
        scores = [e["ag_overall"] for e in entries]
        tier_stats[tier_name] = {
            "n": len(entries),
            "models": [e["short_name"] for e in entries],
            "ag_mean": r1(sum(scores) / len(scores)),
            "ag_range_min": r1(min(scores)),
            "ag_range_max": r1(max(scores)),
        }
    stats["size_tiers"] = tier_stats

    # =========================================================================
    # qwen3-4b "outperforms" analysis
    # =========================================================================
    qwen3_4b_score = None
    for e in ag_rankings:
        if "qwen3-4b-thinking" in e["model"]:
            qwen3_4b_score = e["ag_overall"]
            break

    if qwen3_4b_score is not None:
        beaten_models = []
        for e in ag_rankings:
            if e["ag_overall"] < qwen3_4b_score and e["model"] != "qwen/qwen3-4b-thinking-2507":
                beaten_models.append({
                    "model": e["model"],
                    "short_name": e["short_name"],
                    "params_string": e["params_string"],
                    "ag_overall": e["ag_overall"],
                })

        # Compute param ratios for beaten models
        param_ratios = []
        for bm in beaten_models:
            try:
                bm_params = parse_params(bm["params_string"])
                ratio = bm_params / 4.0  # qwen3-4b is 4B
                param_ratios.append({
                    "model": bm["short_name"],
                    "params": bm_params,
                    "ratio": r1(ratio),
                })
            except (ValueError, ZeroDivisionError):
                pass

        max_ratio = max(pr["ratio"] for pr in param_ratios) if param_ratios else 0

        stats["qwen3_4b_analysis"] = {
            "score": qwen3_4b_score,
            "beaten_models": beaten_models,
            "beaten_count": len(beaten_models),
            "param_ratios": sorted(param_ratios, key=lambda x: x["ratio"], reverse=True),
            "max_param_ratio": max_ratio,
        }

    # =========================================================================
    # Disk sizes from size_bytes
    # =========================================================================
    disk_sizes = {}
    for e in ag_rankings:
        model_meta = meta.get(e["model"], {})
        size_bytes = model_meta.get("size_bytes", 0)
        disk_sizes[e["model"]] = r1(size_bytes / (1024 ** 3))
    stats["disk_sizes_gb"] = disk_sizes

    # =========================================================================
    # Models exceeding 85% overall in agentic
    # =========================================================================
    above_85_ag = sum(1 for e in ag_rankings if e["ag_overall"] >= 85.0)
    stats["models_above_85_ag"] = above_85_ag

    # =========================================================================
    # §4.1: Improvement ratio for qwen3-4b-thinking
    # =========================================================================
    for e in ag_rankings:
        if "qwen3-4b-thinking" in e["model"]:
            if e["ss_overall"] > 0:
                stats["qwen3_4b_improvement_ratio"] = r1(e["ag_overall"] / e["ss_overall"])
            break

    return stats


def print_summary(stats: dict):
    """Print a human-readable summary of all computed statistics."""
    print("=" * 80)
    print("PUBLISHED STATISTICS — AUTHORITATIVE REFERENCE")
    print("=" * 80)

    # Rankings
    print("\n--- §3.1 Agentic Rankings ---")
    print(f"{'Rank':<5} {'Model':<40} {'L0':>6} {'L1':>6} {'L2':>6} {'Overall':>8}")
    for e in stats["model_rankings"]:
        print(f"{e['ag_rank']:<5} {e['short_name']:<40} {e['ag_l0']:>6.1f} {e['ag_l1']:>6.1f} {e['ag_l2']:>6.1f} {e['ag_overall']:>8.1f}")

    print("\n--- §3.2 Single-shot Rankings ---")
    ss_sorted = sorted(stats["model_rankings"], key=lambda x: x["ss_overall"], reverse=True)
    for e in ss_sorted:
        print(f"  {e['short_name']:<40} {e['ss_l0']:>6.1f} {e['ss_l1']:>6.1f} {e['ss_l2']:>6.1f} {e['ss_overall']:>8.1f}")

    # Level comparison
    print("\n--- §3.3 Level Comparison (SS vs AG) ---")
    lc = stats["level_comparison"]
    for level in ["L0", "L1", "L2"]:
        d = lc[level]
        print(f"  {level}: SS score {d['ss_score_mean']}% → AG score {d['ag_score_mean']}%  "
              f"Lift: +{d['lift']}pp  "
              f"SS PR: {d['ss_pass_rate_mean']}%  AG PR: {d['ag_pass_rate_mean']}%")

    ol = stats["overall_lift"]
    print(f"\n  Overall lift: mean +{ol['mean']}pp, median +{ol['median']}pp")

    # Per-model lift
    print("\n--- §3.3 Per-model Lift (sorted by magnitude) ---")
    for e in stats["per_model_lift"]:
        print(f"  {e['short_name']:<40} SS {e['ss_overall']:>5.1f} → AG {e['ag_overall']:>5.1f}  Lift: +{e['lift']:.1f}")

    # Per-level analysis
    print("\n--- §3.4 Per-Level Analysis ---")
    pla = stats["per_level_analysis"]
    print(f"  L0: {pla['ag_l0_100_count']}/21 models at 100.0%")
    print(f"  L1: {pla['ag_l1_100_count']}/21 models at 100.0%")
    print(f"  L1 median: {pla['ag_l1_median']}%")
    print(f"  L2 median: {pla['ag_l2_median']}%")
    print(f"  L2 range: {pla['ag_l2_range_pp']}pp")
    print(f"  L2 models above 85%: {pla['ag_l2_above_85_count']}")
    print(f"  L2 SS pass rate mean: {pla['l2_ss_pass_rate_mean']}%")
    print(f"  L2 SS passers: {pla['l2_ss_passers']}")

    # Tool-trained vs control
    print("\n--- §3.5 Tool-trained vs Control ---")
    ttc = stats["tool_trained_vs_control"]
    tt = ttc["tool_trained"]
    ct = ttc["control"]
    print(f"  Tool-trained (n={tt['n']}): AG mean {tt['ag_mean']}%, "
          f"range {tt['ag_range_min']}-{tt['ag_range_max']}%, "
          f"σ={tt['ag_std_dev']}pp, SS mean {tt['ss_mean']}%")
    print(f"  Control (n={ct['n']}):      AG mean {ct['ag_mean']}%, "
          f"range {ct['ag_range_min']}-{ct['ag_range_max']}%, "
          f"σ={ct['ag_std_dev']}pp, SS mean {ct['ss_mean']}%")
    print(f"  AG delta: +{ttc['ag_delta']}pp")
    print(f"  SS delta: +{ttc['ss_delta']}pp")

    # Size tiers
    print("\n--- §3.6 Size Tiers ---")
    for tier_name, td in stats["size_tiers"].items():
        print(f"  {tier_name}: n={td['n']}, mean={td['ag_mean']}%, "
              f"range={td['ag_range_min']}-{td['ag_range_max']}%")

    # qwen3-4b analysis
    if "qwen3_4b_analysis" in stats:
        qa = stats["qwen3_4b_analysis"]
        print(f"\n--- qwen3-4b-thinking Analysis ---")
        print(f"  Score: {qa['score']}%")
        print(f"  Beats {qa['beaten_count']} models")
        print(f"  Max param ratio of beaten model: {qa['max_param_ratio']}x")
        for pr in qa["param_ratios"]:
            print(f"    {pr['model']:<35} {pr['params']}B  ({pr['ratio']}x)")

    # Models above 85%
    print(f"\n--- Models >= 85% agentic overall: {stats['models_above_85_ag']}/21 ---")

    # Improvement ratio
    if "qwen3_4b_improvement_ratio" in stats:
        print(f"\n--- §4.1 qwen3-4b improvement ratio (AG/SS): {stats['qwen3_4b_improvement_ratio']}x ---")

    # Disk sizes
    print("\n--- Disk Sizes (GB) ---")
    for model, gb in stats["disk_sizes_gb"].items():
        short = model.split("/")[-1] if "/" in model else model
        print(f"  {short:<40} {gb} GB")


def main():
    run_ts = parse_run_arg()
    data = load_results(run_ts)
    if data is None:
        print("Error: No result files found.", file=sys.stderr)
        sys.exit(1)

    meta = load_lmstudio_metadata()
    stats = compute_all_stats(data, meta)

    # Write JSON
    out_path = Path(__file__).parent / "published_stats.json"
    with open(out_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"Wrote: {out_path}")

    # Print summary
    print_summary(stats)


if __name__ == "__main__":
    main()

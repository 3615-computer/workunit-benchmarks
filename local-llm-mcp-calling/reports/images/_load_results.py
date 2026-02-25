"""
Shared data loader for benchmark graph scripts.

Loads result JSON files from v1_singleshot and v2_agentic runs,
builds a unified data structure for the graph generators.

Usage:
    from _load_results import load_results
    data = load_results()       # uses latest run
    data = load_results("20250224_120000")  # specific run
"""

import json
import os
import re
import sys
from pathlib import Path


# Relative path from reports/images/ to results/
RESULTS_BASE = Path(__file__).parent / ".." / ".." / "results"

METHODOLOGY_DIRS = {
    "ss": "v1_singleshot",
    "ag": "v2_agentic",
}


def _find_run_dir(methodology_dir: Path, run_timestamp: str = None) -> Path | None:
    """Find the run directory: specific timestamp, latest symlink, or most recent run_*."""
    if run_timestamp:
        candidate = methodology_dir / f"run_{run_timestamp}"
        if candidate.is_dir():
            return candidate
        # Also try without run_ prefix in case user passes just the dir name
        candidate = methodology_dir / run_timestamp
        if candidate.is_dir():
            return candidate
        return None

    # Try latest symlink first
    latest = methodology_dir / "latest"
    if latest.exists():
        resolved = latest.resolve()
        if resolved.is_dir():
            return resolved

    # Fall back to most recent run_* directory (sorted lexicographically)
    run_dirs = sorted(
        [d for d in methodology_dir.iterdir() if d.is_dir() and d.name.startswith("run_")],
        key=lambda p: p.name,
        reverse=True,
    )
    return run_dirs[0] if run_dirs else None


def _extract_size(model_name: str) -> str:
    """
    Extract model size from model name.

    Looks for patterns like:
      - '-3b', '-30b', '-80b' (dash + digits + b)
      - '-3.5b', '-4.6v' (dash + digits + dot + digits + letter)
      - '-8.3b' etc.
      - Trailing size like 'qwen3-4b-thinking' -> '4B'
    """
    # Match patterns like -30b, -3b, -80b, -14b, -8.3b, -24b, -3.5b at word boundaries
    # Look for the last size-like pattern in the model name
    matches = re.findall(r'[-_](\d+(?:\.\d+)?)[bB](?:[-_]|$)', model_name)
    if matches:
        # Take the last match (most likely the actual size)
        size = matches[-1]
        # Return as clean format
        return f"{size}B"

    # Some models have size embedded differently, e.g., "21b" in "ernie-4.5-21b"
    matches = re.findall(r'(\d+(?:\.\d+)?)[bB]', model_name)
    if matches:
        return f"{matches[-1]}B"

    return ""


def _format_model_label(model_name: str, tool_trained: bool) -> str:
    """
    Format model name for graph label.

    Strips org prefix (e.g., 'mistralai/' -> ''),
    appends size if found, marks not-tool-trained with cross.
    """
    # Strip org prefix
    if "/" in model_name:
        label = model_name.split("/", 1)[1]
    else:
        label = model_name

    size = _extract_size(label)
    if size:
        label = f"{label} {size}"
    if not tool_trained:
        label = f"{label} \u2717"  # cross mark

    return label


def _format_short_label(model_name: str) -> str:
    """
    Format a short label for scatter plot (Panel A of graph 3).

    Strips org prefix, extracts base name, puts size on second line.
    """
    if "/" in model_name:
        name = model_name.split("/", 1)[1]
    else:
        name = model_name

    size = _extract_size(name)
    if size:
        return f"{name}\n{size}"
    return name


def load_results(run_timestamp: str = None) -> dict | None:
    """
    Load all result JSON files and build a unified data structure.

    Args:
        run_timestamp: Optional specific run timestamp to use instead of latest.

    Returns:
        Dictionary with keys:
            'models': {
                model_name: {
                    'tool_trained': bool,
                    'label': str,           # formatted label for bar charts
                    'short_label': str,      # formatted label for scatter plots
                    'ss': {                  # single-shot methodology
                        0: {'pass_rate': float, 'avg_score': float, 'total': int, 'passed': int},
                        1: {...},
                        2: {...},
                    },
                    'ag': {                  # agentic methodology
                        0: {...},
                        1: {...},
                        2: {...},
                    },
                    'ss_overall': float,     # avg of available ss level avg_scores * 100
                    'ag_overall': float,     # avg of available ag level avg_scores * 100
                }
            },
            'sorted_models': [model_name, ...],  # sorted by ag_overall descending
        or None if no results found.
    """
    results_base = RESULTS_BASE.resolve()

    if not results_base.is_dir():
        print(f"Error: Results directory not found: {results_base}", file=sys.stderr)
        return None

    models = {}

    for method_key, dir_name in METHODOLOGY_DIRS.items():
        method_dir = results_base / dir_name
        if not method_dir.is_dir():
            continue

        run_dir = _find_run_dir(method_dir, run_timestamp)
        if run_dir is None:
            continue

        # Load all JSON files from this run
        json_files = sorted(run_dir.glob("*.json"))
        for jf in json_files:
            try:
                with open(jf) as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                print(f"Warning: Failed to load {jf}: {e}", file=sys.stderr)
                continue

            model_name = data.get("model", "")
            level = data.get("level")
            tool_trained = data.get("tool_trained", True)
            summary = data.get("summary", {})

            if not model_name or level is None:
                continue

            if model_name not in models:
                models[model_name] = {
                    "tool_trained": tool_trained,
                    "label": _format_model_label(model_name, tool_trained),
                    "short_label": _format_short_label(model_name),
                    "ss": {},
                    "ag": {},
                    "ss_overall": 0.0,
                    "ag_overall": 0.0,
                }

            models[model_name][method_key][level] = {
                "pass_rate": summary.get("pass_rate", 0.0),
                "avg_score": summary.get("avg_score", 0.0),
                "total": summary.get("total", 0),
                "passed": summary.get("passed", 0),
            }

    if not models:
        print("Error: No result JSON files found in any run directory.", file=sys.stderr)
        print(f"Looked in: {results_base}", file=sys.stderr)
        return None

    # Compute overall scores per model per methodology
    for model_name, mdata in models.items():
        for method_key in ("ss", "ag"):
            level_data = mdata[method_key]
            if level_data:
                scores = [ld["avg_score"] for ld in level_data.values()]
                mdata[f"{method_key}_overall"] = (sum(scores) / len(scores)) * 100
            else:
                mdata[f"{method_key}_overall"] = 0.0

    # Sort by ag_overall descending
    sorted_models = sorted(models.keys(), key=lambda m: models[m]["ag_overall"], reverse=True)

    return {
        "models": models,
        "sorted_models": sorted_models,
    }


def parse_run_arg() -> str | None:
    """Parse --run TIMESTAMP from sys.argv."""
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--run" and i + 1 < len(args):
            return args[i + 1]
    return None


def load_from_cli() -> dict:
    """
    Convenience function: parse CLI args and load results.
    Exits with error message if no results found.
    """
    run_ts = parse_run_arg()
    data = load_results(run_ts)
    if data is None:
        if run_ts:
            print(f"Error: No results found for run timestamp '{run_ts}'.", file=sys.stderr)
        else:
            print("Error: No result files found. Run benchmarks first.", file=sys.stderr)
        print(f"Expected results in: {RESULTS_BASE.resolve()}/{{v1_singleshot,v2_agentic}}/",
              file=sys.stderr)
        sys.exit(1)
    return data

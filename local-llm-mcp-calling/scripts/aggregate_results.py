#!/usr/bin/env python3
"""
Benchmark Results Aggregator
Reads all JSON result files and generates the final comparison table.

Usage:
    python aggregate_results.py                       # Uses latest run dirs
    python aggregate_results.py --run 20260225_143000  # Specific run timestamp
    python aggregate_results.py --results-dir /path    # Flat directory of JSONs
    python aggregate_results.py --output report.md     # Also writes markdown
"""

import argparse
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich import print as rprint
except ImportError:
    print("Missing: pip install rich")
    import sys; sys.exit(1)

BENCHMARK_DIR = Path(__file__).parent.parent
RESULTS_DIR = BENCHMARK_DIR / "results"
console = Console()


def find_result_dirs(run_id: str | None = None) -> list[Path]:
    """Find result directories to aggregate.

    If run_id is given, looks for results/{version}/run_{run_id}/ dirs.
    Otherwise, follows the 'latest' symlinks or falls back to flat dirs.
    """
    dirs = []
    for version_dir in ("v1_singleshot", "v2_agentic"):
        base = RESULTS_DIR / version_dir
        if not base.exists():
            continue

        if run_id:
            run_dir = base / f"run_{run_id}"
            if run_dir.exists():
                dirs.append(run_dir)
        else:
            # Try "latest" symlink first
            latest = base / "latest"
            if latest.is_symlink() and latest.resolve().exists():
                dirs.append(latest.resolve())
            elif latest.is_dir():
                dirs.append(latest)
            else:
                # Fall back: find most recent run_* directory
                run_dirs = sorted(base.glob("run_*"), reverse=True)
                if run_dirs:
                    dirs.append(run_dirs[0])
                elif list(base.glob("level*_*.json")):
                    # Legacy flat directory with JSON files directly in it
                    dirs.append(base)

    return dirs


def load_results(result_dirs: list[Path]) -> list[dict]:
    """Load all JSON result files from given directories, deduplicate by model+level (keep latest)."""
    files = []
    for d in result_dirs:
        files.extend(sorted(d.glob("level*_*.json")))

    if not files:
        dirs_str = ", ".join(str(d) for d in result_dirs) if result_dirs else "none found"
        console.print(f"[red]No result files found in: {dirs_str}[/red]")
        return []

    # Group by (level, model), keep latest
    by_model_level = {}
    for f in files:
        with open(f) as fh:
            data = json.load(fh)
        key = (data["level"], data["model"])
        ts = data.get("timestamp", "")
        if key not in by_model_level or ts > by_model_level[key]["timestamp"]:
            by_model_level[key] = data

    return list(by_model_level.values())


def build_matrix(all_results: list[dict]) -> dict:
    """Build a model -> level -> stats matrix."""
    models = sorted(set(r["model"] for r in all_results))
    levels = sorted(set(r["level"] for r in all_results))

    matrix = {}
    for r in all_results:
        model = r["model"]
        level = r["level"]
        if model not in matrix:
            matrix[model] = {}
        matrix[model][level] = r["summary"]

    return {"models": models, "levels": levels, "data": matrix}


def print_comparison_table(matrix: dict):
    levels = matrix["levels"]
    models = matrix["models"]
    data = matrix["data"]

    table = Table(
        title="Workunit MCP Benchmark — Model Comparison",
        show_header=True,
        header_style="bold cyan",
        show_lines=True
    )

    table.add_column("Model", style="bold", no_wrap=True)
    for lvl in levels:
        table.add_column(f"L{lvl} Pass%", justify="center")
        table.add_column(f"L{lvl} Score", justify="center")
    table.add_column("Overall", justify="center", style="bold yellow")

    rows = []
    for model in models:
        row = [model]
        scores = []
        for lvl in levels:
            stats = data.get(model, {}).get(lvl)
            if stats:
                pass_pct = f"{stats['pass_rate']:.0%}"
                avg_score = f"{stats['avg_score']:.0%}"
                scores.append(stats["avg_score"])
            else:
                pass_pct = "—"
                avg_score = "—"
            row.extend([pass_pct, avg_score])
        overall = f"{sum(scores)/len(scores):.0%}" if scores else "—"
        row.append(overall)
        rows.append((sum(scores) / len(scores) if scores else 0, row))

    # Sort by overall score descending
    rows.sort(reverse=True, key=lambda x: x[0])
    for _, row in rows:
        table.add_row(*row)

    console.print(table)


def generate_markdown(matrix: dict, all_results: list[dict]) -> str:
    levels = matrix["levels"]
    models = matrix["models"]
    data = matrix["data"]

    lines = []
    lines.append("## Benchmark Results\n")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

    # Summary table
    header = "| Model |"
    separator = "|-------|"
    for lvl in levels:
        header += f" L{lvl} Pass% | L{lvl} Score |"
        separator += "---------|---------|"
    header += " Overall |"
    separator += "---------|"

    lines.append(header)
    lines.append(separator)

    rows_with_score = []
    for model in models:
        scores = []
        row = f"| {model} |"
        for lvl in levels:
            stats = data.get(model, {}).get(lvl)
            if stats:
                pass_pct = f"{stats['pass_rate']:.0%}"
                avg_score = f"{stats['avg_score']:.0%}"
                scores.append(stats["avg_score"])
            else:
                pass_pct = "—"
                avg_score = "—"
            row += f" {pass_pct} | {avg_score} |"
        overall = f"{sum(scores)/len(scores):.0%}" if scores else "—"
        row += f" **{overall}** |"
        rows_with_score.append((sum(scores)/len(scores) if scores else 0, row))

    for _, row in sorted(rows_with_score, reverse=True):
        lines.append(row)

    lines.append("")

    # Per-task breakdown by level
    for lvl in levels:
        level_results = [r for r in all_results if r["level"] == lvl]
        if not level_results:
            continue

        lines.append(f"\n### Level {lvl} — Task Breakdown\n")

        # Collect all task IDs for this level
        task_ids = []
        task_names = {}
        for r in level_results:
            for task_r in r.get("results", []):
                tid = task_r["task_id"]
                if tid not in task_ids:
                    task_ids.append(tid)
                    task_names[tid] = task_r["task_name"]

        task_ids.sort()

        # Header
        header = "| Task |"
        separator = "|------|"
        model_cols = sorted(set(r["model"] for r in level_results))
        for m in model_cols:
            short = m.split("/")[-1][:20]
            header += f" {short} |"
            separator += "--------|"
        lines.append(header)
        lines.append(separator)

        # Per-task rows
        for tid in task_ids:
            row = f"| {tid}: {task_names.get(tid, '')[:40]} |"
            for model in model_cols:
                model_result = next((r for r in level_results if r["model"] == model), None)
                if model_result:
                    task_result = next(
                        (tr for tr in model_result.get("results", []) if tr["task_id"] == tid),
                        None
                    )
                    if task_result:
                        icon = "✅" if task_result["passed"] else "❌"
                        row += f" {icon} {task_result['score']:.0%} |"
                    else:
                        row += " — |"
                else:
                    row += " — |"
            lines.append(row)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Aggregate Workunit MCP benchmark results")
    parser.add_argument(
        "--run",
        help="Run timestamp to aggregate (e.g., 20260225_143000). Default: latest run.",
    )
    parser.add_argument(
        "--results-dir",
        help="Legacy: flat directory containing level*_*.json files (overrides --run)",
    )
    parser.add_argument("--output", "-o", help="Write markdown report to this file")
    args = parser.parse_args()

    if args.results_dir:
        # Legacy mode: single flat directory
        result_dirs = [Path(args.results_dir)]
    else:
        result_dirs = find_result_dirs(args.run)

    if not result_dirs:
        console.print("[red]No result directories found.[/red]")
        console.print("[dim]Run benchmarks first, or use --results-dir to point at a flat directory.[/dim]")
        return

    all_results = load_results(result_dirs)

    if not all_results:
        return

    console.print(f"\n[dim]Loaded {len(all_results)} result file(s) from {len(result_dirs)} director{'y' if len(result_dirs) == 1 else 'ies'}[/dim]")
    for d in result_dirs:
        console.print(f"  [dim]{d}[/dim]")
    console.print()

    matrix = build_matrix(all_results)
    print_comparison_table(matrix)

    # Determine where to write the report
    if args.output:
        report_path = Path(args.output)
    elif len(result_dirs) == 1:
        report_path = result_dirs[0] / "aggregated_report.md"
    else:
        report_path = RESULTS_DIR / "aggregated_report.md"

    md = generate_markdown(matrix, all_results)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(md)
    console.print(f"[dim]Markdown report written to {report_path}[/dim]")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Benchmark Results Aggregator
Reads all JSON result files and generates the final comparison table.

Usage:
    python aggregate_results.py                    # Uses ./results/ directory
    python aggregate_results.py --results-dir /path/to/results
    python aggregate_results.py --output report.md # Also writes markdown
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

RESULTS_DIR = Path(__file__).parent.parent / "results"
console = Console()


def load_results(results_dir: Path) -> list[dict]:
    """Load all JSON result files, deduplicate by model+level (keep latest)."""
    files = sorted(results_dir.glob("level*_*.json"))
    if not files:
        console.print(f"[red]No result files found in {results_dir}[/red]")
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
    """Build a model → level → stats matrix."""
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
    parser.add_argument("--results-dir", default=str(RESULTS_DIR))
    parser.add_argument("--output", "-o", help="Write markdown report to this file")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    all_results = load_results(results_dir)

    if not all_results:
        return

    console.print(f"\n[dim]Loaded {len(all_results)} result file(s)[/dim]\n")

    matrix = build_matrix(all_results)
    print_comparison_table(matrix)

    if args.output:
        md = generate_markdown(matrix, all_results)
        out = Path(args.output)
        out.write_text(md)
        console.print(f"\n[dim]Markdown report written to {out}[/dim]")
    else:
        md = generate_markdown(matrix, all_results)
        report_path = results_dir / "aggregated_report.md"
        report_path.write_text(md)
        console.print(f"\n[dim]Markdown report written to {report_path}[/dim]")


if __name__ == "__main__":
    main()

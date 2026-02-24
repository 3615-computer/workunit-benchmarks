#!/usr/bin/env python3
"""
Workunit MCP Benchmark — Single-shot Runner
Runs all three levels for all models via LM Studio's OpenAI-compatible API.
Evaluates the first response only (no agentic loop). No MCP server required —
tool calls are validated structurally, not executed.

Usage:
    # Run all models, all levels
    python runner_v1_singleshot.py --models ../models.txt

    # Single model, single level
    python runner_v1_singleshot.py --model ibm/granite-4-h-tiny --level 0

    # Dry run — show plan without executing
    python runner_v1_singleshot.py --models ../models.txt --dry-run

    # List models available in LM Studio
    python runner_v1_singleshot.py --list-models

Requirements:
    pip install openai rich
"""

import argparse
import json
import os
import re
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from openai import OpenAI
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
except ImportError:
    print("Missing dependencies. Run: pip install openai rich")
    sys.exit(1)

# ─── Config ───────────────────────────────────────────────────────────────────

_LMSTUDIO_HOST     = os.environ.get("LMSTUDIO_HOST", "localhost:1234")
LMSTUDIO_BASE_URL  = f"http://{_LMSTUDIO_HOST}/v1"
LMSTUDIO_MGMT_URL  = f"http://{_LMSTUDIO_HOST}"

BENCHMARK_DIR = Path(__file__).parent.parent
TASKS_DIR     = BENCHMARK_DIR / "tasks"
RESULTS_DIR   = BENCHMARK_DIR / "results" / "v1_singleshot"
PROJECT_ROOT  = BENCHMARK_DIR.parent

TASK_FILES = {
    0: TASKS_DIR / "level0_explicit.json",
    1: TASKS_DIR / "level1_natural.json",
    2: TASKS_DIR / "level2_reasoning.json",
}

SYSTEM_PROMPT = (
    "You are a helpful AI assistant with access to the Workunit project management "
    "platform via MCP tools. When asked to perform an action, you MUST call the "
    "appropriate tool — do not describe what you would do, actually call it. "
    "Use only the tools provided; do not invent tool names."
)

console = Console()


# ─── LM Studio helpers ────────────────────────────────────────────────────────

def list_models() -> list[dict]:
    """Return all LLMs from LM Studio (excludes embedding models)."""
    import urllib.request
    with urllib.request.urlopen(f"{LMSTUDIO_MGMT_URL}/api/v0/models") as resp:
        data = json.loads(resp.read())
    return [m for m in data["data"] if m.get("type") == "llm"]


def get_loaded_model() -> str | None:
    """Return the currently loaded model ID, or None."""
    for m in list_models():
        if m.get("state") == "loaded":
            return m["id"]
    return None


def wait_for_model(model_id: str, timeout: int = 300) -> bool:
    """
    Poll until model_id is loaded. LM Studio auto-loads on first chat request,
    but large models can take 30-120s. We send a tiny probe request and wait.
    """
    client = OpenAI(base_url=LMSTUDIO_BASE_URL, api_key="lm-studio")
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            resp = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
                temperature=0.0,
            )
            if resp.model:
                return True
        except Exception:
            pass
        time.sleep(5)

    return False


# ─── MCP Tool schemas (used as `tools` in chat completions) ───────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ping",
            "description": "Test MCP server connectivity",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Message to echo"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_authenticated_user",
            "description": "Get details about the authenticated user",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_project",
            "description": "Create a project to organize workunits and assets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Project name (max 255 chars)"},
                    "description": {"type": "string", "description": "Project description"},
                    "status": {"type": "string", "enum": ["planning", "active", "on_hold", "completed", "archived"]},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "repo_url": {"type": "string"},
                    "default_branch": {"type": "string"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_project",
            "description": "Get project details with optional assets, checkins, and workunits.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "include_stats": {"type": "boolean"},
                    "include_assets": {"type": "boolean"},
                    "include_workunits": {"type": "boolean"}
                },
                "required": ["id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_projects",
            "description": "List projects with optional status/owner/tag filters and pagination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "organization_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["planning", "active", "on_hold", "completed", "archived"]},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "page_size": {"type": "integer"},
                    "page_number": {"type": "integer"}
                },
                "required": ["organization_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_project",
            "description": "Update project fields via update_mask.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "update_mask": {
                        "type": "object",
                        "properties": {"paths": {"type": "array", "items": {"type": "string"}}},
                        "required": ["paths"]
                    },
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "status": {"type": "string", "enum": ["planning", "active", "on_hold", "completed", "archived"]},
                    "tags": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["id", "update_mask"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_project",
            "description": "Removes a project. action='archive' preserves data, action='delete' is permanent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "action": {"type": "string", "enum": ["archive", "delete"]}
                },
                "required": ["id", "action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_workunit",
            "description": "Create a workunit with problem statement and success criteria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "problem_statement": {"type": "string", "description": "Problem statement (max 1000 chars)"},
                    "success_criteria": {"type": "string", "description": "Success criteria (max 1000 chars)"},
                    "project_id": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
                    "status": {"type": "string", "enum": ["draft", "active", "paused", "completed", "archived"]},
                    "description": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["name", "problem_statement", "success_criteria"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_workunit",
            "description": "Get workunit details with optional tasks and context atoms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "include_tasks": {"type": "boolean"},
                    "include_ai_context": {"type": "boolean"},
                    "include_assets": {"type": "boolean"}
                },
                "required": ["id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_workunit",
            "description": "Update workunit fields via update_mask. status=completed requires completion_notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "update_mask": {
                        "type": "object",
                        "properties": {"paths": {"type": "array", "items": {"type": "string"}}},
                        "required": ["paths"]
                    },
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "problem_statement": {"type": "string"},
                    "success_criteria": {"type": "string"},
                    "priority": {"type": "string", "enum": ["low", "normal", "high", "urgent"]},
                    "status": {"type": "string", "enum": ["draft", "active", "paused", "completed", "archived"]},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "completion_notes": {"type": "string"},
                    "archive_reason": {"type": "string"}
                },
                "required": ["id", "update_mask"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a task in a workunit with title, priority, and optional dependencies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workunit_id": {"type": "string"},
                    "title": {"type": "string", "description": "Task title (max 255 chars)"},
                    "description": {"type": "string"},
                    "status": {"type": "string", "enum": ["todo", "in_progress", "done", "blocked", "wont_do"]},
                    "priority": {"type": "string", "enum": ["low", "normal", "high"]},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "depends_on": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["workunit_id", "title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_task",
            "description": "Retrieve detailed information about a specific task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "include_comments": {"type": "boolean"},
                    "include_dependencies": {"type": "boolean"}
                },
                "required": ["id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "Update task fields via update_mask.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "update_mask": {
                        "type": "object",
                        "properties": {"paths": {"type": "array", "items": {"type": "string"}}},
                        "required": ["paths"]
                    },
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "status": {"type": "string", "enum": ["todo", "in_progress", "done", "blocked", "wont_do"]},
                    "priority": {"type": "string", "enum": ["low", "normal", "high"]},
                    "tags": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["id", "update_mask"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_context",
            "description": "Save a structured context atom to a workunit's trail-of-thought.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workunit_id": {"type": "string"},
                    "atom_type": {"type": "string", "enum": ["decision", "insight", "question", "attempt", "progress"]},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "importance": {"type": "string", "enum": ["critical", "high", "normal", "low"]},
                    "tags": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["workunit_id", "atom_type", "title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search workunits, tasks, and assets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "result_types": {"type": "array", "items": {"type": "string", "enum": ["workunit", "task", "asset"]}},
                    "page_size": {"type": "integer"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_asset",
            "description": "Creates a new asset. asset_type: product|people|knowledge|system.",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_type": {"type": "string", "enum": ["product", "people", "knowledge", "system"]},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "status": {"type": "string"},
                    "category": {"type": "string"},
                    "format": {"type": "string", "enum": ["document", "video", "course", "database", "wiki", "spreadsheet"]},
                    "lifecycle_stage": {"type": "string", "enum": ["concept", "development", "production", "maintenance", "discontinued"]},
                    "tags": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["asset_type", "name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "project_asset_link",
            "description": "Link or unlink an asset to a project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "asset_id": {"type": "string"},
                    "action": {"type": "string", "enum": ["link", "unlink"]},
                    "notes": {"type": "string"}
                },
                "required": ["project_id", "asset_id", "action"]
            }
        }
    }
]


# ─── Validation ────────────────────────────────────────────────────────────────

def _normalize(val):
    """Coerce string booleans to actual booleans for comparison."""
    if isinstance(val, str):
        if val.lower() == "true":
            return True
        if val.lower() == "false":
            return False
    return val


def validate(tool_calls: list[dict], task: dict) -> tuple[bool, float, list[str]]:
    """
    Returns (passed, score 0.0-1.0, details).
    tool_calls is a list of {"name": str, "arguments": dict}.
    """
    validation = task.get("validation", {})
    val_type = validation.get("type", "tool_call_match")
    details = []

    if not tool_calls:
        return False, 0.0, ["No tool call emitted — model responded with text only"]

    # ── Single tool call ──────────────────────────────────────────────────────
    if val_type == "tool_call_match":
        expected_tool = task.get("expected_tool")
        actual_tool = tool_calls[0]["name"]

        if actual_tool != expected_tool:
            return False, 0.0, [f"Wrong tool: called '{actual_tool}', expected '{expected_tool}'"]

        args = tool_calls[0].get("arguments", {})
        score = 1.0

        for param in validation.get("required_params", []):
            if param not in args:
                details.append(f"Missing required param: '{param}'")
                score -= 0.25

        for param, expected_val in validation.get("param_exact", {}).items():
            actual_val = _normalize(args.get(param))
            expected_val = _normalize(expected_val)
            if actual_val != expected_val:
                details.append(f"'{param}': expected {expected_val!r}, got {actual_val!r}")
                score -= 0.15

        for param, expected_val in validation.get("param_contains", {}).items():
            actual_val = args.get(param)
            if isinstance(expected_val, str) and isinstance(actual_val, str):
                if expected_val.lower() not in actual_val.lower():
                    details.append(f"'{param}': expected to contain {expected_val!r}, got {actual_val!r}")
                    score -= 0.15
            elif isinstance(expected_val, list) and isinstance(actual_val, list):
                actual_lower = [v.lower() if isinstance(v, str) else v for v in actual_val]
                for item in expected_val:
                    needle = item.lower() if isinstance(item, str) else item
                    if needle not in actual_lower:
                        details.append(f"'{param}': missing expected item {item!r}")
                        score -= 0.05
            else:
                if _normalize(actual_val) != _normalize(expected_val):
                    details.append(f"'{param}': expected {expected_val!r}, got {actual_val!r}")
                    score -= 0.15

        for param in validation.get("param_present", []):
            if param not in args or args[param] is None or args[param] == "":
                details.append(f"'{param}' should be present but is missing/empty")
                score -= 0.10

        # update_mask path check
        paths_required = validation.get("update_mask_must_contain", [])
        if paths_required:
            update_mask  = args.get("update_mask", {})
            actual_paths = update_mask.get("paths", []) if isinstance(update_mask, dict) else []
            for p in paths_required:
                if p not in actual_paths:
                    details.append(f"update_mask.paths missing '{p}'")
                    score -= 0.10

        score = max(0.0, min(1.0, score))
        passed = score >= 0.6 and not any("required" in d for d in details)
        if not details:
            details = ["All checks passed"]
        return passed, score, details

    # ── Multiple calls of same tool ───────────────────────────────────────────
    elif val_type == "multi_tool_call":
        expected_tool = validation.get("tool")
        matching = [tc for tc in tool_calls if tc["name"] == expected_tool]
        min_count = validation.get("call_count", 1)

        if len(matching) < min_count:
            return False, len(matching) / min_count * 0.5, [
                f"Expected {min_count}× {expected_tool}, got {len(matching)}"
            ]

        required_each = validation.get("each_must_have", [])
        score = 1.0
        for tc in matching:
            for param in required_each:
                if param not in tc.get("arguments", {}):
                    details.append(f"Call missing required param '{param}'")
                    score -= 0.1

        titles_required = validation.get("titles_must_include", [])
        found_titles = [tc.get("arguments", {}).get("title", "") for tc in matching]
        for t in titles_required:
            if not any(t.lower() in ft.lower() for ft in found_titles):
                details.append(f"Expected task title not found: '{t}'")
                score -= 0.15

        score = max(0.0, min(1.0, score))
        passed = score >= 0.7
        if not details:
            details = [f"{len(matching)}/{min_count} calls made correctly"]
        return passed, score, details

    # ── Ordered multi-tool sequence ───────────────────────────────────────────
    elif val_type in ("multi_tool_sequence", "reasoning_chain"):
        steps = validation.get("steps", [])
        step_scores = []

        for i, step in enumerate(steps):
            expected_tool = step.get("tool")
            # Find the i-th call of this tool in order
            matching = [tc for tc in tool_calls if tc["name"] == expected_tool]

            if not matching:
                step_scores.append(0.0)
                details.append(f"Step {i+1} ({expected_tool}): not called")
                continue

            tc = matching[0]
            args = tc.get("arguments", {})
            step_score = 1.0

            for param in step.get("must_have_params", []):
                if param not in args:
                    details.append(f"Step {i+1} ({expected_tool}): missing '{param}'")
                    step_score -= 0.25

            for param, val in step.get("param_exact", {}).items():
                if _normalize(args.get(param)) != _normalize(val):
                    details.append(f"Step {i+1} ({expected_tool}): '{param}'={args.get(param)!r} (want {val!r})")
                    step_score -= 0.2

            for param, val in step.get("param_contains", {}).items():
                actual_val = args.get(param)
                if isinstance(val, str) and isinstance(actual_val, str):
                    if val.lower() not in actual_val.lower():
                        details.append(f"Step {i+1} ({expected_tool}): '{param}'={actual_val!r} (want contains {val!r})")
                        step_score -= 0.2
                else:
                    if _normalize(actual_val) != _normalize(val):
                        details.append(f"Step {i+1} ({expected_tool}): '{param}'={actual_val!r} (want {val!r})")
                        step_score -= 0.2

            for param in step.get("param_present", []):
                if param not in args:
                    details.append(f"Step {i+1} ({expected_tool}): '{param}' missing")
                    step_score -= 0.15

            step_score = max(0.0, step_score)
            step_scores.append(step_score)
            if step_score >= 0.8:
                details.append(f"Step {i+1} ({expected_tool}): ✓")

        score = sum(step_scores) / len(steps) if steps else 0.0
        passed = score >= 0.75
        return passed, score, details

    return False, 0.0, ["Unknown validation type"]


# ─── Single task execution ─────────────────────────────────────────────────────

def run_task(client: OpenAI, model_id: str, task: dict, context: dict) -> dict:
    """Run one task. Returns result dict."""
    # Inject context variables ({{project_id}}, {{workunit_id}}, etc.)
    prompt = task["prompt"]
    for key, val in context.items():
        prompt = prompt.replace(f"{{{{{key}}}}}", str(val))

    start = time.time()
    tool_calls = []
    error = None

    try:
        response = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.0,
            max_tokens=1024,
        )

        msg = response.choices[0].message
        if msg.tool_calls:
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {"_raw": tc.function.arguments}
                tool_calls.append({"name": tc.function.name, "arguments": args})
        else:
            error = f"Text response (no tool call): {(msg.content or '')[:150]}"

    except Exception as e:
        error = str(e)

    elapsed = round(time.time() - start, 2)
    passed, score, details = validate(tool_calls, task)

    return {
        "task_id": task["id"],
        "task_name": task["name"],
        "passed": passed,
        "score": score,
        "details": details,
        "tool_calls": tool_calls,
        "elapsed_s": elapsed,
        "error": error,
    }


# ─── Level runner ──────────────────────────────────────────────────────────────

def run_level(client: OpenAI, model_id: str, level: int, context: dict) -> dict:
    """Run all tasks for a level. Returns summary + per-task results."""
    task_file = TASK_FILES[level]
    level_names = {0: "Explicit", 1: "Natural Language", 2: "Reasoning"}

    with open(task_file) as f:
        task_data = json.load(f)
    tasks = task_data["tasks"]

    console.print(f"\n  [bold]Level {level} — {level_names[level]}[/bold] ({len(tasks)} tasks)")

    results = []
    for task in tasks:
        with console.status(f"    [dim]{task['id']}: {task['name']}[/dim]"):
            result = run_task(client, model_id, task, context)

        icon = "✅" if result["passed"] else "❌"
        score_pct = f"{result['score']:.0%}"
        console.print(f"    {icon} {task['id']} [{score_pct}] {task['name']} ({result['elapsed_s']}s)")
        if not result["passed"] or result["error"]:
            for d in result["details"][:2]:
                console.print(f"       [dim]{d}[/dim]")

        results.append(result)

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    avg_score = sum(r["score"] for r in results) / total if total else 0.0

    return {
        "level": level,
        "summary": {
            "total": total,
            "passed": passed,
            "pass_rate": round(passed / total, 3),
            "avg_score": round(avg_score, 3),
        },
        "results": results,
    }


# ─── Model runner ──────────────────────────────────────────────────────────────

def run_model(model_id: str, levels: list[int], tool_trained: bool,
              force: bool = False, no_git: bool = False) -> dict:
    """Run all levels for one model. Handles model switching automatically.

    Skips levels that already have a result file unless force=True.
    """
    # Check which levels still need running
    pending_levels = []
    for level in levels:
        if not force and result_exists(model_id, level):
            console.print(f"  [dim]Level {level}: already done, skipping (use --force to re-run)[/dim]")
        else:
            pending_levels.append(level)

    if not pending_levels:
        console.print(Panel(
            f"[bold cyan]{model_id}[/bold cyan]\n"
            f"[dim]All levels already complete — skipping[/dim]",
            expand=False
        ))
        return {}

    console.print(Panel(
        f"[bold cyan]{model_id}[/bold cyan]\n"
        f"[dim]Tool-trained: {'yes' if tool_trained else 'no (control group)'}  "
        f"Levels to run: {pending_levels}[/dim]",
        expand=False
    ))

    client = OpenAI(base_url=LMSTUDIO_BASE_URL, api_key="lm-studio")

    # Trigger model load by sending a probe request
    console.print("  [dim]Loading model...[/dim]")
    if not wait_for_model(model_id):
        console.print(f"  [red]Model failed to load within timeout, skipping[/red]")
        return {}

    console.print(f"  [dim]Model ready[/dim]")

    context = {}  # Fresh per model; populated as tasks succeed
    model_results = {
        "model": model_id,
        "tool_trained": tool_trained,
        "timestamp": datetime.now().isoformat(),
        "levels": {},
    }

    for level in pending_levels:
        level_result = run_level(client, model_id, level, context)
        model_results["levels"][level] = level_result

        s = level_result["summary"]
        console.print(
            f"  → Level {level}: {s['passed']}/{s['total']} passed "
            f"({s['pass_rate']:.0%} pass rate, {s['avg_score']:.0%} avg score)"
        )

        # Save result file immediately after each level
        save_result(model_id, level, level_result, tool_trained)
        if not no_git:
            git_commit(model_id, level)

    return model_results


# ─── Persistence ──────────────────────────────────────────────────────────────

def result_exists(model_id: str, level: int) -> bool:
    """Return True if a non-empty result file already exists for this model+level."""
    safe = re.sub(r"[^\w\-.]", "_", model_id)
    existing = list(RESULTS_DIR.glob(f"level{level}_{safe}_*.json"))
    return len(existing) > 0


def save_result(model_id: str, level: int, level_result: dict, tool_trained: bool):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w\-.]", "_", model_id)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS_DIR / f"level{level}_{safe}_{ts}.json"

    output = {
        "level": level,
        "model": model_id,
        "tool_trained": tool_trained,
        "timestamp": datetime.now().isoformat(),
        **level_result,
    }
    with open(out, "w") as f:
        json.dump(output, f, indent=2)

    console.print(f"  [dim]Saved → {out.name}[/dim]")


def git_commit(model_id: str, level: int):
    try:
        subprocess.run(
            ["git", "add", "local-llm-mcp-calling/results/"],
            cwd=str(PROJECT_ROOT), check=True, capture_output=True
        )
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(PROJECT_ROOT), capture_output=True
        )
        if result.returncode != 0:  # There are staged changes
            subprocess.run(
                ["git", "commit", "-m",
                 f"results: level{level} — {model_id}\n\n[benchmark auto-commit]"],
                cwd=str(PROJECT_ROOT), check=True, capture_output=True
            )
            console.print(f"  [dim]Committed to git[/dim]")
    except subprocess.CalledProcessError:
        pass  # Non-fatal: results are saved to disk regardless


# ─── CLI ───────────────────────────────────────────────────────────────────────

def load_models_file(path: str) -> list[tuple[str, bool]]:
    """
    Parse models.txt. Returns list of (model_id, tool_trained).
    Lines with '# * no tool training' annotation are marked tool_trained=False.
    """
    models = []
    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            # Split off inline comment
            parts = stripped.split("#", 1)
            model_id = parts[0].strip()
            comment = parts[1].strip() if len(parts) > 1 else ""
            tool_trained = "no tool training" not in comment.lower()
            models.append((model_id, tool_trained))
    return models


def main():
    parser = argparse.ArgumentParser(
        description="Workunit MCP Benchmark — single-shot runner via LM Studio API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--model", "-m", help="Single model ID")
    group.add_argument("--models", help="Path to models.txt")
    group.add_argument("--list-models", action="store_true", help="List LM Studio models and exit")

    parser.add_argument("--level", type=int, choices=[0, 1, 2], help="Run only this level")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    parser.add_argument("--no-git", action="store_true", help="Skip git commits")
    parser.add_argument(
        "--force", action="store_true",
        help="Re-run levels that already have result files (default: skip completed levels)",
    )
    args = parser.parse_args()

    if args.list_models:
        models = list_models()
        table = Table(title="LM Studio Models", show_header=True)
        table.add_column("Key")
        table.add_column("Size")
        table.add_column("Tool-trained", justify="center")
        table.add_column("State")
        for m in models:
            tool = "✅" if "tool_use" in m.get("capabilities", []) else "❌"
            table.add_row(m["id"], m.get("quantization", ""), tool, m.get("state", "?"))
        console.print(table)
        return

    levels = [args.level] if args.level is not None else [0, 1, 2]

    # Resolve model list
    if args.model:
        model_list = [(args.model, True)]  # Assume tool-trained for single model
    elif args.models:
        model_list = load_models_file(args.models)
    else:
        parser.error("Provide --model, --models, or --list-models")

    if args.dry_run:
        pending = []
        done    = []
        for m, tt in model_list:
            for lvl in levels:
                if not args.force and result_exists(m, lvl):
                    done.append(f"  [dim]✓ L{lvl} {m}[/dim]")
                else:
                    pending.append(f"  • L{lvl} {m}{' (no tool training)' if not tt else ''}")

        lines = []
        if pending:
            lines.append(f"[bold]Will run ({len(pending)}):[/bold]")
            lines.extend(pending)
        if done:
            lines.append(f"\n[dim]Already done, will skip ({len(done)}):[/dim]")
            lines.extend(done)
        lines.append(f"\nTasks per level: L0=11, L1=10, L2=7")

        console.print(Panel("\n".join(lines), title="Dry Run Plan"))
        return

    console.print(Panel(
        f"[bold cyan]Workunit MCP Benchmark — Single-shot[/bold cyan]\n\n"
        f"Models: {len(model_list)}\n"
        f"Levels: {levels}\n"
        f"Force re-run: {'yes' if args.force else 'no (skipping completed levels)'}\n"
        f"LM Studio: {LMSTUDIO_BASE_URL}",
        title="Starting Run"
    ))

    start = time.time()
    for i, (model_id, tool_trained) in enumerate(model_list, 1):
        console.print(f"\n[dim]── Model {i}/{len(model_list)} ──────────────────────────────[/dim]")
        run_model(model_id, levels, tool_trained, args.force, args.no_git)

    elapsed = time.time() - start
    console.print(f"\n[bold green]Complete![/bold green] {elapsed/60:.1f} minutes total")

    # Final aggregated report
    console.print("\nGenerating report...")
    agg = Path(__file__).parent / "aggregate_results.py"
    subprocess.run([sys.executable, str(agg)], cwd=str(BENCHMARK_DIR))

    if not args.no_git:
        # Commit any remaining aggregated report changes
        try:
            subprocess.run(
                ["git", "add", "local-llm-mcp-calling/results/"],
                cwd=str(PROJECT_ROOT), check=True, capture_output=True
            )
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=str(PROJECT_ROOT), capture_output=True
            )
            if result.returncode != 0:
                subprocess.run(
                    ["git", "commit", "-m",
                     "results: aggregated report\n\n[benchmark auto-commit]"],
                    cwd=str(PROJECT_ROOT), check=True, capture_output=True
                )
                console.print(f"  [dim]Committed aggregated report to git[/dim]")
        except subprocess.CalledProcessError:
            pass


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Workunit MCP Benchmark — Agentic Runner
Runs all three levels for all models via LM Studio's OpenAI-compatible API.

Each task runs a full agentic loop:
  1. Send prompt to model
  2. Model returns tool calls → execute against real MCP server → feed results back
  3. Repeat until model stops calling tools or task timeout is hit
  4. Evaluate the full sequence of tool calls made

This means L2 tasks (multi-step reasoning with ID chaining) are actually solvable —
the model gets real data back and can chain IDs across calls.

Usage:
    # Token via env var (recommended):
    export WORKUNIT_TOKEN=your_token
    python runner_v2_agentic.py --models ../models.txt
    python runner_v2_agentic.py --model mistralai/ministral-3-3b --level 0

    # Token via CLI flag:
    python runner_v2_agentic.py --models ../models.txt --token <bearer_token>

    # Local dev stack (MCP at localhost:9000, OAuth at localhost:3000):
    python runner_v2_agentic.py --models ../models.txt --local

    # Cleanup org data only:
    python runner_v2_agentic.py --cleanup-only --yes

Requirements:
    pip install openai rich requests
"""

import argparse
import json
import os
import re
import sys
import time
import threading
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from openai import OpenAI
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    import requests
except ImportError:
    print("Missing dependencies. Run: pip install openai rich requests")
    sys.exit(1)

# ─── Config ───────────────────────────────────────────────────────────────────

_LMSTUDIO_HOST     = os.environ.get("LMSTUDIO_HOST", "localhost:1234")
LMSTUDIO_BASE_URL  = f"http://{_LMSTUDIO_HOST}/v1"
LMSTUDIO_MGMT_URL  = f"http://{_LMSTUDIO_HOST}"
MCP_URL            = os.environ.get("MCP_URL", "https://workunit.app/mcp")
MCP_CALL_TIMEOUT   = int(os.environ.get("MCP_CALL_TIMEOUT", "60"))

BENCHMARK_DIR = Path(__file__).parent.parent
TASKS_DIR     = BENCHMARK_DIR / "tasks"
RESULTS_DIR   = BENCHMARK_DIR / "results" / "v2_agentic"
PROJECT_ROOT  = BENCHMARK_DIR.parent

TASK_FILES = {
    0: TASKS_DIR / "level0_explicit.json",
    1: TASKS_DIR / "level1_natural.json",
    2: TASKS_DIR / "level2_reasoning.json",
}

# Per-task wall-clock timeout in seconds.
# Based on observed timings: seed-oss-36b worst single turn = 279s.
# L2 agentic tasks may need 3-4 turns, so 300s per task is generous
# for all legitimate models while still catching pathological hangs
# like qwen2.5-coder-32b's 1860s text responses.
TASK_TIMEOUT_S = int(os.environ.get("TASK_TIMEOUT_S", "300"))

SYSTEM_PROMPT = (
    "You are a helpful AI assistant with access to the Workunit project management "
    "platform via MCP tools. When asked to perform an action, you MUST call the "
    "appropriate tool — do not describe what you would do, actually call it. "
    "Use only the tools provided; do not invent tool names."
)

console = Console()


# ─── MCP Client ───────────────────────────────────────────────────────────────

OAUTH_TOKEN_URL   = os.environ.get("OAUTH_TOKEN_URL", "https://workunit.app/oauth/token")
OAUTH_CLIENT_ID   = os.environ.get("WORKUNIT_OAUTH_CLIENT_ID", "")


class MCPClient:
    """
    Minimal stateful MCP client over HTTP (streamable transport).
    Handles initialize handshake, tool calls, and transparent token refresh.
    """

    def __init__(self, token: str, refresh_token: str = ""):
        self.token           = token
        self.refresh_token   = refresh_token
        self.session         = None
        self._refresh_failed = False
        self._req_id       = 0

    def _headers(self) -> dict:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.token}",
        }
        if self.session:
            h["Mcp-Session-Id"] = self.session
        return h

    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def initialize(self) -> bool:
        """Perform MCP handshake, store session ID. Returns True on success."""
        payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "id": self._next_id(),
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "benchmark", "version": "2.0"},
            },
        }
        try:
            resp = requests.post(MCP_URL, json=payload, headers=self._headers(), timeout=MCP_CALL_TIMEOUT)
            if resp.status_code == 401 and self.refresh_token:
                # Token expired — get a new one and retry
                if self._do_refresh():
                    resp = requests.post(MCP_URL, json=payload, headers=self._headers(), timeout=MCP_CALL_TIMEOUT)
                else:
                    return False
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", "5"))
                console.print(f"  [yellow]Rate limited, waiting {wait}s...[/yellow]")
                time.sleep(wait)
                payload["id"] = self._next_id()
                resp = requests.post(MCP_URL, json=payload, headers=self._headers(), timeout=MCP_CALL_TIMEOUT)
            resp.raise_for_status()
            self.session = resp.headers.get("Mcp-Session-Id")
            return True
        except Exception as e:
            console.print(f"  [red]MCP init failed: {e}[/red]")
            return False

    def _do_refresh(self) -> bool:
        """Exchange refresh_token for a new access_token. Returns True on success."""
        if self._refresh_failed:
            return False  # Don't keep hammering after a confirmed failure
        try:
            resp = requests.post(
                OAUTH_TOKEN_URL,
                data={
                    "grant_type":    "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id":     OAUTH_CLIENT_ID,
                },
                timeout=10,
            )
            resp.raise_for_status()
            data               = resp.json()
            self.token         = data["access_token"]
            self.refresh_token = data.get("refresh_token", self.refresh_token)
            self.session       = None
            self._refresh_failed = False
            console.print("  [dim]Token refreshed[/dim]")
            return True
        except Exception as e:
            console.print(f"  [red]Token refresh failed: {e}[/red]")
            self._refresh_failed = True
            return False

    def call_tool(self, name: str, arguments: dict) -> str:
        """
        Execute a tool call against the MCP server.
        Transparently refreshes the token on 401 and retries once.
        Backs off on 429 rate-limit responses.
        Returns the result as a string (JSON or plain text).
        """
        for attempt in range(2):
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "id": self._next_id(),
                "params": {"name": name, "arguments": arguments},
            }
            try:
                resp = requests.post(MCP_URL, json=payload, headers=self._headers(), timeout=MCP_CALL_TIMEOUT)
                if resp.status_code == 401 and attempt == 0:
                    if self._do_refresh() and self.initialize():
                        continue
                    return json.dumps({"error": "unauthorized, refresh failed"})
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", "5"))
                    console.print(f"  [yellow]Rate limited on {name}, waiting {wait}s...[/yellow]")
                    time.sleep(wait)
                    payload["id"] = self._next_id()
                    resp = requests.post(MCP_URL, json=payload, headers=self._headers(), timeout=MCP_CALL_TIMEOUT)
                resp.raise_for_status()
                data = resp.json()
                if "error" in data:
                    return json.dumps({"error": data["error"]})
                content = data.get("result", {}).get("content", [])
                if content:
                    return content[0].get("text", "")
                return "{}"
            except Exception as e:
                return json.dumps({"error": str(e)})
        return json.dumps({"error": "tool call failed after token refresh"})


# ─── LM Studio helpers ────────────────────────────────────────────────────────

def list_models() -> list[dict]:
    """Return all LLMs from LM Studio (excludes embedding models)."""
    import urllib.request
    with urllib.request.urlopen(f"{LMSTUDIO_MGMT_URL}/api/v0/models") as resp:
        data = json.loads(resp.read())
    return [m for m in data["data"] if m.get("type") == "llm"]


# Minimum context length for all models. The full TOOLS list is ~4100 tokens;
# add system prompt, user message, multi-turn history, and response headroom.
MODEL_CONTEXT_LENGTH = 8192


def load_model(model_id: str, timeout: int = 600) -> str | None:
    """
    Explicitly load a model via POST /api/v1/models/load with a fixed context_length.
    Unloads any existing instances first to ensure we get the right context size.
    Returns the instance_id string on success, None on failure.
    """
    # Unload any existing instances of this model (they may be at the wrong context size)
    _unload_all_instances(model_id)

    try:
        resp = requests.post(
            f"{LMSTUDIO_MGMT_URL}/api/v1/models/load",
            json={
                "model": model_id,
                "context_length": MODEL_CONTEXT_LENGTH,
                "flash_attention": True,
                "echo_load_config": True,
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            instance_id = data.get("instance_id", model_id)
            ctx = data.get("load_config", {}).get("context_length", MODEL_CONTEXT_LENGTH)
            console.print(f"  [dim]Model loaded — instance: {instance_id}, ctx={ctx}[/dim]")
            return instance_id
        console.print(f"  [yellow]Load endpoint returned {resp.status_code}: {resp.text[:200]}[/yellow]")
        return None
    except Exception as e:
        console.print(f"  [red]Model load failed: {e}[/red]")
        return None


def _unload_all_instances(model_id: str):
    """Unload all loaded instances of a model (best-effort)."""
    try:
        resp = requests.get(f"{LMSTUDIO_MGMT_URL}/api/v1/models", timeout=10)
        if resp.status_code != 200:
            return
        for m in resp.json().get("models", []):
            if m.get("key") != model_id:
                continue
            for inst in m.get("loaded_instances", []):
                iid = inst.get("instance_id") or inst.get("id")
                if iid:
                    requests.post(
                        f"{LMSTUDIO_MGMT_URL}/api/v1/models/unload",
                        json={"instance_id": iid},
                        timeout=15,
                    )
    except Exception:
        pass


def unload_all_models():
    """Unload every loaded model instance in LM Studio. Called once at benchmark start
    to ensure a clean VRAM state — any model left over from a previous session would
    otherwise crowd out the benchmark models onto CPU, making timings meaningless."""
    try:
        resp = requests.get(f"{LMSTUDIO_MGMT_URL}/api/v1/models", timeout=10)
        if resp.status_code != 200:
            return
        unloaded = 0
        for m in resp.json().get("models", []):
            for inst in m.get("loaded_instances", []):
                iid = inst.get("instance_id") or inst.get("id")
                if iid:
                    requests.post(
                        f"{LMSTUDIO_MGMT_URL}/api/v1/models/unload",
                        json={"instance_id": iid},
                        timeout=15,
                    )
                    unloaded += 1
        if unloaded:
            console.print(f"[dim]Unloaded {unloaded} pre-existing model instance(s) from LM Studio[/dim]")
    except Exception:
        pass


def unload_model(instance_id: str):
    """Unload a specific model instance to free VRAM before loading the next one."""
    try:
        resp = requests.post(
            f"{LMSTUDIO_MGMT_URL}/api/v1/models/unload",
            json={"instance_id": instance_id},
            timeout=30,
        )
        if resp.status_code == 200:
            console.print(f"  [dim]Model unloaded[/dim]")
    except Exception:
        pass  # Best-effort — don't abort the run if unload fails


# ─── MCP Tool schemas (used as `tools` in chat completions) ───────────────────
#
# These match the real Workunit MCP server's inputSchema exactly (19 tools).
# Excluded: delete_asset (destructive), directory (complex admin multi-action).
# Descriptions are kept concise — models need to know what to call, not full docs.

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
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_authenticated_user",
            "description": "Get details about the authenticated user",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False}
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
                    "name":           {"type": "string", "description": "Project name (max 255 chars)"},
                    "description":    {"type": "string", "description": "Project description"},
                    "status":         {"type": "string", "description": "planning|active|on_hold|completed|archived (default: planning)"},
                    "tags":           {"type": "array", "items": {"type": "string"}},
                    "repo_url":       {"type": "string", "description": "Repository URL"},
                    "default_branch": {"type": "string", "description": "Default branch (e.g. main)"},
                    "organization_id":{"type": "string", "description": "Org ID (defaults to user's org)"},
                    "owner_id":       {"type": "string", "description": "Owner user ID (defaults to creator)"}
                },
                "required": ["name"],
                "additionalProperties": False
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
                    "id":                {"type": "string"},
                    "include_stats":     {"type": "boolean", "description": "Include workunit/asset/checkin counts"},
                    "include_assets":    {"type": "boolean"},
                    "include_checkins":  {"type": "boolean"},
                    "include_workunits": {"type": "boolean"}
                },
                "required": ["id"],
                "additionalProperties": False
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
                    "organization_id": {"type": "string", "description": "Org ID to list projects from"},
                    "owner_id":        {"type": "string", "description": "Filter by owner user ID"},
                    "status":          {"type": "string", "description": "Filter: planning|active|on_hold|completed|archived"},
                    "tags":            {"type": "array", "items": {"type": "string"}, "description": "Filter by tags (any match)"},
                    "sort_by":         {"type": "string", "description": "created_at|updated_at|name (default: created_at)"},
                    "sort_order":      {"type": "string", "description": "asc|desc (default: desc)"},
                    "page_size":       {"type": "integer", "description": "Results per page (default: 50, max: 100)"},
                    "page_number":     {"type": "integer", "description": "Page number (1-based, default: 1)"}
                },
                "required": ["organization_id"],
                "additionalProperties": False
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
                        "required": ["paths"],
                        "additionalProperties": False
                    },
                    "name":           {"type": "string"},
                    "description":    {"type": "string"},
                    "status":         {"type": "string", "description": "planning|active|on_hold|completed|archived"},
                    "tags":           {"type": "array", "items": {"type": "string"}},
                    "repo_url":       {"type": "string"},
                    "default_branch": {"type": "string"},
                    "owner_id":       {"type": "string"}
                },
                "required": ["id", "update_mask"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "remove_project",
            "description": "Removes a project. action='archive' preserves data (can be restored), action='delete' is permanent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id":     {"type": "string"},
                    "action": {"type": "string", "description": "archive|delete"}
                },
                "required": ["id", "action"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_workunit",
            "description": "Create a workunit with problem statement and success criteria. Can link initial assets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name":               {"type": "string", "description": "Workunit name (max 255 chars)"},
                    "problem_statement":  {"type": "string", "description": "Problem statement (max 1000 chars)"},
                    "success_criteria":   {"type": "string", "description": "Success criteria (max 1000 chars)"},
                    "description":        {"type": "string", "description": "Description (max 2000 chars)"},
                    "project_id":         {"type": "string"},
                    "priority":           {"type": "string", "description": "low|normal|high|urgent"},
                    "status":             {"type": "string", "description": "draft|active|paused|completed|archived"},
                    "tags":               {"type": "array", "items": {"type": "string"}},
                    "due_date":           {"type": "string", "description": "Due date (ISO 8601)"},
                    "organization_id":    {"type": "string"},
                    "owner_id":           {"type": "string"},
                    "initial_assets": {
                        "type": "array",
                        "description": "Assets to link at creation",
                        "items": {
                            "type": "object",
                            "properties": {
                                "asset_id":         {"type": "string"},
                                "relationship_type":{"type": "string", "description": "requires|affects|involves|references|owns|depends_on"},
                                "notes":            {"type": "string"}
                            },
                            "required": ["asset_id", "relationship_type"],
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["name", "problem_statement", "success_criteria"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_workunit",
            "description": "Get workunit details with optional tasks, assets, and structured context atoms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id":                       {"type": "string"},
                    "include_tasks":            {"type": "boolean"},
                    "include_ai_context":       {"type": "boolean"},
                    "include_assets":           {"type": "boolean"},
                    "include_task_comments":    {"type": "boolean"},
                    "include_task_context":     {"type": "boolean"},
                    "include_task_dependencies":{"type": "boolean"},
                    "include_task_time_logs":   {"type": "boolean"}
                },
                "required": ["id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_workunit",
            "description": "Update workunit fields via update_mask. Status=completed/archived triggers special workflows.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "update_mask": {
                        "type": "object",
                        "properties": {"paths": {"type": "array", "items": {"type": "string"}}},
                        "required": ["paths"],
                        "additionalProperties": False
                    },
                    "name":               {"type": "string"},
                    "description":        {"type": "string"},
                    "problem_statement":  {"type": "string"},
                    "success_criteria":   {"type": "string"},
                    "priority":           {"type": "string", "description": "low|normal|high|urgent"},
                    "status":             {"type": "string", "description": "draft|active|paused|completed|archived"},
                    "tags":               {"type": "array", "items": {"type": "string"}},
                    "completion_notes":   {"type": "string", "description": "Required when status=completed (max 2000 chars)"},
                    "archive_reason":     {"type": "string", "description": "Used when status=archived (max 1000 chars)"},
                    "due_date":           {"type": "string"},
                    "owner_id":           {"type": "string"},
                    "project_id":         {"type": "string"}
                },
                "required": ["id", "update_mask"],
                "additionalProperties": False
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
                    "workunit_id":    {"type": "string"},
                    "title":          {"type": "string", "description": "Task title (max 255 chars)"},
                    "description":    {"type": "string"},
                    "status":         {"type": "string", "description": "todo|in_progress|done|blocked|wont_do (default: todo)"},
                    "priority":       {"type": "string", "description": "low|normal|high (default: normal)"},
                    "tags":           {"type": "array", "items": {"type": "string"}},
                    "depends_on":     {"type": "array", "items": {"type": "string"}, "description": "Task IDs this depends on"},
                    "assigned_to":    {"type": "string", "description": "User ID to assign"},
                    "due_date":       {"type": "string", "description": "Due date (ISO 8601)"},
                    "estimated_hours":{"type": "number"},
                    "position":       {"type": "integer", "description": "Position in list (0 = append)"}
                },
                "required": ["workunit_id", "title"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_task",
            "description": "Retrieve detailed information about a specific task, including status, assignee, dependencies, and optionally comments and time logs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id":                   {"type": "string"},
                    "include_comments":     {"type": "boolean"},
                    "include_dependencies": {"type": "boolean"},
                    "include_time_logs":    {"type": "boolean"}
                },
                "required": ["id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "Update task fields via update_mask. Supports status, priority, assignment, due_date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "update_mask": {
                        "type": "object",
                        "properties": {"paths": {"type": "array", "items": {"type": "string"}}},
                        "required": ["paths"],
                        "additionalProperties": False
                    },
                    "title":          {"type": "string"},
                    "description":    {"type": "string"},
                    "status":         {"type": "string", "description": "todo|in_progress|done|blocked|wont_do"},
                    "priority":       {"type": "string", "description": "low|normal|high"},
                    "tags":           {"type": "array", "items": {"type": "string"}},
                    "assigned_to":    {"type": "string", "description": "User ID (empty string to unassign)"},
                    "due_date":       {"type": "string"},
                    "estimated_hours":{"type": "number"}
                },
                "required": ["id", "update_mask"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_context",
            "description": "Save a structured context atom to a workunit's trail-of-thought. Use this to preserve decisions, insights, questions, attempts, and progress across AI sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "workunit_id":      {"type": "string"},
                    "atom_type":        {"type": "string", "description": "decision|insight|question|attempt|progress"},
                    "title":            {"type": "string", "description": "Short summary (max 120 chars)"},
                    "content":          {"type": "string", "description": "Detailed description (max 10000 chars)"},
                    "importance":       {"type": "string", "description": "critical|high|normal|low (default: normal)"},
                    "strength":         {"type": "string", "description": "hard (locked)|soft (revisitable) (default: soft)"},
                    "tags":             {"type": "array", "items": {"type": "string"}},
                    "author_model":     {"type": "string", "description": "LLM model name or 'human'"},
                    "confidence":       {"type": "string", "description": "high|medium|low"},
                    "supersedes_id":    {"type": "string", "description": "ID of atom this replaces"},
                    "artifacts":        {"type": "array", "items": {"type": "string"}, "description": "File paths, PR links, commit refs"},
                    "related_asset_ids":{"type": "array", "items": {"type": "string"}},
                    "related_task_ids": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["workunit_id", "atom_type", "title", "content"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Search workunits, tasks, and assets. Filter by result_types. Use to find IDs for linking.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query":           {"type": "string"},
                    "result_types":    {"type": "array", "items": {"type": "string"}, "description": "Filter: ['workunit', 'task', 'asset']. Omit for all types."},
                    "organization_id": {"type": "string"},
                    "page_size":       {"type": "integer", "description": "Max results (default: 50, max: 50)"},
                    "page_number":     {"type": "integer"},
                    "directory_id":    {"type": "string", "description": "Filter assets by directory ID"},
                    "root_only":       {"type": "boolean", "description": "If true, only return root-level assets"}
                },
                "required": ["query"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_asset",
            "description": "Creates a new asset. Asset types: product (deliverables), people (individuals/teams), knowledge (docs/training), system (infrastructure/processes).",
            "parameters": {
                "type": "object",
                "properties": {
                    "asset_type":         {"type": "string", "description": "product|people|knowledge|system"},
                    "name":               {"type": "string", "description": "Asset name (max 255 chars)"},
                    "description":        {"type": "string"},
                    "status":             {"type": "string"},
                    "tags":               {"type": "array", "items": {"type": "string"}},
                    "organization_id":    {"type": "string"},
                    "category":           {"type": "string", "description": "Product: hardware|software|service|subscription|physical_good. Knowledge: documentation|training|standards|research|template|playbook. System: manufacturing|logistics|business_process|infrastructure|quality_control"},
                    "lifecycle_stage":    {"type": "string", "description": "Product only: concept|development|production|maintenance|discontinued"},
                    "format":             {"type": "string", "description": "Knowledge only: document|video|course|database|wiki|spreadsheet"},
                    "content":            {"type": "string", "description": "Knowledge only: inline markdown (max 500KB)"},
                    "content_url":        {"type": "string", "description": "Knowledge only: URL to external content"},
                    "criticality":        {"type": "string", "description": "System only: standard|important|critical"},
                    "location":           {"type": "string", "description": "System only: physical/logical location"},
                    "asset_subtype":      {"type": "string", "description": "People only: individual|team|department|contractor"},
                    "availability_status":{"type": "string", "description": "People only: available|busy|off|partially_available"},
                    "workload_percent":   {"type": ["null", "integer"], "description": "People only: 0-100"},
                    "user_id":            {"type": "string", "description": "People only: user ID for individuals"},
                    "lead_user_id":       {"type": "string", "description": "People only: team lead user ID"},
                    "version":            {"type": "string", "description": "Knowledge only: version ID"},
                    "directory_id":       {"type": "string", "description": "Directory to place asset in"}
                },
                "required": ["asset_type", "name"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_asset",
            "description": "Get asset details by ID. Includes type-specific fields by default.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id":                          {"type": "string"},
                    "include_type_specific_fields": {"type": ["null", "boolean"], "description": "Include type-specific fields (default: true)"}
                },
                "required": ["id"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_asset",
            "description": "Updates an existing asset. Requires asset_type and update_mask.paths specifying which fields to update.",
            "parameters": {
                "type": "object",
                "properties": {
                    "id":          {"type": "string"},
                    "asset_type":  {"type": "string", "description": "product|people|knowledge|system"},
                    "update_mask": {
                        "type": "object",
                        "properties": {"paths": {"type": "array", "items": {"type": "string"}}},
                        "required": ["paths"],
                        "additionalProperties": False
                    },
                    "name":               {"type": ["null", "string"]},
                    "description":        {"type": ["null", "string"]},
                    "status":             {"type": ["null", "string"]},
                    "tags":               {"type": "array", "items": {"type": "string"}},
                    "category":           {"type": ["null", "string"]},
                    "lifecycle_stage":    {"type": ["null", "string"], "description": "Product only"},
                    "format":             {"type": ["null", "string"], "description": "Knowledge only"},
                    "content":            {"type": ["null", "string"], "description": "Knowledge only"},
                    "content_url":        {"type": ["null", "string"], "description": "Knowledge only"},
                    "criticality":        {"type": ["null", "string"], "description": "System only"},
                    "location":           {"type": ["null", "string"], "description": "System only"},
                    "asset_subtype":      {"type": ["null", "string"], "description": "People only"},
                    "availability_status":{"type": ["null", "string"], "description": "People only"},
                    "workload_percent":   {"type": ["null", "integer"], "description": "People only"},
                    "directory_id":       {"type": ["null", "string"], "description": "Move to directory (empty string for root)"}
                },
                "required": ["id", "asset_type", "update_mask"],
                "additionalProperties": False
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "project_asset_link",
            "description": "Manages asset-project relationships. action='link' associates an asset with a project, action='unlink' removes it.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_id": {"type": "string"},
                    "asset_id":   {"type": "string"},
                    "action":     {"type": "string", "description": "link|unlink"},
                    "notes":      {"type": "string", "description": "Notes about why this asset is linked (link action only)"}
                },
                "required": ["project_id", "asset_id", "action"],
                "additionalProperties": False
            }
        }
    }
]


# ─── Validation ────────────────────────────────────────────────────────────────

def validate(tool_calls: list[dict], task: dict) -> tuple[bool, float, list[str]]:
    """
    Returns (passed, score 0.0-1.0, details).
    tool_calls is the full list of {"name": str, "arguments": dict} across all turns.
    """
    validation = task.get("validation", {})
    val_type   = validation.get("type", "tool_call_match")
    details    = []

    if not tool_calls:
        return False, 0.0, ["No tool call emitted — model responded with text only"]

    # ── Single tool call ──────────────────────────────────────────────────────
    if val_type == "tool_call_match":
        expected_tool = task.get("expected_tool")
        actual_tool   = tool_calls[0]["name"]

        if actual_tool != expected_tool:
            return False, 0.0, [f"Wrong tool: called '{actual_tool}', expected '{expected_tool}'"]

        args  = tool_calls[0].get("arguments", {})
        score = 1.0

        for param in validation.get("required_params", []):
            if param not in args:
                details.append(f"Missing required param: '{param}'")
                score -= 0.25

        for param, expected_val in validation.get("param_exact", {}).items():
            actual_val = args.get(param)
            if actual_val != expected_val:
                details.append(f"'{param}': expected {expected_val!r}, got {actual_val!r}")
                score -= 0.15

        for param in validation.get("param_present", []):
            if param not in args or args[param] is None or args[param] == "":
                details.append(f"'{param}' should be present but is missing/empty")
                score -= 0.10

        paths_required = validation.get("update_mask_must_contain", [])
        if paths_required:
            update_mask  = args.get("update_mask")
            actual_paths = update_mask.get("paths", []) if isinstance(update_mask, dict) else []
            for p in paths_required:
                if p not in actual_paths:
                    details.append(f"update_mask.paths missing '{p}'")
                    score -= 0.10

        score  = max(0.0, min(1.0, score))
        passed = score >= 0.6 and not any("required" in d for d in details)
        if not details:
            details = ["All checks passed"]
        return passed, score, details

    # ── Multiple calls of same tool ───────────────────────────────────────────
    elif val_type == "multi_tool_call":
        expected_tool = validation.get("tool")
        matching      = [tc for tc in tool_calls if tc["name"] == expected_tool]
        min_count     = validation.get("call_count", 1)

        if len(matching) < min_count:
            return False, len(matching) / min_count * 0.5, [
                f"Expected {min_count}× {expected_tool}, got {len(matching)}"
            ]

        score = 1.0
        for tc in matching:
            for param in validation.get("each_must_have", []):
                if param not in tc.get("arguments", {}):
                    details.append(f"Call missing required param '{param}'")
                    score -= 0.1

        titles_required = validation.get("titles_must_include", [])
        found_titles    = [tc.get("arguments", {}).get("title", "") for tc in matching]
        for t in titles_required:
            if not any(t.lower() in ft.lower() for ft in found_titles):
                details.append(f"Expected task title not found: '{t}'")
                score -= 0.15

        score  = max(0.0, min(1.0, score))
        passed = score >= 0.7
        if not details:
            details = [f"{len(matching)}/{min_count} calls made correctly"]
        return passed, score, details

    # ── Ordered multi-tool sequence ───────────────────────────────────────────
    elif val_type in ("multi_tool_sequence", "reasoning_chain"):
        steps       = validation.get("steps", [])
        step_scores = []

        for i, step in enumerate(steps):
            expected_tool = step.get("tool")
            matching      = [tc for tc in tool_calls if tc["name"] == expected_tool]

            if not matching:
                step_scores.append(0.0)
                details.append(f"Step {i+1} ({expected_tool}): not called")
                continue

            tc         = matching[0]
            args       = tc.get("arguments", {})
            step_score = 1.0

            for param in step.get("must_have_params", []):
                if param not in args:
                    details.append(f"Step {i+1} ({expected_tool}): missing '{param}'")
                    step_score -= 0.25

            for param, val in step.get("param_exact", {}).items():
                if args.get(param) != val:
                    details.append(f"Step {i+1} ({expected_tool}): '{param}'={args.get(param)!r} (want {val!r})")
                    step_score -= 0.2

            for param in step.get("param_present", []):
                if param not in args:
                    details.append(f"Step {i+1} ({expected_tool}): '{param}' missing")
                    step_score -= 0.15

            step_score = max(0.0, step_score)
            step_scores.append(step_score)
            if step_score >= 0.8:
                details.append(f"Step {i+1} ({expected_tool}): ✓")

        score  = sum(step_scores) / len(steps) if steps else 0.0
        passed = score >= 0.75
        return passed, score, details

    return False, 0.0, ["Unknown validation type"]


# ─── Agentic task execution ────────────────────────────────────────────────────

def run_task(client: OpenAI, mcp: MCPClient, model_id: str, task: dict) -> dict:
    """
    Run one task with a full agentic loop:
    - Model calls tool → we execute it against MCP → feed result back → repeat
    - Stops when model sends a message with no tool calls, or TASK_TIMEOUT_S elapses
    - Result contains every tool call made across all turns for validation
    """
    prompt = task["prompt"]

    start      = time.time()
    all_calls  = []   # every tool call across all turns, for validation
    turns      = 0
    timed_out  = False
    error      = None

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": prompt},
    ]

    try:
        while True:
            if time.time() - start > TASK_TIMEOUT_S:
                timed_out = True
                break

            response = client.chat.completions.create(
                model=model_id,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0.0,
                max_tokens=4096,
                timeout=TASK_TIMEOUT_S,
            )

            msg   = response.choices[0].message
            turns += 1

            if not msg.tool_calls:
                # Model is done — no more tool calls
                break

            # Parse all tool calls in this turn
            turn_calls = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {"_raw": tc.function.arguments}
                turn_calls.append({
                    "id":        tc.id,
                    "name":      tc.function.name,
                    "arguments": args,
                })
                all_calls.append({"name": tc.function.name, "arguments": args})

            # Append assistant message with tool calls
            messages.append({
                "role":       "assistant",
                "content":    msg.content,
                "tool_calls": [
                    {
                        "id":       tc["id"],
                        "type":     "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])},
                    }
                    for tc in turn_calls
                ],
            })

            # Execute each tool call against MCP and append results
            for tc in turn_calls:
                result = mcp.call_tool(tc["name"], tc["arguments"])
                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc["id"],
                    "content":      result,
                })

            # Early exit: stop looping as soon as the task is already passing.
            # No need to wait for the model to stop on its own or hit the timeout.
            early_passed, _, _ = validate(all_calls, task)
            if early_passed:
                break

    except Exception as e:
        error = str(e)
        if "n_keep" in error and "n_ctx" in error:
            error = f"Context overflow: model's n_ctx is too small for the full TOOLS list. Increase context length in LM Studio to ≥8192. ({error})"

    elapsed = round(time.time() - start, 2)
    passed, score, details = validate(all_calls, task)

    if timed_out:
        details.insert(0, f"Task timed out after {TASK_TIMEOUT_S}s ({turns} turns completed)")

    return {
        "task_id":    task["id"],
        "task_name":  task["name"],
        "passed":     passed,
        "score":      score,
        "details":    details,
        "tool_calls": all_calls,
        "turns":      turns,
        "elapsed_s":  elapsed,
        "timed_out":  timed_out,
        "error":      error,
    }


# ─── Level runner ──────────────────────────────────────────────────────────────

def run_level(client: OpenAI, mcp: MCPClient, model_id: str, level: int) -> dict:
    """Run all tasks for a level. Returns summary + per-task results."""
    task_file   = TASK_FILES[level]
    level_names = {0: "Explicit", 1: "Natural Language", 2: "Reasoning"}

    with open(task_file) as f:
        task_data = json.load(f)
    tasks = task_data["tasks"]

    console.print(f"\n  [bold]Level {level} — {level_names[level]}[/bold] ({len(tasks)} tasks)")

    results = []
    for task in tasks:
        with console.status(f"    [dim]{task['id']}: {task['name']}[/dim]"):
            result = run_task(client, mcp, model_id, task)

        icon      = "✅" if result["passed"] else "❌"
        score_pct = f"{result['score']:.0%}"
        turns_str = f"{result['turns']}t" if result['turns'] > 1 else ""
        timeout_str = " ⏱" if result.get("timed_out") else ""
        console.print(
            f"    {icon} {task['id']} [{score_pct}] {task['name']} "
            f"({result['elapsed_s']}s{' ' + turns_str if turns_str else ''}{timeout_str})"
        )
        if not result["passed"] or result["error"]:
            for d in result["details"][:2]:
                console.print(f"       [dim]{d}[/dim]")

        results.append(result)

    total    = len(results)
    passed   = sum(1 for r in results if r["passed"])
    avg_score = sum(r["score"] for r in results) / total if total else 0.0

    return {
        "level": level,
        "summary": {
            "total":     total,
            "passed":    passed,
            "pass_rate": round(passed / total, 3),
            "avg_score": round(avg_score, 3),
        },
        "results": results,
    }


# ─── Model runner ──────────────────────────────────────────────────────────────

def reset_benchmark_env(mcp: "MCPClient"):
    """Wipe all benchmark org data via MCP between model runs for a clean slate.

    Steps:
      1. get_authenticated_user → extract org_id
      2. list_projects → remove_project(action=delete) for each
      3. search for orphaned assets → delete_asset for each
      4. list directories → delete(recursive=True) for each
    """
    # 1. Get org_id
    user_raw = mcp.call_tool("get_authenticated_user", {})
    try:
        user_data = json.loads(user_raw)
        orgs = user_data.get("organizations", [])
        org_id = orgs[0]["id"] if orgs else user_data.get("organization_id", "")
    except (json.JSONDecodeError, KeyError, IndexError):
        console.print("  [yellow]Could not determine org_id from user data, cleanup may be incomplete[/yellow]")
        org_id = ""

    if not org_id:
        console.print("  [yellow]No org_id found, skipping cleanup[/yellow]")
        return

    def _parse_mcp(raw: str, key: str, label: str) -> list:
        """Parse an MCP call_tool response, warn on errors, return list."""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            console.print(f"  [yellow]Cleanup: {label} returned invalid JSON[/yellow]")
            return []
        if "error" in data:
            console.print(f"  [yellow]Cleanup: {label} failed: {data['error']}[/yellow]")
            return []
        return data.get(key, [])

    # 2. Delete all projects (cascades to workunits/tasks)
    projects_raw = mcp.call_tool("list_projects", {"organization_id": org_id, "page_size": 100})
    projects = _parse_mcp(projects_raw, "projects", "list_projects")

    for proj in projects:
        pid = proj.get("id", "")
        if pid:
            mcp.call_tool("remove_project", {"id": pid, "action": "delete"})

    # 3. Delete orphaned assets
    assets_raw = mcp.call_tool("search", {"query": " ", "result_types": ["asset"], "page_size": 50})
    assets = _parse_mcp(assets_raw, "results", "search assets")

    for asset in assets:
        aid = asset.get("id", "")
        if aid:
            mcp.call_tool("delete_asset", {"id": aid})

    # 4. Delete directories
    dirs_raw = mcp.call_tool("directory", {"action": "list", "organization_id": org_id})
    directories = _parse_mcp(dirs_raw, "directories", "list directories")

    for d in directories:
        did = d.get("id", "")
        if did:
            mcp.call_tool("directory", {"action": "delete", "id": did, "recursive": True})

    deleted = len(projects) + len(assets) + len(directories)
    if deleted:
        console.print(f"  [dim]Cleanup: deleted {len(projects)} projects, {len(assets)} assets, {len(directories)} directories[/dim]")
    else:
        console.print("  [dim]Cleanup: org already clean[/dim]")


def run_model(model_id: str, levels: list[int], tool_trained: bool, token: str,
              refresh_token: str = "", force: bool = False, no_git: bool = False) -> dict:
    """
    Run all levels for one model.

    Skips levels that already have a result file unless force=True.
    Each level is wrapped in its own try/except so a crash in one level
    doesn't abort the remaining levels or models.
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
    mcp    = MCPClient(token=token, refresh_token=refresh_token)

    # Initialize MCP session once — used for both cleanup and task execution
    if not mcp.initialize():
        console.print("  [red]Could not connect to MCP server, skipping model[/red]")
        return {}

    # Reset org data before each model so tests don't bleed into each other
    reset_benchmark_env(mcp)

    # Load model with explicit context length so the full TOOLS list fits
    console.print(f"  [dim]Loading model (ctx={MODEL_CONTEXT_LENGTH})...[/dim]")
    instance_id = load_model(model_id)
    if not instance_id:
        console.print(f"  [red]Model failed to load, skipping[/red]")
        return {}

    model_results = {
        "model":        model_id,
        "tool_trained": tool_trained,
        "timestamp":    datetime.now().isoformat(),
        "levels":       {},
    }

    try:
        for level in pending_levels:
            try:
                level_result = run_level(client, mcp, model_id, level)
                model_results["levels"][level] = level_result

                s = level_result["summary"]
                console.print(
                    f"  → Level {level}: {s['passed']}/{s['total']} passed "
                    f"({s['pass_rate']:.0%} pass rate, {s['avg_score']:.0%} avg score)"
                )

                save_result(model_id, level, level_result, tool_trained)
                if not no_git:
                    git_commit(model_id, level)

            except Exception as e:
                console.print(f"  [red]Level {level} crashed: {e}[/red]")
                console.print(f"  [dim]Continuing to next level...[/dim]")
    finally:
        unload_model(instance_id)

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
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    out  = RESULTS_DIR / f"level{level}_{safe}_{ts}.json"

    output = {
        "level":       level,
        "model":       model_id,
        "tool_trained": tool_trained,
        "timestamp":   datetime.now().isoformat(),
        **level_result,
    }
    with open(out, "w") as f:
        json.dump(output, f, indent=2)

    console.print(f"  [dim]Saved → {out.name}[/dim]")


def git_commit(model_id: str, level: int):
    try:
        subprocess.run(
            ["git", "add", "benchmark/results/"],
            cwd=str(PROJECT_ROOT), check=True, capture_output=True
        )
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(PROJECT_ROOT), capture_output=True
        )
        if result.returncode != 0:
            subprocess.run(
                ["git", "commit", "-m",
                 f"results: level{level} — {model_id}\n\n[benchmark auto-commit]"],
                cwd=str(PROJECT_ROOT), check=True, capture_output=True
            )
            console.print(f"  [dim]Committed to git[/dim]")
    except subprocess.CalledProcessError:
        pass


# ─── CLI ───────────────────────────────────────────────────────────────────────

def load_models_file(path: str) -> list[tuple[str, bool]]:
    models = []
    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts      = stripped.split("#", 1)
            model_id   = parts[0].strip()
            comment    = parts[1].strip() if len(parts) > 1 else ""
            tool_trained = "no tool training" not in comment.lower()
            models.append((model_id, tool_trained))
    return models


def main():
    parser = argparse.ArgumentParser(
        description="Workunit MCP Benchmark — agentic runner via LM Studio API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--model", "-m", help="Single model ID")
    group.add_argument("--models", help="Path to models.txt")
    group.add_argument("--list-models", action="store_true", help="List LM Studio models and exit")
    group.add_argument(
        "--cleanup-only", action="store_true",
        help="Reset the org (delete all projects/assets/directories) and exit",
    )

    parser.add_argument("--level", type=int, choices=[0, 1, 2], help="Run only this level")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    parser.add_argument("--no-git", action="store_true", help="Skip git commits")
    parser.add_argument(
        "--force", action="store_true",
        help="Re-run levels that already have result files (default: skip completed levels)",
    )
    parser.add_argument(
        "--token",
        help="Workunit MCP bearer token (or set WORKUNIT_TOKEN env var)",
        default=os.environ.get("WORKUNIT_TOKEN", ""),
    )
    parser.add_argument(
        "--refresh-token",
        help="OAuth refresh token for automatic renewal (or set WORKUNIT_REFRESH_TOKEN env var)",
        default=os.environ.get("WORKUNIT_REFRESH_TOKEN", ""),
    )
    parser.add_argument(
        "--local", action="store_true",
        help="Use local dev stack (MCP at localhost:9000, OAuth at localhost:3000)",
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip the destructive data warning prompt",
    )
    args = parser.parse_args()

    # --local overrides endpoints to dev stack
    if args.local:
        global MCP_URL, OAUTH_TOKEN_URL
        MCP_URL        = "http://localhost:9000/mcp"
        OAUTH_TOKEN_URL = "http://localhost:3000/oauth/token"

    if args.list_models:
        models = list_models()
        table  = Table(title="LM Studio Models", show_header=True)
        table.add_column("Key")
        table.add_column("Tool-trained", justify="center")
        table.add_column("State")
        for m in models:
            tool = "✅" if "tool_use" in m.get("capabilities", []) else "❌"
            table.add_row(m["id"], tool, m.get("state", "?"))
        console.print(table)
        return

    if not args.token:
        console.print("[red]Error: Workunit bearer token required.[/red]")
        console.print("Pass via --token or set WORKUNIT_TOKEN env var.")
        console.print("\nGenerate one at: https://workunit.app/settings/api")
        sys.exit(1)

    # --cleanup-only: reset the org and exit
    if args.cleanup_only:
        if args.dry_run:
            console.print("[dim]--dry-run: would delete all projects, assets, and directories in your org[/dim]")
            return
        if not args.yes:
            console.print("[bold red]WARNING: This will delete ALL projects, workunits, assets, and directories in your org.[/bold red]")
            console.print("Use a dedicated Workunit account for benchmarking.\n")
            confirm = input("Type 'yes' to continue: ")
            if confirm.strip().lower() != "yes":
                console.print("Aborted.")
                return
        mcp = MCPClient(token=args.token, refresh_token=args.refresh_token)
        if not mcp.initialize():
            console.print("[red]Could not connect to MCP server[/red]")
            sys.exit(1)
        reset_benchmark_env(mcp)
        console.print("[green]Cleanup complete.[/green]")
        return

    # Destructive data warning before benchmark runs
    if not args.yes:
        console.print("[bold yellow]WARNING: The benchmark deletes ALL projects, workunits, assets, and directories[/bold yellow]")
        console.print("[bold yellow]in your org between each model run. Use a dedicated Workunit account.[/bold yellow]\n")
        confirm = input("Type 'yes' to continue (or use --yes to skip): ")
        if confirm.strip().lower() != "yes":
            console.print("Aborted.")
            return

    levels = [args.level] if args.level is not None else [0, 1, 2]

    if args.model:
        default_models_file = BENCHMARK_DIR / "models.txt"
        tool_trained = True
        if default_models_file.exists():
            for mid, tt in load_models_file(str(default_models_file)):
                if mid == args.model:
                    tool_trained = tt
                    break
        model_list = [(args.model, tool_trained)]
    elif args.models:
        model_list = load_models_file(args.models)
    else:
        parser.error("Provide --model, --models, or --list-models")

    if args.dry_run:
        # Show which model+level combos would actually run vs skip
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
        lines.append(f"\nTask timeout: {TASK_TIMEOUT_S}s per task")
        lines.append(f"Tasks per level: L0=11, L1=10, L2=7")

        console.print(Panel("\n".join(lines), title="Dry Run Plan"))
        return

    console.print(Panel(
        f"[bold cyan]Workunit MCP Benchmark — Agentic[/bold cyan]\n\n"
        f"Models: {len(model_list)}\n"
        f"Levels: {levels}\n"
        f"Task timeout: {TASK_TIMEOUT_S}s\n"
        f"Force re-run: {'yes' if args.force else 'no (skipping completed levels)'}\n"
        f"LM Studio: {LMSTUDIO_BASE_URL}\n"
        f"MCP: {MCP_URL}",
        title="Starting Run"
    ))

    unload_all_models()

    start = time.time()
    failed_models = []
    for i, (model_id, tool_trained) in enumerate(model_list, 1):
        console.print(f"\n[dim]── Model {i}/{len(model_list)} ──────────────────────────────[/dim]")
        try:
            run_model(model_id, levels, tool_trained, args.token, args.refresh_token,
                      args.force, args.no_git)
        except Exception as e:
            console.print(f"[red]Model {model_id} crashed unexpectedly: {e}[/red]")
            console.print("[dim]Continuing to next model...[/dim]")
            failed_models.append(model_id)

    elapsed = time.time() - start
    console.print(f"\n[bold green]Run complete![/bold green] {elapsed/60:.1f} minutes total")

    if failed_models:
        console.print(f"\n[yellow]Models that crashed (can be re-run individually):[/yellow]")
        for m in failed_models:
            console.print(f"  python runner_v2_agentic.py --model {m} --token $WORKUNIT_TOKEN --yes")

    console.print("\n[dim]To generate the aggregated report:[/dim]")
    console.print(f"  python {Path(__file__).parent / 'aggregate_results.py'}")


if __name__ == "__main__":
    main()

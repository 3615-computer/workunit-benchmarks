# Workunit MCP Tool Calling Benchmark

**Can your local model actually use MCP tools?**

This benchmark evaluates how well local LLMs can interact with the [Workunit](https://workunit.app) platform via its MCP server. It tests real-world tool calling across three difficulty levels — from "I'll hand you everything" to "figure it out yourself."

All three levels run through LM Studio's OpenAI-compatible API. No OpenCode, no manual steps. Models are switched automatically — LM Studio unloads the current model and loads the next one when the `model` field changes in a request. GPU offload to RAM is handled automatically.

---

## Three Difficulty Levels

### Level 0 — Explicit

You're told exactly which tool to call and with what parameters. Tests whether the model can emit a valid, well-formed tool call at all.

> *"Call `create_workunit` with name='Hello World', problem_statement='...', success_criteria='...', priority='normal'"*

### Level 1 — Natural Language

A human-style request with the key information present but not structured. The model must identify the right tool and map the description to parameter names.

> *"Create a workunit called 'Fix Login Page Bug'. The problem is users can't log in with special characters in their password. We'll know it's done when all character types work and there are regression tests. High priority."*

### Level 2 — Reasoning

High-level goal. No tool names. No parameter hints. The model must figure out the sequence, chain IDs across calls, and make decisions about structure.

> *"End of sprint. Mark all todo tasks done, save a summary of what was accomplished, and complete the workunit."*

---

## Reproducing Results

The published results were generated against a local Workunit dev stack. You can reproduce them against the production `workunit.app` MCP server or your own local instance.

### Prerequisites

1. [LM Studio](https://lmstudio.ai/) running with local server enabled (default: `http://localhost:1234`)
2. Python 3.10+ with dependencies: `pip install openai rich requests`

### Option A: Against workunit.app (recommended)

This is the easiest way to run the benchmark — no backend setup required.

1. Sign up at [workunit.app](https://workunit.app) (free). **Use a dedicated account** (see data warning below).
2. Get your MCP tokens using the MCP Inspector:
   ```bash
   bunx @modelcontextprotocol/inspector@latest
   ```
   Connect to `https://workunit.app/mcp`, complete the OAuth flow, and copy the `access_token` and `refresh_token` from the inspector UI.
3. Run:
   ```bash
   export WORKUNIT_TOKEN=your_access_token
   export WORKUNIT_REFRESH_TOKEN=your_refresh_token

   # Agentic run (real MCP tool execution)
   python scripts/runner_v2_agentic.py --models models.txt

   # Single-shot run (no MCP needed, validates tool call format only)
   python scripts/runner_v1_singleshot.py --models models.txt
   ```

### Option B: Against a local Workunit dev stack

If you have the Workunit backend running locally (MCP at `localhost:9000`, OAuth at `localhost:3000`):

```bash
export WORKUNIT_TOKEN=your_local_token
python scripts/runner_v2_agentic.py --models models.txt --local
```

The `--local` flag overrides `MCP_URL` to `http://localhost:9000/mcp` and `OAUTH_TOKEN_URL` to `http://localhost:3000/oauth/token`.

### Data Warning

The agentic runner (v2) deletes **ALL projects, workunits, assets, and directories** in your org between each model run to prevent data bleed. If you use your main account, **you will lose all your data**. Create a separate free account just for benchmarking. The runner will prompt for confirmation before starting unless you pass `--yes`.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKUNIT_TOKEN` | *(required for v2)* | OAuth access token from MCP Inspector |
| `WORKUNIT_REFRESH_TOKEN` | *(optional)* | OAuth refresh token for automatic renewal |
| `MCP_URL` | `https://workunit.app/mcp` | MCP endpoint |
| `OAUTH_TOKEN_URL` | `https://workunit.app/oauth/token` | OAuth token endpoint |
| `LMSTUDIO_HOST` | `localhost:1234` | LM Studio host:port |
| `TASK_TIMEOUT_S` | `300` | Per-task timeout in seconds |
| `MCP_CALL_TIMEOUT` | `60` | MCP HTTP call timeout in seconds |

---

## Setup

### Prerequisites

- **LM Studio** running with local server enabled (`http://localhost:1234`)
- **Python 3.10+** with dependencies:
  ```bash
  pip install openai rich requests
  ```

### LM Studio Configuration

The runner connects to `http://localhost:1234` by default. Override with `LMSTUDIO_HOST` env var.

Model switching is fully automatic — just specify the model ID in `models.txt` and the runner handles loading/unloading via the LM Studio management API.

GPU offload to RAM is automatic. With 16GB VRAM + 64GB RAM, LM Studio will push as many layers as fit into VRAM and overflow the rest to RAM transparently.

---

## Running the Benchmark

### Full overnight run (all models, all levels)

```bash
export WORKUNIT_TOKEN=your_token
python scripts/runner_v2_agentic.py --models models.txt
```

### Single model

```bash
python scripts/runner_v2_agentic.py --model ibm/granite-4-h-tiny --level 0
python scripts/runner_v1_singleshot.py --model ibm/granite-4-h-tiny --level 0
```

### List available models

```bash
python scripts/runner_v1_singleshot.py --list-models
```

### Dry run (show plan without executing)

```bash
python scripts/runner_v2_agentic.py --models models.txt --dry-run
```

### Cleanup org data

```bash
python scripts/runner_v2_agentic.py --cleanup-only --yes
```

### Aggregate results after runs

```bash
python scripts/aggregate_results.py
```

---

## Task Inventory

### Level 0 — Explicit (11 tasks)

| ID | Task | What it tests |
|----|------|---------------|
| L0-01 | Ping server | Basic tool invocation, zero params |
| L0-02 | Get authenticated user | Zero-parameter tool |
| L0-03 | Create project | String parameters, enum values |
| L0-04 | Create workunit | Required + optional params |
| L0-05 | Create task | String + enum params |
| L0-06 | Get workunit with tasks | Boolean parameters |
| L0-07 | Update task status | Nested object (update_mask) |
| L0-08 | Save context atom | Enum params (atom_type, importance) |
| L0-09 | Search for workunits | Array parameter (result_types) |
| L0-10 | Create knowledge asset | Type-conditional parameters |
| L0-11 | Complete workunit | Multi-field update_mask |

### Level 1 — Natural Language (10 tasks)

| ID | Task | What it tests |
|----|------|---------------|
| L1-01 | Create project from description | Tag arrays, status enums |
| L1-02 | Create workunit from narrative | Deriving problem_statement + success_criteria |
| L1-03 | Add three tasks | Multi-call reasoning (3× create_task) |
| L1-04 | Update task to in-progress | update_mask inference |
| L1-05 | Find and retrieve workunit | Two-step: search → get |
| L1-06 | Save a decision atom | Correct atom_type + importance inference |
| L1-07 | Create product asset | Asset type + lifecycle_stage |
| L1-08 | Get project with stats | Optional flag inference |
| L1-09 | Update priority and tags | Multi-field update_mask |
| L1-10 | Complete workunit with notes | Status-conditional completion_notes |

### Level 2 — Reasoning (7 tasks)

| ID | Task | What it tests |
|----|------|---------------|
| L2-01 | Bootstrap a feature project | create_project → create_workunit with ID chaining |
| L2-02 | Break down feature into tasks | Reasoning about tasks, workunit → N tasks |
| L2-03 | Find and annotate stale work | search → iterate → save_context |
| L2-04 | Document architectural decision | search → save critical decision atom |
| L2-05 | Create project with linked asset | Three-step ID chain: project → asset → link |
| L2-06 | Triage tasks by content | get_workunit → conditional update_task |
| L2-07 | End-of-sprint closeout | Four-step chain: get → update tasks → context → complete |

---

## Results

Results are organized by methodology and run timestamp:
```
results/v1_singleshot/run_20260225_143000/level0_ibm_granite-4-h-tiny_....json
results/v2_agentic/run_20260225_143000/level0_ibm_granite-4-h-tiny_....json
```

A `latest` symlink points to the most recent run. The aggregated comparison table is generated on demand via `python scripts/aggregate_results.py` (or `--run <timestamp>` for a specific run).

---

## Tested Models

21 models across 6 tiers. 5 are not trained for tool calling (`trained_for_tool_use: false` per LM Studio metadata):

| Model | Size | Tool-trained |
|-------|------|-------------|
| `mistralai/ministral-3-3b` | 3B | ✅ |
| `qwen/qwen3-4b-thinking-2507` | 4B | ✅ |
| `ibm/granite-4-h-tiny` | 7B | ✅ |
| `deepseek/deepseek-r1-0528-qwen3-8b` | 8B | ❌ not tool-trained |
| `essentialai/rnj-1` | 8.3B | ✅ |
| `zai-org/glm-4.6v-flash` | 9.4B | ✅ |
| `google/gemma-3-12b` | 12B | ❌ not tool-trained |
| `mistralai/ministral-3-14b-reasoning` | 14B | ✅ |
| `microsoft/phi-4-reasoning-plus` | 15B | ❌ not tool-trained |
| `openai/gpt-oss-20b` | 20B | ✅ |
| `baidu/ernie-4.5-21b-a3b` | 21B | ❌ not tool-trained |
| `mistralai/magistral-small-2509` | 24B | ✅ |
| `mistralai/devstral-small-2-2512` | 24B | ✅ |
| `liquid/lfm2-24b-a2b` | 24B | ✅ |
| `qwen/qwen2.5-coder-32b` | 32B | ❌ not tool-trained |
| `qwen/qwen3.5-35b-a3b` | 35B | ✅ |
| `zai-org/glm-4.7-flash` | 30B | ✅ |
| `qwen/qwen3-coder-30b` | 30B | ✅ |
| `nvidia/nemotron-3-nano` | 30B | ✅ |
| `bytedance/seed-oss-36b` | 36B | ✅ |
| `qwen/qwen3-coder-next` | 80B | ✅ |

---

## About Workunit

[Workunit](https://workunit.app) is a project manager built around AI agents. Each workunit is a self-contained unit of work — problem statement, tasks, and a trail-of-thought that the AI writes back as it works. Connect it to any AI via MCP and the agent gets full context upfront, then saves its decisions and reasoning for the next session.

Free to start. Try it at workunit.app.

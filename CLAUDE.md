# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A benchmark suite evaluating local LLMs on real MCP (Model Context Protocol) tool calling against the Workunit project management API (19 tools). Two evaluation methodologies: single-shot (one response, no feedback) and agentic loop (model gets tool results back, iterates until pass or timeout). 28 tasks across 3 difficulty levels (L0 explicit, L1 natural language, L2 multi-step reasoning).

## Running Benchmarks

```bash
# Full run (v1 singleshot → v2 agentic → aggregate report)
cd local-llm-mcp-calling
LMSTUDIO_HOST=<ip>:1234 ./scripts/run_all_benchmarks.sh <access_token> <refresh_token>

# Single model, single level
python scripts/runner_v2_agentic.py --model ibm/granite-4-h-tiny --level 0 --token <token> --local

# Resume crashed run (skips completed model+level combos)
BENCH_RESUME=20260225_143000 ./scripts/run_all_benchmarks.sh <token>

# Aggregate results into report
python scripts/aggregate_results.py --run <timestamp>

# Generate graph images (run from reports/images/)
cd reports/images && python gen_graph1_ss_vs_ag.py  # supports --run <timestamp>
```

Key env vars: `LMSTUDIO_HOST` (default localhost:1234), `BENCH_MODEL` (filter to one model), `BENCH_LEVEL` (filter to one level), `BENCH_PHASES` (ss,ag,report).

## Architecture

All code lives under `local-llm-mcp-calling/`.

### Runners (scripts/)

**`runner_v1_singleshot.py`** — Sends one prompt per task, scores the model's first response. After scoring, executes tool calls against MCP to capture real entity IDs for placeholder substitution in subsequent tasks.

**`runner_v2_agentic.py`** — Full agentic loop: prompt → model tool calls → execute against MCP → feed results back → repeat until pass or 300s timeout. Handles model loading/unloading via LM Studio management API, org data cleanup between models, and L2 fixture seeding.

Both runners share the same `validate()` function (defined in v2, duplicated in v1). The validation engine is the core of the benchmark.

### Task Definitions (tasks/)

Three JSON files: `level0_explicit.json`, `level1_natural.json`, `level2_reasoning.json`. Each contains a `tasks` array with:
- `prompt`: sent to the model (may contain `{{project_id}}` etc. placeholders)
- `validation`: scoring rules (see Validation Types below)

**Placeholder substitution**: Runners maintain a `context` dict populated with entity IDs from previous task results. Before each task, `{{project_id}}`, `{{workunit_id}}`, `{{task_id}}` in prompts are replaced with real UUIDs.

**L2 fixture seeding**: Before L2 tasks run, `seed_l2_fixtures()` creates a project, workunit, and 4 tasks via real MCP calls. This provides data for L2-06 (triage tasks) and L2-07 (sprint closeout).

### Validation Types

1. **`tool_call_match`** — Single tool call. Checks tool name, required params, exact values, contains checks, param presence, update_mask paths.

2. **`multi_tool_call`** — Multiple calls of same tool (e.g., create 3 tasks). Checks `call_count_min`, `each_must_have`, `titles_must_include`.

3. **`multi_tool_sequence` / `reasoning_chain`** — Ordered multi-step. Each step validates: tool name, params, and semantic validators:
   - `name_must_relate_to` — keyword in name param
   - `query_must_contain` / `query_must_relate_to` — search query content
   - `atom_type_must_be` — exact atom_type match
   - `content_must_mention` — keywords in content/title
   - `*_must_match` (project_id, asset_id, workunit_id) — ID chaining validation
   - `update_mask_must_contain` — required update_mask paths

### Scoring

- **Task score**: 0.0-1.0 with partial credit per step/param
- **Pass threshold**: score >= 0.75 (tool_call_match uses 0.6)
- **Level score**: mean of task scores at that level
- **Overall score**: mean of three level scores

### Graph Generation (reports/images/)

`_load_results.py` — Shared loader that reads result JSONs from `results/{v1_singleshot,v2_agentic}/latest/`. All graph scripts use `load_from_cli()` with optional `--run TIMESTAMP`.

Three generators produce PNG images: graph1 (SS vs AG horizontal bars), graph2 (L0/L1/L2 agentic breakdown), graph3 (tool-trained vs control scatter + grouped bars).

### Results Layout

```
results/v1_singleshot/run_<timestamp>/level{0,1,2}_<model>_<ts>.json
results/v2_agentic/run_<timestamp>/level{0,1,2}_<model>_<ts>.json
results/*/latest -> run_<timestamp>  (symlink)
```

## Key Design Decisions

- **v2 agentic cleans all org data between models** to prevent data bleed. This is destructive — always use a dedicated Workunit account.
- **L2 tasks use natural language references** (e.g., "the 'Implement User Notifications' workunit") instead of UUIDs, requiring models to search for entities.
- **L2-07 does NOT enforce step ordering** — save_context before update_task is equally valid.
- **ID chaining validation** falls back to UUID format heuristic when `mcp_result` isn't stored in tool call records.
- **Models list** is in `models.txt` — comments with `#`, models marked `*` are not tool-trained (control group).

## Dependencies

```bash
pip install openai rich requests matplotlib numpy
```

Python 3.10+ required. LM Studio provides the OpenAI-compatible inference API.

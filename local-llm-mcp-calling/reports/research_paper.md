# MCP Tool Calling Performance of Local LLMs: Single-shot vs Agentic Evaluation Across 21 Models

> **Status: COMPLETE** — v2 benchmark run with semantic validation, February 2026

## Abstract

We evaluate 21 locally-run large language models (3B–80B parameters, primarily Q4_K_M quantization) on MCP (Model Context Protocol) tool calling using a 19-tool project management API. The benchmark comprises 28 tasks across three difficulty levels — explicit instruction (L0, 11 tasks), natural language interpretation (L1, 10 tasks), and multi-step reasoning (L2, 7 tasks) — evaluated under two methodologies: single-shot (one response, no feedback) and agentic loop (iterative with real API responses, 300s timeout). Agentic evaluation yields consistent gains over single-shot, with the effect scaling by difficulty: +5.0pp at L0 (explicit), +12.6pp at L1 (natural language), and +37.3pp at L2 (reasoning). Tool-trained models outperform control-group models by 19.4pp on average in agentic mode. Model size alone is a weak predictor: a 4B-parameter model (qwen3-4b-thinking-2507) achieves 89.3% agentic overall, outperforming models up to 9x its size. The top-performing model is glm-4.7-flash at 95.4% agentic overall.

---

## 1. Introduction

Tool calling — the ability of a language model to select, parameterize, and invoke external functions — is a foundational capability for agentic workflows. As LLM-based agents move beyond text generation into real software systems, tool calling accuracy determines whether an agent can reliably interact with APIs, databases, and infrastructure. The Model Context Protocol (MCP) has emerged as a standard interface for connecting LLMs to external tools, making tool-calling proficiency directly relevant to practical deployment.

Most tool-calling evaluations focus on cloud-hosted frontier models with proprietary training data and infrastructure. Comparatively little empirical data exists for local, quantized models — the kind practitioners actually run on consumer hardware. This gap matters because quantization, limited context, and the absence of tool-specific fine-tuning may degrade tool-calling accuracy in ways that general-purpose benchmarks do not capture.

This benchmark measures tool-calling performance along two independent axes: **task difficulty** (how much reasoning is required to construct the correct tool call) and **evaluation methodology** (whether the model receives feedback from real tool execution). The interaction between these axes reveals which models benefit from iterative correction, which models can reason through multi-step tool chains on the first attempt, and where model size, architecture, and training data make the difference.

## 2. Experimental Setup

### 2.1 Hardware and Runtime

All models were evaluated on a single consumer workstation. No cloud APIs were used; all inference ran locally via LM Studio.

| Component | Specification |
|-----------|--------------|
| CPU | AMD Ryzen 7 7800X3D (8-core, x86_64, AVX/AVX2) |
| GPU | NVIDIA GeForce RTX 4080 SUPER (Discrete, CUDA) |
| VRAM | 16 GB |
| System RAM | 64 GB |
| Model runtime | LM Studio 0.4.4 (Build 1) |
| Inference backend | CUDA 12 llama.cpp v2.4.0 |
| Context length | 8192 tokens (all models) |
| Temperature | 0.0 (deterministic, set by runner) |
| Max output tokens | 4096 |
| Quantization | Q4_K_M (19 models), Q3_K_L (devstral-small-2), MXFP4 (gpt-oss-20b) |
| Task timeout | 300s wall-clock per task (agentic only) |
| Max agentic turns | 25 turns per task |

### 2.2 MCP Server

The target API is the Workunit project management system, exposing 19 MCP tools across five functional categories:

| Category | Tools | Description |
|----------|-------|-------------|
| Projects | `create_project`, `get_project`, `update_project`, `remove_project`, `list_projects` | Project lifecycle management |
| Workunits | `create_workunit`, `get_workunit`, `update_workunit` | Work item tracking with problem statements and success criteria |
| Tasks | `create_task`, `get_task`, `update_task` | Task management within workunits |
| Assets | `create_asset`, `get_asset`, `update_asset`, `delete_asset`, `project_asset_link` | Knowledge, product, people, and system assets |
| Cross-cutting | `search`, `save_context`, `directory`, `ping`, `get_authenticated_user` | Search, audit trail, directory management |

The API maintains real state: entities created by the model persist across tasks within a run. The database is cleaned between models to prevent data bleed. This means tool calls have real consequences — creating a project returns a real UUID that subsequent tasks must reference.

### 2.3 Models Tested

21 models spanning 3B to 80B parameters, with 16 tool-trained and 5 control-group models (not fine-tuned for tool calling). Most models were quantized to Q4_K_M; two exceptions are noted below (devstral-small-2 at Q3_K_L, gpt-oss-20b at MXFP4).

| # | Model | Params | Disk Size | Quant | Tool-trained |
|---|-------|--------|----------:|-------|:---:|
| 1 | mistralai/ministral-3-3b | 3B | 2.8 GB | Q4_K_M | Yes |
| 2 | qwen/qwen3-4b-thinking-2507 | 4B | 2.3 GB | Q4_K_M | Yes |
| 3 | ibm/granite-4-h-tiny | 7B | 3.9 GB | Q4_K_M | Yes |
| 4 | deepseek/deepseek-r1-0528-qwen3-8b | 8B | 4.7 GB | Q4_K_M | No |
| 5 | essentialai/rnj-1 | 8.3B | 4.8 GB | Q4_K_M | Yes |
| 6 | zai-org/glm-4.6v-flash | 9.4B | 7.4 GB | Q4_K_M | Yes |
| 7 | google/gemma-3-12b | 12B | 7.6 GB | Q4_K_M | No |
| 8 | microsoft/phi-4-reasoning-plus | 15B | 8.4 GB | Q4_K_M | No |
| 9 | mistralai/ministral-3-14b-reasoning | 14B | 8.5 GB | Q4_K_M | Yes |
| 10 | openai/gpt-oss-20b | 20B | 11.3 GB | MXFP4 | Yes |
| 11 | baidu/ernie-4.5-21b-a3b | 21B (3B active) | 12.6 GB | Q4_K_M | No |
| 12 | mistralai/magistral-small-2509 | 24B | 14.2 GB | Q4_K_M | Yes |
| 13 | mistralai/devstral-small-2-2512 | 24B | 12.4 GB | Q3_K_L | Yes |
| 14 | liquid/lfm2-24b-a2b | 24B (MoE 64×1.3B) | 13.4 GB | Q4_K_M | Yes |
| 15 | zai-org/glm-4.7-flash | 30B | 16.9 GB | Q4_K_M | Yes |
| 16 | qwen/qwen3-coder-30b | 30B (3B active) | 17.4 GB | Q4_K_M | Yes |
| 17 | nvidia/nemotron-3-nano | 30B | 22.8 GB | Q4_K_M | Yes |
| 18 | qwen/qwen2.5-coder-32b | 32B | 18.5 GB | Q4_K_M | No |
| 19 | qwen/qwen3.5-35b-a3b | 35B (3B active) | 20.6 GB | Q4_K_M | Yes |
| 20 | bytedance/seed-oss-36b | 36B | 20.3 GB | Q4_K_M | Yes |
| 21 | qwen/qwen3-coder-next | 80B | 45.2 GB | Q4_K_M | Yes |

**Control group models** (marked "No" for tool-trained): deepseek-r1-0528-qwen3-8b, gemma-3-12b, phi-4-reasoning-plus, ernie-4.5-21b-a3b, and qwen2.5-coder-32b. These were included to measure whether general reasoning ability alone enables tool calling, and to quantify the effect of tool-specific fine-tuning.

### 2.4 Task Design

28 tasks across three difficulty levels, each testing progressively more demanding tool-calling skills:

**Level 0 — Explicit (11 tasks)**: The prompt names the exact tool and provides all parameter values. The model only needs to format a well-formed tool call. Tests: basic tool invocation, parameter types (strings, booleans, arrays, nested objects), update_mask construction.

> *Example L0 (explicit) prompt*: `Call the create_project tool with these exact parameters: name="Benchmark Test Project", description="Created during MCP benchmark testing", status="active".`

**Level 1 — Natural Language (10 tasks)**: The prompt describes what to do in plain language with most parameter values embedded in the narrative. The model must identify the correct tool and map natural language to parameter names. Tests: tool selection, parameter inference, multi-call reasoning, update_mask generation.

> *Example L1 (natural language) prompt*: `I need to track some work on fixing our login page. Create a workunit named "Fix Login Page Bug" in project {{project_id}}. The problem is that users can't log in when they have special characters in their password. We'll know it's done when all character types are supported and there are regression tests. Make it high priority.`

**Level 2 — Multi-step Reasoning (7 tasks)**: The prompt describes a high-level goal in human terms. The model must determine which tools to call, in what order, derive parameters from context and previous tool results, and chain entity IDs across steps. Tests: multi-step planning, ID chaining, conditional logic, semantic correctness of generated content.

> *Example L2 (reasoning) prompt*: `I'm starting work on a dark mode feature for our app. Set up everything I need to track this work: create a project for it, then create a workunit inside that project for the implementation work.`

L2 (reasoning) tasks include ID chaining validation — the UUID returned by one tool call must appear as input to the next — and semantic validation of generated content (e.g., a "decision" context atom about WebSockets must mention both "WebSocket" and "polling").

### 2.5 Scoring

- **Task score** (0.0–1.0): Partial credit awarded per parameter match, per step in multi-step chains. A task with 5 validation checks that passes 3 scores 0.6.
- **Pass rate**: Binary. A task passes at score ≥ 0.75 (single-tool tasks use ≥ 0.6 threshold).
- **Level score**: Mean of task scores across all tasks at that level.
- **Overall score**: Mean of three level scores (equally weighted regardless of task count per level).

### 2.6 Evaluation Methodologies

**Single-shot**: The model receives one prompt per task and produces one response. No tool results are returned. The runner scores whatever the model emits. After scoring, tool calls are executed against the MCP API to capture entity IDs for placeholder substitution in subsequent tasks.

**Agentic loop**: The model receives a prompt, emits a tool call, receives the real API response, and can continue calling tools until the task passes or the 300s wall-clock timeout expires. A 25-turn cap prevents spin loops. The model receives full tool results (success responses with entity data, or error messages) and can self-correct across turns.

### 2.7 v2 Methodology Improvements

Key changes from v1 that affect scores:

1. **Semantic validation enforced**: `name_must_relate_to`, `query_must_contain`, `query_must_relate_to`, `atom_type_must_be`, `content_must_mention`, `update_mask_must_contain`, and ID chaining (`*_must_match`) validators are now active. v1 had these defined in task JSONs but never checked.
2. **call_count_min fixed**: Tasks requiring multiple calls of the same tool (e.g., `create_task` ×3) now correctly enforce the minimum count. v1 silently defaulted to 1.
3. **Placeholder substitution**: Tasks referencing entities from earlier tasks (`{{project_id}}`, `{{workunit_id}}`) now receive real UUIDs instead of literal placeholder strings.
4. **L2 (reasoning) fixture seeding**: L2 (reasoning) tasks that require pre-existing data (e.g., "triage the tasks in this workunit") now have fixture data created before the level runs.
5. **L2-03 prompt clarity**: atom_type expectation made unambiguous.
6. **L2-07 ordering relaxed**: Multiple valid step orderings accepted.
7. **Best-call validation (v2.1)**: The agentic validator scores every call of the expected tool and keeps the best result, rather than always scoring the first call. This correctly rewards models that self-correct across turns.
8. **Max-turns cap (v2.1)**: 25-turn limit per task prevents spin loops where a model repeats the same failing call until wall-clock timeout (observed: 488 identical calls in one task).

**Impact**: L2 (reasoning) scores are more discriminating (semantic correctness matters, not just tool name matching). Some models score lower than v1 on tasks where they were getting credit for structurally correct but semantically wrong calls.

### 2.8 Known Limitations of v1 Singleshot Methodology

The v1 singleshot runner uses **placeholder substitution** where entity IDs from earlier tasks (e.g., `{{project_id}}` from L0-03) are injected into later task prompts. When an early task fails, downstream tasks receive literal placeholder strings instead of valid UUIDs, causing cascade failures. A single failed `create_project` at L0-03 can cascade to 5 downstream tasks (L0-04 through L0-11). This is a known design tradeoff: it tests realistic chained workflows but conflates independent tool-calling ability with error recovery. The v2 agentic benchmark does not have this issue since models receive real MCP results and can recover.

### 2.9 Model Notes

- **qwen/qwen2.5-coder-32b** is a code completion model (emits FIM tokens like `<|fim_suffix|>`, `<|fim_middle|>`) not designed for chat-based tool calling.
- **bytedance/seed-oss-36b** experienced a Jinja template incompatibility in LM Studio during the initial v2 agentic run (`Unknown operator "in" between ArrayValue and TupleValue`). LM Studio's Jinja engine does not support Python's `in` operator for membership testing against tuples or arrays. Three template constructs were incompatible: `t in ("number", "integer")` (tuple membership), `name in item.function.parameters.required` (array membership), and `message.role in ["user", "system"]` (array membership). Each was rewritten to use explicit equality checks and loop-based membership. After applying the fix, seed-oss-36b was rerun successfully. Its v1 singleshot results were not affected (single-turn messages never triggered the template bugs). Full template fix details are documented in `reports/notes.md`.

## 3. Results

### 3.1 Agentic Loop — Overall Rankings

![Agentic and single-shot overall score heatmap](images/graph5_heatmap.png)

*Figure 1. Heatmap of per-level scores and overall scores across all 21 models, agentic methodology. Models sorted by agentic overall score descending.*

| Rank | Model | Params | Disk | Tool | L0 (explicit) | L1 (natural language) | L2 (reasoning) | Overall |
|------|-------|--------|-----:|:----:|-----:|-----:|-----:|--------:|
| 1 | glm-4.7-flash | 30B | 16.9 GB | Yes | 100.0 | 97.0 | 89.3 | **95.4** |
| 2 | qwen3-coder-next | 80B | 45.2 GB | Yes | 100.0 | 100.0 | 85.7 | **95.2** |
| 3 | devstral-small-2-2512 | 24B | 12.4 GB | Yes | 100.0 | 100.0 | 82.1 | **94.0** |
| 3 | ministral-3-14b-reasoning | 14B | 8.5 GB | Yes | 100.0 | 100.0 | 82.1 | **94.0** |
| 3 | qwen3.5-35b-a3b | 35B (3B active) | 20.6 GB | Yes | 100.0 | 100.0 | 82.1 | **94.0** |
| 6 | magistral-small-2509 | 24B | 14.2 GB | Yes | 100.0 | 98.5 | 77.6 | **92.0** |
| 7 | qwen3-coder-30b | 30B (3B active) | 17.4 GB | Yes | 100.0 | 100.0 | 75.0 | **91.7** |
| 8 | phi-4-reasoning-plus | 15B | 8.4 GB | No | 100.0 | 96.5 | 77.6 | **91.4** |
| 9 | gpt-oss-20b | 20B | 11.3 GB | Yes | 100.0 | 92.0 | 81.2 | **91.1** |
| 10 | qwen3-4b-thinking-2507 | 4B | 2.3 GB | Yes | 100.0 | 100.0 | 67.9 | **89.3** |
| 11 | lfm2-24b-a2b | 24B (MoE 64×1.3B) | 13.4 GB | Yes | 100.0 | 92.0 | 75.4 | **89.1** |
| 12 | essentialai/rnj-1 | 8.3B | 4.8 GB | Yes | 100.0 | 100.0 | 64.8 | **88.3** |
| 13 | granite-4-h-tiny | 7B | 3.9 GB | Yes | 98.6 | 91.5 | 69.9 | **86.7** |
| 14 | nemotron-3-nano | 30B | 22.8 GB | Yes | 100.0 | 98.5 | 59.3 | **85.9** |
| 14 | gemma-3-12b | 12B | 7.6 GB | No | 100.0 | 91.0 | 66.7 | **85.9** |
| 14 | ernie-4.5-21b-a3b | 21B (3B active) | 12.6 GB | No | 100.0 | 100.0 | 57.6 | **85.9** |
| 17 | ministral-3-3b | 3B | 2.8 GB | Yes | 100.0 | 92.0 | 63.2 | **85.1** |
| 18 | glm-4.6v-flash | 9.4B | 7.4 GB | Yes | 90.9 | 83.5 | 67.1 | **80.5** |
| 19 | seed-oss-36b | 36B | 20.3 GB | Yes | 86.8 | 71.3 | 41.7 | **66.6** |
| 20 | qwen2.5-coder-32b | 32B | 18.5 GB | No | 72.7 | 40.0 | 17.9 | **43.5** |
| 21 | deepseek-r1-0528-qwen3-8b | 8B | 4.7 GB | No | 97.3 | 22.0 | 0.0 | **39.8** |

**Level averages (agentic)**: L0 (explicit) 97.4%, L1 (natural language) 88.8%, L2 (reasoning) 65.9%. **Pass rate averages**: L0 (explicit) 97.8%, L1 (natural language) 89.5%, L2 (reasoning) 49.7%.

### 3.2 Single-shot — Overall Rankings

| Rank | Model | Params | Disk | Tool | L0 (explicit) | L1 (natural language) | L2 (reasoning) | Overall |
|------|-------|--------|-----:|:----:|-----:|-----:|-----:|--------:|
| 1 | lfm2-24b-a2b | 24B (MoE 64×1.3B) | 13.4 GB | Yes | 100.0 | 89.0 | 57.1 | **82.0** |
| 2 | devstral-small-2-2512 | 24B | 12.4 GB | Yes | 100.0 | 93.5 | 44.0 | **79.2** |
| 3 | magistral-small-2509 | 24B | 14.2 GB | Yes | 100.0 | 92.0 | 41.7 | **77.9** |
| 4 | ministral-3-14b-reasoning | 14B | 8.5 GB | Yes | 100.0 | 91.0 | 40.5 | **77.2** |
| 4 | qwen3-coder-next | 80B | 45.2 GB | Yes | 100.0 | 93.5 | 38.1 | **77.2** |
| 6 | ministral-3-3b | 3B | 2.8 GB | Yes | 100.0 | 92.5 | 35.5 | **76.0** |
| 7 | qwen3-coder-30b | 30B (3B active) | 17.4 GB | Yes | 100.0 | 93.5 | 29.8 | **74.4** |
| 8 | granite-4-h-tiny | 7B | 3.9 GB | Yes | 100.0 | 79.7 | 42.6 | **74.1** |
| 9 | gpt-oss-20b | 20B | 11.3 GB | Yes | 100.0 | 85.2 | 36.9 | **74.0** |
| 10 | ernie-4.5-21b-a3b | 21B (3B active) | 12.6 GB | No | 100.0 | 85.2 | 36.2 | **73.8** |
| 11 | glm-4.7-flash | 30B | 16.9 GB | Yes | 100.0 | 85.2 | 33.3 | **72.8** |
| 12 | gemma-3-12b | 12B | 7.6 GB | No | 100.0 | 84.2 | 31.9 | **72.0** |
| 13 | qwen3.5-35b-a3b | 35B (3B active) | 20.6 GB | Yes | 100.0 | 85.2 | 26.2 | **70.5** |
| 14 | essentialai/rnj-1 | 8.3B | 4.8 GB | Yes | 100.0 | 83.7 | 26.2 | **70.0** |
| 15 | nemotron-3-nano | 30B | 22.8 GB | Yes | 100.0 | 83.5 | 7.1 | **63.5** |
| 16 | seed-oss-36b | 36B | 20.3 GB | Yes | 77.7 | 76.7 | 33.3 | **62.6** |
| 17 | glm-4.6v-flash | 9.4B | 7.4 GB | Yes | 90.9 | 45.2 | 19.0 | **51.7** |
| 18 | qwen3-4b-thinking-2507 | 4B | 2.3 GB | Yes | 81.8 | 30.2 | 7.1 | **39.7** |
| 19 | deepseek-r1-0528-qwen3-8b | 8B | 4.7 GB | No | 90.9 | 26.7 | 0.0 | **39.2** |
| 20 | qwen2.5-coder-32b | 32B | 18.5 GB | No | 63.6 | 43.5 | 7.1 | **38.1** |
| 21 | phi-4-reasoning-plus | 15B | 8.4 GB | No | 36.4 | 61.7 | 7.1 | **35.1** |

**Level averages (single-shot)**: L0 (explicit) 92.4%, L1 (natural language) 76.2%, L2 (reasoning) 28.6%. **Pass rate averages**: L0 (explicit) 92.6%, L1 (natural language) 73.3%, L2 (reasoning) 2.0%.

### 3.3 Single-shot vs Agentic Comparison

![Single-shot vs agentic overall scores for all 21 models](images/graph1_ss_vs_ag_overall.png)

*Figure 2. Horizontal bar chart comparing single-shot (orange) and agentic (blue) overall scores for all 21 models, sorted by agentic score.*

The agentic methodology produced higher overall scores for every model tested. The mean lift across all models is +18.3pp (median +16.8pp). The magnitude scales with difficulty:

| Level | Single-shot Score (mean) | Agentic Score (mean) | Lift | Single-shot Pass Rate | Agentic Pass Rate |
|-------|----------------:|----------------:|-----:|-------------:|-------------:|
| L0 (explicit) | 92.4% | 97.4% | +5.0pp | 92.6% | 97.8% |
| L1 (natural language) | 76.2% | 88.8% | +12.6pp | 73.3% | 89.5% |
| L2 (reasoning) | 28.6% | 65.9% | +37.3pp | 2.0% | 49.7% |

The per-model lift varies considerably:

![Agentic lift per model](images/graph4_agentic_lift.png)

*Figure 3. Agentic lift (agentic score minus single-shot score) for each model, sorted by magnitude.*

| Model | Single-shot Overall | Agentic Overall | Lift |
|-------|----------:|----------:|-----:|
| phi-4-reasoning-plus | 35.1 | 91.4 | **+56.3** |
| qwen3-4b-thinking-2507 | 39.7 | 89.3 | **+49.6** |
| glm-4.6v-flash | 51.7 | 80.5 | **+28.8** |
| qwen3.5-35b-a3b | 70.5 | 94.0 | **+23.5** |
| glm-4.7-flash | 72.8 | 95.4 | **+22.6** |
| nemotron-3-nano | 63.5 | 85.9 | **+22.4** |
| essentialai/rnj-1 | 70.0 | 88.3 | **+18.3** |
| qwen3-coder-next | 77.2 | 95.2 | **+18.0** |
| qwen3-coder-30b | 74.4 | 91.7 | **+17.3** |
| gpt-oss-20b | 74.0 | 91.1 | **+17.1** |
| ministral-3-14b-reasoning | 77.2 | 94.0 | **+16.8** |
| devstral-small-2-2512 | 79.2 | 94.0 | **+14.8** |
| magistral-small-2509 | 77.9 | 92.0 | **+14.1** |
| gemma-3-12b | 72.0 | 85.9 | **+13.9** |
| granite-4-h-tiny | 74.1 | 86.7 | **+12.6** |
| ernie-4.5-21b-a3b | 73.8 | 85.9 | **+12.1** |
| ministral-3-3b | 76.0 | 85.1 | **+9.1** |
| lfm2-24b-a2b | 82.0 | 89.1 | **+7.1** |
| qwen2.5-coder-32b | 38.1 | 43.5 | **+5.4** |
| seed-oss-36b | 62.6 | 66.6 | **+4.0** |
| deepseek-r1-0528-qwen3-8b | 39.2 | 39.8 | **+0.6** |

The two largest lifts — phi-4-reasoning-plus (+56.3pp) and qwen3-4b-thinking-2507 (+49.6pp) — both come from models that struggled with single-shot formatting but have strong underlying reasoning. phi-4-reasoning-plus scored only 36.4% on L0 (explicit) in single-shot mode (suggesting format or template issues) but achieved 100.0% L0 (explicit) in agentic mode once it could observe and correct its output.

### 3.4 Per-Level Analysis

![Agentic scores broken down by level for all 21 models](images/graph2_level_breakdown_agentic.png)

*Figure 4. Stacked bar chart showing L0 (explicit), L1 (natural language), and L2 (reasoning) agentic scores for each model.*

**L0 (Explicit)**: Near-ceiling for most models. 16 of 21 models scored 100.0%. The remaining 5 scored between 72.7% and 98.6%. L0 does not discriminate between capable models.

**L1 (Natural Language)**: Moderate spread. Scores range from 22.0% (deepseek-r1-0528-qwen3-8b) to 100.0% (8 models tied). The median L1 score is 97.0%. L1 separates models that can identify tools from natural language from those that cannot, but provides limited resolution at the top.

**L2 (Multi-step Reasoning)**: The primary discriminator. Scores range from 0.0% (deepseek-r1-0528-qwen3-8b) to 89.3% (glm-4.7-flash), with a spread of 89.3pp. The median L2 score is 69.9%. Only 2 models exceed 85% at L2 (reasoning). Pass rates drop sharply: L2 (reasoning) agentic pass rate is 49.7% versus 97.8% at L0 (explicit).

**L2 (reasoning) in single-shot mode** is nearly non-functional: the average L2 (reasoning) single-shot pass rate is 2.0% (only lfm2-24b-a2b passes any L2 (reasoning) tasks in single-shot mode, with 42.9% pass rate). This confirms that multi-step tool chains effectively require iterative execution with real feedback.

### 3.5 Tool-trained vs Control Group

![Tool-trained vs control group comparison](images/graph3_trained_vs_control.png)

*Figure 5. Comparison of tool-trained models (n=16) vs control group (n=5) on agentic overall scores.*

| Group | N | Agentic Overall (mean) | Agentic Overall (range) | Std Dev (σ) |
|-------|---|------------------:|-------------------:|--------------:|
| Tool-trained | 16 | 88.7% | 66.6% – 95.4% | 7.2pp |
| Control | 5 | 69.3% | 39.8% – 91.4% | 25.4pp |
| **Delta** | | **+19.4pp** | | |

The tool-training effect is substantial but not uniform. Within the control group, phi-4-reasoning-plus (91.4% agentic) performs at the level of the top tool-trained models, while deepseek-r1-0528-qwen3-8b (39.8%) and qwen2.5-coder-32b (43.5%) perform poorly. This suggests that strong general reasoning (phi-4) can compensate for the absence of tool-specific training, but code-completion pretraining (qwen2.5-coder) does not transfer to structured tool calling.

The control group shows wider variance (σ = 25.4pp) compared to the tool-trained group (σ = 7.2pp), suggesting that tool-training provides a more consistent floor of competence.

### 3.6 Size-Performance Analysis

Grouping models by parameter count into tiers:

| Tier | Models | Param Range | Disk Range | Agentic Overall (mean) | Agentic Overall (range) |
|------|--------|-------------|-----------|------------------:|-------------------:|
| Tiny (3–4B) | 2 | 3B–4B | 2.3–2.8 GB | 87.2% | 85.1% – 89.3% |
| Small (7–9.4B) | 4 | 7B–9.4B | 3.9–7.4 GB | 73.8% | 39.8% – 88.3% |
| Medium (12–15B) | 3 | 12B–15B | 7.6–8.5 GB | 90.4% | 85.9% – 94.0% |
| Large (20–24B) | 5 | 20B–24B | 11.3–14.2 GB | 90.4% | 85.9% – 94.0% |
| XL (30–36B) | 6 | 30B–36B | 16.9–22.8 GB | 79.5% | 43.5% – 95.4% |
| XXL (80B) | 1 | 80B | 45.2 GB | 95.2% | 95.2% |

Within the tool-trained subset, the correlation between parameter count and agentic overall score is weak. The Tiny tier (mean 87.2%) outperforms the Small tier (73.8%) and approaches the Large tier (90.4%). The XL tier's mean is dragged down by qwen2.5-coder-32b (43.5%, control) and seed-oss-36b (66.6%, template issues).

Notable observations:
- **ministral-3-3b** (3B, 2.8 GB on disk, 85.1% agentic) outperforms 4 of the 21 models, including models up to 36B parameters.
- **qwen3-4b-thinking-2507** (4B, 2.3 GB on disk, 89.3% agentic) outperforms 11 of the 20 other models, including models up to 9x its parameter count (seed-oss-36b, 36B).
- The highest-performing model overall (glm-4.7-flash, 30B, 95.4%) is not the largest.

## 4. Discussion

### 4.1 Methodology Effect

The agentic methodology consistently outperforms single-shot across all models, but the magnitude scales with task difficulty. The +5.0pp mean lift at L0 (explicit) reflects minor formatting corrections — models that emit slightly malformed tool calls on the first attempt can fix them after seeing the error response. The +12.6pp lift at L1 (natural language) reflects models correcting tool selection or parameter mapping after feedback. The +37.3pp lift at L2 (reasoning) is qualitatively different: it reflects the fundamental advantage of iterative tool chaining. Single-shot L2 (reasoning) requires the model to predict the correct UUIDs for entities it hasn't created yet — which is impossible by design.

The practical implication is that single-shot evaluation dramatically underestimates a model's tool-calling utility. A model scoring 39.7% single-shot (qwen3-4b-thinking-2507) can score 89.3% in an agentic setting — a 2.2x improvement. For practitioners building agent systems, single-shot benchmarks provide limited signal about real-world performance.

### 4.2 L2 (Reasoning) as Discriminator

L0 (explicit) and L1 (natural language) show ceiling effects in agentic mode: 16/21 models score 100.0% on L0 (explicit), and 8/21 score 100.0% on L1 (natural language). L2 (reasoning) remains discriminating even in agentic mode, with an 89.3pp range and no model at ceiling.

L2 (reasoning) tasks require capabilities that feedback alone cannot provide: multi-step planning (determining the correct tool sequence), ID chaining (using output from one call as input to the next), conditional logic (applying different actions based on data), and semantic content generation (producing contextually appropriate descriptions). These capabilities reflect genuine reasoning, not just format compliance.

The L2 (reasoning) single-shot pass rate of 2.0% (compared to 49.7% agentic) shows that L2 (reasoning) tasks effectively cannot be solved without iterative execution. This makes L2 (reasoning) the appropriate level for evaluating models in realistic agentic deployments.

### 4.3 Tool Training

The 19.4pp gap between tool-trained (88.7%) and control (69.3%) groups confirms that tool-specific fine-tuning provides substantial benefit. However, the phi-4-reasoning-plus result (91.4% agentic, not tool-trained) demonstrates that strong reasoning models can achieve tool-trained-level performance through in-context learning alone, when given real feedback in an agentic loop.

This has a practical nuance: phi-4-reasoning-plus achieves 91.4% in agentic mode but only 35.1% in single-shot mode. The model can reason about tools when given feedback, but cannot reliably format tool calls without it. Tool training appears to provide the most value for single-shot reliability (the gap between tool-trained single-shot average of 70.2% and control single-shot average of 51.6% is 18.5pp), with diminishing but still meaningful returns in agentic mode.

### 4.4 Small Models

The performance of sub-10B models challenges the assumption that tool calling requires large models:

- **ministral-3-3b** (3B): 85.1% agentic overall, outperforming 4 models ~2.7–12x its size
- **qwen3-4b-thinking-2507** (4B): 89.3% agentic overall, ranking 10th out of 21 models
- **essentialai/rnj-1** (8.3B): 88.3% agentic overall, comparable to models 3x its size

The qwen3-4b-thinking-2507 result is particularly notable: at 4B parameters (2.3 GB on disk) it fits in under 3GB of VRAM yet outperforms models requiring 20+ GB. Its weakness is single-shot mode (39.7%), suggesting it relies on the agentic loop for error correction — but in an agentic deployment, this is not a limitation.

### 4.5 Anomalies

**phi-4-reasoning-plus (+56.3pp lift)**: The largest agentic lift in the benchmark. In single-shot, it scores 36.4% on L0 (explicit) — far below the 92.4% L0 (explicit) average — suggesting fundamental formatting or template issues. In agentic mode, it achieves 100.0% on L0 (explicit). The model appears to have strong reasoning but poor zero-shot tool-call formatting, and the agentic loop provides the correction mechanism it needs.

**deepseek-r1-0528-qwen3-8b (+0.6pp lift)**: The smallest agentic lift. This model scores 97.3% on L0 (explicit) in agentic mode (correct basic formatting) but 22.0% on L1 (natural language) and 0.0% on L2 (reasoning). It can follow explicit instructions but cannot select tools from natural language or reason about multi-step chains. The agentic loop provides minimal help because the model's failure mode is not formatting errors but fundamental reasoning gaps.

**seed-oss-36b (Jinja template fix)**: Initially scored 0.0% on all v2 agentic tasks due to an LM Studio Jinja template incompatibility. After rewriting three incompatible `in` operator constructs in the chat template (tuple membership, array membership, and inline for-loop filters), the model was rerun successfully, scoring 66.6% agentic overall. This illustrates a practical risk of local model deployment: infrastructure compatibility issues can completely block a model's capabilities. The v1 singleshot results were unaffected (62.6%) since single-turn messages never triggered the template bugs.

**nemotron-3-nano (L2 reasoning divergence)**: Scores 7.1% on L2 (reasoning) in single-shot but 59.3% in agentic mode (+52.2pp L2-specific lift). Its single-shot L2 (reasoning) score is indistinguishable from random, but with feedback it achieves moderate multi-step reasoning.

### 4.6 v1 vs v2 Comparison

The v2 validation improvements primarily affected L2 (reasoning) scores. The enforcement of semantic validators (`name_must_relate_to`, `content_must_mention`, `atom_type_must_be`) means models can no longer receive full credit for calling the right tool with the wrong content. The `call_count_min` fix particularly affected L1-03 (add three tasks) where v1 gave full credit for a single `create_task` call.

Placeholder substitution and fixture seeding improved the fairness of L2 (reasoning) evaluation by ensuring all models receive valid entity IDs and pre-existing data rather than testing infrastructure robustness.

## 5. Limitations

- **Single hardware configuration**: All results are from one RTX 4080 SUPER 16GB system with 64GB RAM. Different GPU architectures or VRAM capacities may yield different results, particularly for larger models that approach VRAM limits.
- **Low-bit quantization**: 19 of 21 models were tested at Q4_K_M quantization, with devstral-small-2 at Q3_K_L and gpt-oss-20b at MXFP4. Native precision (FP16/BF16) or higher quantization levels may improve scores for models that are particularly sensitive to quantization noise.
- **Fixed 8192 context length**: Some models support longer contexts (32K, 128K). Multi-step L2 (reasoning) tasks might benefit from extended context windows that allow the model to retain more turn history.
- **Single MCP domain**: All tasks target a project management API. Tool-calling performance on different domains (code execution, data analysis, web browsing) may differ.
- **Temperature 0.0**: Deterministic decoding eliminates sampling variance but also eliminates sampling diversity. Some models may perform better with non-zero temperature.
- **LM Studio-specific formatting**: LM Studio's tool-call formatting and Jinja template rendering may advantage or disadvantage specific models. The seed-oss-36b template issue illustrates this risk.
- **V1 singleshot placeholder cascade**: One early failure can penalize up to 5 downstream tasks (6x penalty amplification for a single error).
- **No repeated trials**: Each model was run once per methodology. Variance across runs at temperature 0.0 is expected to be minimal but is not measured.

## 6. Conclusion

Three findings stand out for practitioners choosing local models for MCP tool calling:

**1. Use agentic evaluation.** Single-shot benchmarks understate real-world tool-calling performance by 18.3pp on average, and by 37.3pp on multi-step tasks. Any model evaluation for agent deployment should use iterative execution with real tool feedback.

**2. Tool training matters, but reasoning matters more.** Tool-trained models outperform untrained ones by 19.4pp on average, but a strong reasoning model without tool training (phi-4-reasoning-plus, 91.4%) outperforms most tool-trained models. The combination of tool training and strong reasoning is where the top models sit.

**3. Small models are viable for tool calling.** A 4B-parameter model (qwen3-4b-thinking-2507, 89.3%) and a 3B model (ministral-3-3b, 85.1%) compete with or exceed models up to 9x their size. For VRAM-constrained deployments, these results suggest that small, well-trained models can handle structured tool calling at production-relevant accuracy.

The top-performing model overall is **glm-4.7-flash** (30B, 95.4% agentic overall), with qwen3-coder-next (80B, 95.2%) close behind. In the agentic setting, 17 of 21 models exceed 85% overall, suggesting that MCP tool calling at L0 (explicit) and L1 (natural language) difficulty is largely a solved problem for current-generation local models. L2 (reasoning) multi-step tasks remain the frontier, with only 2 models exceeding 85% and a mean of 65.9%.

---

## Appendix

### A. Graph Index

| Figure | File | Description |
|--------|------|-------------|
| 1 | `images/graph5_heatmap.png` | Per-level score heatmap, all models |
| 2 | `images/graph1_ss_vs_ag_overall.png` | Single-shot vs agentic overall comparison |
| 3 | `images/graph4_agentic_lift.png` | Agentic lift per model |
| 4 | `images/graph2_level_breakdown_agentic.png` | L0 (explicit)/L1 (natural language)/L2 (reasoning) agentic breakdown |
| 5 | `images/graph3_trained_vs_control.png` | Tool-trained vs control group |

### B. Task Summary

| Level | Tasks | Focus | Example |
|-------|-------|-------|---------|
| L0 (explicit) | 11 | Explicit tool invocation | "Call `create_project` with name=..." |
| L1 (natural language) | 10 | Natural language → tool mapping | "Create a workunit for fixing the login page" |
| L2 (reasoning) | 7 | Multi-step reasoning chains | "Set up everything for a dark mode feature" |

### C. Raw Result Data

Every benchmark run produces per-model, per-level JSON files in `results/`. The file naming convention is `level{0,1,2}_{org}_{model}_{timestamp}.json`. Each file contains the full audit trail for every task: the exact prompt sent, every tool call the model made (with arguments), the real MCP API response, scoring details, and timing. Both `v1_singleshot/` and `v2_agentic/` directories follow the same structure, with `latest` symlinks pointing to the most recent run.

```
results/
├── v1_singleshot/
│   └── latest/ → run_20260225_*/
│       ├── level0_mistralai_ministral-3-3b_20260225_*.json
│       ├── level1_mistralai_ministral-3-3b_20260225_*.json
│       └── ...
└── v2_agentic/
    └── latest/ → run_20260225_*/
        ├── level0_mistralai_ministral-3-3b_20260225_*.json
        └── ...
```

**Agentic result entry structure** (one per task):

```json
{
  "task_id": "L1-03",
  "task_name": "Add three tasks to a workunit",
  "prompt_sent": "Add these three tasks to workunit 66ed6f25...: ...",
  "tool_calls": [
    {
      "name": "create_task",
      "arguments": {
        "workunit_id": "66ed6f25...",
        "title": "Reproduce the bug locally",
        "priority": "high",
        "status": "todo"
      },
      "mcp_result": "{\"task\":{\"created_at\":\"2026-02-25T18:49:46Z\",\"id\":\"5a3b...\", ...}}"
    },
    { "..." : "..." },
    { "..." : "..." }
  ],
  "turns": 3,
  "passed": true,
  "score": 1.0,
  "details": ["3/3 calls made correctly"],
  "elapsed_s": 4.71,
  "timed_out": false,
  "error": null
}
```

Key fields: `prompt_sent` is the exact text the model received (with placeholders already substituted). `tool_calls` contains every tool invocation the model made, with the full `arguments` object and the raw `mcp_result` JSON string from the real API. In agentic mode, `turns` shows how many round-trips occurred, and `mcp_result` on each call shows what the model saw before making its next decision.

**Singleshot result entries** have the same structure but without `mcp_result` (tool calls are scored but not executed until after scoring), no `turns` field, and a `model_response` field capturing the raw model output text.

This means anyone can open a result JSON, pick a task, and see exactly what the model was asked, what it called, what the API returned, and how it was scored — full transparency on every data point behind the aggregate numbers.

### D. Reproducibility

Full source code, task definitions, runner scripts, and result JSONs are available at:

**Repository**: [github.com/3615-computer/workunit-benchmarks](https://github.com/3615-computer/workunit-benchmarks)

To reproduce:
```bash
cd local-llm-mcp-calling
LMSTUDIO_HOST=<ip>:1234 ./scripts/run_all_benchmarks.sh <access_token> <refresh_token>
```

Requires: Python 3.10+, LM Studio with CUDA, a Workunit API account (free tier).

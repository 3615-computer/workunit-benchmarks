# Reddit Post — r/AIToolsPerformance
# https://www.reddit.com/r/AIToolsPerformance/

---

## TITLE

Benchmark: 21 local LLMs on MCP tool calling — explicit, natural language, and multi-step reasoning tasks, evaluated single-shot and agentic. Full methodology, per-level breakdowns, and reproducibility data.

---

## POST BODY

### Overview

A structured benchmark comparing 21 locally-run LLMs on real MCP (Model Context Protocol) tool calling performance. Each model was evaluated under two methodologies against the same 28 tasks and 19-tool API:

1. **Single-shot**: one API call per task, score the first response
2. **Agentic loop**: model receives actual tool results after each call and continues until the task passes or a 5-minute timeout is hit

The goal is to measure how evaluation methodology affects measured tool-calling ability, and how task complexity (from explicit instruction following to multi-step reasoning) discriminates between models.

---

### Hardware and Infrastructure

| Component | Specification |
|-----------|--------------|
| GPU | NVIDIA RTX 4080 16GB |
| System RAM | 64GB |
| Model runtime | LM Studio (local, OpenAI-compatible API) |
| Context length | 8192 tokens (all models) |
| Temperature | 0.0 (all models) |
| Quantization | Q4_K_M (default); gpt-oss at MXFP4, devstral at Q3_K_L |
| Task timeout | 300s per task (agentic only) |

Models were unloaded from VRAM before each run and reloaded at a fixed 8192 context. The test database was wiped between each model run to prevent data bleed-through.

---

### Models Tested

21 models across 6 size tiers (3B to 80B). 16 classified as tool-trained; 5 not trained for tool calling (per LM Studio metadata), included as a control group.

| Model | Size | Quant | Tool-trained |
|-------|------|-------|-------------|
| mistralai/ministral-3-3b | 3B | Q4_K_M | Yes |
| qwen/qwen3-4b-thinking-2507 | 4B | Q4_K_M | Yes |
| ibm/granite-4-h-tiny | 7B | Q4_K_M | Yes |
| deepseek/deepseek-r1-0528-qwen3-8b | 8B | Q4_K_M | No |
| essentialai/rnj-1 | 8.3B | Q4_K_M | Yes |
| zai-org/glm-4.6v-flash | 9.4B | Q4_K_M | Yes |
| google/gemma-3-12b | 12B | Q4_K_M | No |
| mistralai/ministral-3-14b-reasoning | 14B | Q4_K_M | Yes |
| microsoft/phi-4-reasoning-plus | 15B | Q4_K_M | No |
| openai/gpt-oss-20b | 20B | MXFP4 | Yes |
| baidu/ernie-4.5-21b-a3b | 21B | Q4_K_M | No |
| mistralai/magistral-small-2509 | 24B | Q4_K_M | Yes |
| mistralai/devstral-small-2-2512 | 24B | Q3_K_L | Yes |
| liquid/lfm2-24b-a2b | 24B | Q4_K_M | Yes |
| nvidia/nemotron-3-nano | 30B | Q4_K_M | Yes |
| zai-org/glm-4.7-flash | 30B | Q4_K_M | Yes |
| qwen/qwen3-coder-30b | 30B | Q4_K_M | Yes |
| qwen/qwen2.5-coder-32b | 32B | Q4_K_M | No |
| qwen/qwen3.5-35b-a3b | 35B | Q4_K_M | Yes |
| bytedance/seed-oss-36b | 36B | Q4_K_M | Yes |
| qwen/qwen3-coder-next | 80B | Q4_K_M | Yes |

---

### Task Design

**28 tasks across 3 difficulty levels**, targeting a real project management API with 19 tools (create/get/update for projects, workunits, tasks, assets; search; save_context; directory management; link management).

**Level 0 — Explicit** (11 tasks): Exact tool name and all parameters specified in the prompt. Tests format compliance and basic tool call emission.

> *"Call `create_workunit` with name='Hello World', problem_statement='Users can't track work', success_criteria='Workunit visible in dashboard', priority='normal'"*

**Level 1 — Natural language** (10 tasks): Human-phrased request with relevant information present but unstructured. Model must identify the correct tool and map natural language to parameter names and values.

> *"Create a workunit called 'Fix Login Page Bug'. Problem: users can't log in with special characters. Done when all character types work with regression tests. High priority."*

**Level 2 — Reasoning** (7 tasks): High-level goal with no tool names or parameter hints. Model must plan a multi-step sequence, infer which tools to call, and chain IDs returned from earlier calls into subsequent ones.

> *"End of sprint. Mark all todo tasks done, save a summary of what was accomplished, and complete the workunit."*

---

### Scoring Methodology

Each task defines a required sequence of tool calls with argument constraints. Validation types:

- `tool_call_match`: Exact tool name and required parameters
- `multi_tool_call`: Multiple calls of the same tool required
- `multi_tool_sequence`: Ordered sequence of different tool calls
- `reasoning_chain`: Multi-step sequence with ID propagation between calls
- `param_contains`: Substring matching for flexible parameter validation

**Task score** (0-100%): Partial credit for completing some steps of a multi-step task. A task **passes** at ≥75% score.

**Level score**: Mean task score across all tasks at that level.

**Overall score**: Mean of the three level scores (L0, L1, L2), giving equal weight to each difficulty level regardless of task count (11, 10, 7 tasks respectively).

---

### Methodology: Single-shot vs Agentic

**Single-shot**: The model receives the system prompt, tool definitions, and user task. It makes one (or more, if it emits multiple tool calls in one response) calls, then scoring is based on whatever it produced. No feedback. No continuation.

**Agentic loop**: After each tool call, the runner executes the call against the real MCP server and feeds the result back as a `tool` role message. The model can continue calling tools until the task validation passes or the 300s timeout is hit. The runner exits immediately when validation passes (early exit), so timing reflects actual time-to-completion.

Both runs used `temperature=0.0`. The agentic run also resets the test database between each model and uses `max_tokens=4096` per completion.

---

### Results — Agentic Loop

![Agentic pass rate by difficulty level — 21 models](images/graph2_level_breakdown_agentic.png)

| Model | Size | Tool | L0 Pass% | L1 Pass% | L2 Pass% | Overall |
|-------|------|------|---------|---------|---------|---------|
| qwen/qwen3-coder-30b | 30B | Yes | 100% | 90% | 71% | **92%** |
| qwen/qwen3-coder-next | 80B | Yes | 100% | 90% | 71% | **92%** |
| baidu/ernie-4.5-21b-a3b | 21B | No | 100% | 100% | 29% | **85%** |
| qwen/qwen3-4b-thinking-2507 | 4B | Yes | 100% | 80% | 57% | **85%** |
| ibm/granite-4-h-tiny | 7B | Yes | 100% | 100% | 29% | **85%** |
| openai/gpt-oss-20b | 20B | Yes | 100% | 80% | 43% | **85%** |
| mistralai/ministral-3-14b-reasoning | 14B | Yes | 100% | 90% | 29% | **84%** |
| mistralai/magistral-small-2509 | 24B | Yes | 100% | 100% | 29% | **82%** |
| mistralai/devstral-small-2-2512 | 24B | Yes | 100% | 80% | 43% | **82%** |
| mistralai/ministral-3-3b | 3B | Yes | 91% | 90% | 29% | **81%** |
| google/gemma-3-12b | 12B | No | 91% | 80% | 43% | **80%** |
| qwen/qwen3.5-35b-a3b | 35B | Yes | 100% | 50% | 71% | **77%** |
| nvidia/nemotron-3-nano | 30B | Yes | 100% | 60% | 43% | **77%** |
| essentialai/rnj-1 | 8.3B | Yes | 100% | 80% | 0% | **77%** |
| liquid/lfm2-24b-a2b | 24B | Yes | 82% | 90% | 29% | **73%** |
| zai-org/glm-4.6v-flash | 9.4B | Yes | 91% | 60% | 29% | **70%** |
| zai-org/glm-4.7-flash | 30B | Yes | 55% | 60% | 71% | **63%** |
| microsoft/phi-4-reasoning-plus | 15B | No | 46% | 80% | 43% | **62%** |
| qwen/qwen2.5-coder-32b | 32B | No | 91% | 50% | 14% | **58%** |
| deepseek/deepseek-r1-0528-qwen3-8b | 8B | No | 0% | 0% | 0% | **0%** |
| bytedance/seed-oss-36b | 36B | Yes | 0% | 0% | 0% | **0%** |

---

### Results — Single-shot

| Model | Size | Tool | L0 Pass% | L1 Pass% | L2 Pass% | Overall |
|-------|------|------|---------|---------|---------|---------|
| qwen/qwen3-coder-next | 80B | Yes | 100% | 90% | 0% | **81%** |
| mistralai/devstral-small-2-2512 | 24B | Yes | 100% | 90% | 0% | **79%** |
| liquid/lfm2-24b-a2b | 24B | Yes | 73% | 90% | 57% | **78%** |
| mistralai/ministral-3-14b-reasoning | 14B | Yes | 100% | 90% | 0% | **78%** |
| mistralai/magistral-small-2509 | 24B | Yes | 100% | 90% | 0% | **78%** |
| openai/gpt-oss-20b | 20B | Yes | 100% | 80% | 0% | **76%** |
| mistralai/ministral-3-3b | 3B | Yes | 100% | 90% | 0% | **76%** |
| essentialai/rnj-1 | 8.3B | Yes | 100% | 80% | 0% | **74%** |
| qwen/qwen3-coder-30b | 30B | Yes | 100% | 80% | 0% | **73%** |
| ibm/granite-4-h-tiny | 7B | Yes | 100% | 80% | 0% | **73%** |
| bytedance/seed-oss-36b | 36B | Yes | 100% | 80% | 0% | **71%** |
| qwen/qwen3.5-35b-a3b | 35B | Yes | 91% | 70% | 0% | **65%** |
| zai-org/glm-4.6v-flash | 9.4B | Yes | 82% | 70% | 0% | **61%** |
| nvidia/nemotron-3-nano | 30B | Yes | 91% | 40% | 0% | **51%** |
| zai-org/glm-4.7-flash | 30B | Yes | 64% | 40% | 0% | **44%** |
| qwen/qwen2.5-coder-32b | 32B | No | 64% | 40% | 0% | **38%** |
| microsoft/phi-4-reasoning-plus | 15B | No | 55% | 60% | 0% | **38%** |
| qwen/qwen3-4b-thinking-2507 | 4B | Yes | 91% | 20% | 0% | **37%** |
| deepseek/deepseek-r1-0528-qwen3-8b | 8B | No | 9% | 0% | 0% | **3%** |
| google/gemma-3-12b | 12B | No | 0% | 0% | 0% | **0%** |
| baidu/ernie-4.5-21b-a3b | 21B | No | 0% | 0% | 0% | **0%** |

Single-shot L2 was 0% for 20 of 21 models. The one exception: liquid/lfm2-24b at 57%. Tasks requiring ID chaining are structurally impossible in single-shot since the model cannot observe intermediate results.

---

### Methodology Impact — SS vs AG

![Single-shot vs Agentic Overall Score — 21 models](images/graph1_ss_vs_ag_overall.png)

The mean absolute delta between single-shot and agentic overall scores is 18.3 percentage points across all 21 models.

- 17 models improved with the agentic loop (mean gain: +22.4 pp)
- 2 models scored lower in agentic: seed-oss-36b dropped from 71% to 0%, lfm2-24b dropped from 78% to 73%
- 2 models showed minimal change (deepseek-r1: near 0% in both)

The seed-oss result is a notable anomaly — the model scored 100% L0 and 80% L1 in single-shot but emitted zero tool calls in the agentic loop. The only difference between methodologies is that the agentic runner feeds tool results back as context, which appears to suppress tool calling for this model.

---

### Tool-trained vs Not Tool-trained

![Tool-trained vs not tool-trained — SS and agentic performance](images/graph3_trained_vs_control.png)

5 models not trained for tool calling were included as a control group.

**Single-shot**: Average L0 pass rate is 26% for the control group vs. 93% for tool-trained. Two control models (ernie-4.5 and gemma-3) scored 0% across all levels — they never emitted tool calls.

**Agentic loop**: The gap narrows at L0 (66% control vs. 88% tool-trained) and L1 (62% vs. 75%). At L2, control models average 26% vs. 35% for tool-trained. The two models that scored 0% in single-shot reached 85% (ernie-4.5) and 80% (gemma-3) in the agentic loop, indicating the additional context is sufficient for capable models to infer tool call format.

**L2 gap persists**: Even in the agentic loop, tool-trained models that perform well at L2 (qwen3-coder at 71%, qwen3-4b at 57%) maintain a clear advantage over control models on multi-step reasoning chains.

---

### Key Findings

**1. Evaluation methodology is load-bearing for L2.** Single-shot gives 0% at L2 for 20 of 21 models. The agentic loop unlocks L2 for the better models (up to 71%). Methodology choice is a first-order concern when interpreting tool-calling benchmarks.

**2. Parameter count does not predict performance.** The top overall performer at 92% is 30B. A 4B model (qwen3-4b-thinking) and a 7B model (granite-4-h-tiny) both score 85%, outperforming models up to 36B. A 32B model (qwen2.5-coder) scores 58%. Tool-call fine-tuning is a stronger predictor than size.

**3. Tool training has variable impact depending on methodology.** In single-shot, models not trained for tool calling that never emitted tool calls scored 0%. In the agentic loop, the same models scored up to 85%, partially narrowing the gap — though it re-opens at L2.

**4. Inverted difficulty curves exist.** phi-4-reasoning-plus: 46% L0, 80% L1, 43% L2 — it does worst on explicit instructions. glm-4.7-flash: 55% L0, 60% L1, 71% L2 — it scores highest on reasoning tasks while failing basic format compliance.

**5. Common failure patterns across models:**
- `update_mask: { paths: [...] }` — nested object that most models omit or flatten
- Single-call truncation: "add three tasks" prompts one `create_task` call instead of three
- Missing follow-up retrieval: search returns a list, model skips the subsequent `get` by ID
- ID chaining: passing returned IDs into subsequent calls (structurally impossible in single-shot)

**6. L2-07 (end-of-sprint closeout) remains unsolved.** Three sequential calls with state threading. 0/21 models fully pass it in either methodology. ernie-4.5 comes closest at 95% task score.

---

### Reproducibility

Each model was tested in a single primary run. A second run was performed for 17 models to assess stability:

- **Agentic**: Mean absolute delta of 2 percentage points. 67% of models produced identical scores. Maximum delta: 6 pp.
- **Single-shot**: 59% of models produced identical scores. Variance concentrated in reasoning/thinking models (qwen3-4b-thinking dropped from 74% to 37% across runs due to nondeterministic empty responses despite temperature=0.0).

Agentic results showed higher reproducibility, likely because the feedback loop provides self-correction opportunities. Results should be treated as point estimates.

---

### Limitations

- **Single hardware configuration**: all results on one RTX 4080 16GB system
- **8192 fixed context**: some models may perform better with longer context
- **Q4_K_M quantization**: higher-fidelity quantizations may yield different results
- **Single API schema**: results may not generalize to other MCP servers
- **LM Studio tool-training labels**: not independently verified
- **Single primary run**: no statistical confidence intervals
- **Temperature 0.0 nondeterminism**: quantized inference produces nondeterministic behavior despite zero temperature

---

### Reproduce

All code, tasks, and results are open source:

```bash
git clone https://github.com/3615-computer/workunit-benchmarks
cd workunit-benchmarks/local-llm-mcp-calling
pip install openai rich requests

# Agentic (primary)
python scripts/runner_v2_agentic.py --models models.txt --token <mcp-token> --refresh-token <refresh-token>

# Single-shot (reference)
python scripts/runner_v1_singleshot.py --models models.txt --token <mcp-token> --refresh-token <refresh-token>
```

Requires LM Studio with the target models available locally. See the repo README for setup options (local dev stack or production endpoint).

**Repository**: https://github.com/3615-computer/workunit-benchmarks

- Task definitions: `local-llm-mcp-calling/tasks/*.json`
- Results: `local-llm-mcp-calling/results/v1_singleshot/` and `results/v2_agentic/`
- Aggregated reports: `results/*/aggregated_report.md`
- Graph scripts: `reports/images/gen_graph*.py`

Questions and feedback welcome.

— Alyx

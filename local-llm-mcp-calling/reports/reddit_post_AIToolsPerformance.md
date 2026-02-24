# Reddit Post — r/AIToolsPerformance (FINAL)
# https://www.reddit.com/r/AIToolsPerformance/
# Angle: methodology + comparative performance, data-first

---

## TITLE

19 local LLMs on real MCP tool calling — 3 levels (explicit, natural language, reasoning), single-shot vs agentic. Same models, wildly different rankings.

---

## POST BODY

### What this is

A benchmark comparing how 19 local LLMs perform on real MCP (Model Context Protocol) tool calling, run twice with two different evaluation methodologies:

1. **Single-shot**: one API call per task, score the first response
2. **Agentic loop**: model receives actual tool results after each call and continues until the task passes or a 5-minute timeout is hit

Both runs used the same 19 models, same 28 tasks, and the same live MCP server.

---

### Hardware and infrastructure

- **GPU**: RTX 4080 16GB
- **RAM**: 64GB system
- **Model runtime**: LM Studio (local, OpenAI-compatible API at `http://localhost:1234/v1`)
- **Context length**: 8192 tokens for all models (loaded programmatically via LM Studio management API)
- **MCP server**: A real project management MCP server running locally (`http://localhost:9000/mcp`), 19 tools
- **Runner**: Custom Python script using the `openai` client library for model calls and streamable HTTP for MCP
- **Temperature**: 0.0 for all models
- **Task timeout**: 300s per task (agentic run only)

All models were unloaded from VRAM before each run and reloaded at a fixed 8192 context. The test database was wiped between each model run to prevent data bleed-through.

---

### Models tested

19 models total. 5 are not trained for tool calling (per LM Studio metadata), included to measure whether reasoning capability substitutes for tool-call fine-tuning. All models run at Q4_K_M quantization unless noted otherwise.

| Model | Size | Quant | Tool-trained |
|-------|------|-------|-------------|
| ibm/granite-4-h-tiny | 7B | Q4_K_M | ✅ |
| qwen/qwen3-coder-30b | 30B | Q4_K_M | ✅ |
| mistralai/magistral-small-2509 | 24B | Q4_K_M | ✅ |
| qwen/qwen3-4b-thinking-2507 | 4B | Q4_K_M | ✅ |
| openai/gpt-oss-20b | 20B | MXFP4 | ✅ |
| mistralai/ministral-3-14b-reasoning | 14B | Q4_K_M | ✅ |
| mistralai/ministral-3-3b | 3B | Q4_K_M | ✅ |
| essentialai/rnj-1 | 8.3B | Q4_K_M | ✅ |
| nvidia/nemotron-3-nano | 30B | Q4_K_M | ✅ |
| zai-org/glm-4.6v-flash | 9.4B | Q4_K_M | ✅ |
| zai-org/glm-4.7-flash | 30B | Q4_K_M | ✅ |
| bytedance/seed-oss-36b | 36B | Q4_K_M | ✅ |
| mistralai/devstral-small-2-2512 | 24B | Q3_K_L | ✅ |
| qwen/qwen3-coder-next | 80B | Q4_K_M | ✅ |
| baidu/ernie-4.5-21b-a3b | 21B | Q4_K_M | ❌ |
| google/gemma-3-12b | 12B | Q4_K_M | ❌ |
| microsoft/phi-4-reasoning-plus | 15B | Q4_K_M | ❌ |
| qwen/qwen2.5-coder-32b | 32B | Q4_K_M | ❌ |
| deepseek/deepseek-r1-0528-qwen3-8b | 8B | Q4_K_M | ❌ |

---

### Task design

**28 tasks across 3 difficulty levels**, targeting a real project management API with 19 tools (create/get/update for projects, workunits, tasks, assets; search; save_context; directory management).

**Level 0 — Explicit** (11 tasks): Exact tool name and all parameters specified in the prompt. Tests format compliance and basic tool call emission.

Example: *"Call `create_workunit` with name='Hello World', problem_statement='Users can't track work', success_criteria='Workunit visible in dashboard', priority='normal'"*

**Level 1 — Natural language** (10 tasks): Human-phrased request with relevant information present but unstructured. Model must identify the correct tool and map natural language to parameter names and values.

Example: *"Create a workunit called 'Fix Login Page Bug'. Problem: users can't log in with special characters. Done when all character types work with regression tests. High priority."*

**Level 2 — Reasoning** (7 tasks): High-level goal with no tool names or parameter hints. Model must plan a multi-step sequence, infer which tools to call, and chain IDs returned from earlier calls into subsequent ones.

Example: *"End of sprint. Mark all todo tasks done, save a summary of what was accomplished, and complete the workunit."*

**Scoring**: Each task is scored 0-100%. Tasks with multiple required steps award partial credit (e.g., completing 2 of 3 steps). A task "passes" only at 100%. The L0/L1/L2 columns in the results tables show **binary pass rates** — the percentage of tasks fully passed. The **Overall Score** averages each level's mean task score (including partial credit), then averages those three level scores. This means Overall can be higher than you'd expect from the pass rate columns alone. The repo's `aggregated_report.md` shows both pass rates and scores per level for full transparency.

**Validation**: Automated — each task defines a required sequence of tool calls and argument constraints. The runner collects all calls made during the task and checks them against the criteria.

The hardest patterns empirically:
- `update_mask: { paths: ["status", "completion_notes"] }` — a nested object that most models either omit or flatten incorrectly
- ID chaining: use the `id` returned by `create_project` as the `project_id` argument to `create_workunit`
- Multiple sequential calls from a single prompt (e.g. "add three tasks" requires three `create_task` calls)
- Two-step retrieval: search returns a list, then `get_workunit` must be called with the specific ID

---

### Methodology: single-shot vs. agentic

**Single-shot**: The model receives the system prompt, the tool definitions, and the user task. It makes one (or more, if it emits multiple tool calls in one response) calls, then we score whatever it produced. No feedback. No continuation. This represents the worst case: using a model directly without an agentic framework.

**Agentic loop**: After each tool call, the runner executes the call against the real MCP server and feeds the result back as a `tool` role message. The model can continue calling tools until the task validation passes or the 300s timeout is hit. The runner exits immediately when validation passes (early exit), so timing reflects actual time-to-completion, not time-to-timeout. This represents realistic usage inside an agentic framework.

Both runs used `temperature=0.0`. The agentic run also resets the test database between each model and uses `max_tokens=4096` per completion.

---

### Results

![Agentic pass rate by difficulty level — 19 models](images/graph2_level_breakdown_agentic.png)

**Agentic loop (primary results):**

| Model | Quant | L0 Pass% | L1 Pass% | L2 Pass% | Overall Score |
|-------|-------|---------|---------|---------|--------------|
| ibm/granite-4-h-tiny | Q4_K_M | 100% | 100% | 57% | **89%** |
| qwen/qwen3-coder-30b | Q4_K_M | 100% | 90% | 57% | **88%** |
| mistralai/magistral-small-2509 | Q4_K_M | 100% | 100% | 43% | **85%** |
| qwen/qwen3-4b-thinking-2507 | Q4_K_M | 100% | 80% | 57% | **85%** |
| openai/gpt-oss-20b | MXFP4 | 100% | 80% | 43% | **85%** |
| mistralai/ministral-3-14b-reasoning | Q4_K_M | 100% | 90% | 29% | **84%** |
| baidu/ernie-4.5-21b-a3b ❌ | Q4_K_M | 100% | 100% | 29% | **83%** |
| mistralai/ministral-3-3b | Q4_K_M | 91% | 90% | 29% | **81%** |
| google/gemma-3-12b ❌ | Q4_K_M | 91% | 80% | 29% | **78%** |
| essentialai/rnj-1 | Q4_K_M | 100% | 80% | 0% | **77%** |
| nvidia/nemotron-3-nano | Q4_K_M | 100% | 60% | 14% | **71%** |
| zai-org/glm-4.6v-flash | Q4_K_M | 91% | 60% | 14% | **68%** |
| microsoft/phi-4-reasoning-plus ❌ | Q4_K_M | 46% | 80% | 43% | **64%** |
| zai-org/glm-4.7-flash | Q4_K_M | 55% | 50% | 71% | **61%** |
| qwen/qwen2.5-coder-32b ❌ | Q4_K_M | 91% | 50% | 14% | **58%** |
| deepseek/deepseek-r1-0528-qwen3-8b ❌ | Q4_K_M | 18% | 0% | 0% | **6%** |
| bytedance/seed-oss-36b | Q4_K_M | 0% | 0% | 0% | **0%** |
| mistralai/devstral-small-2-2512 | Q3_K_L | — | — | — | **—** |
| qwen/qwen3-coder-next | Q4_K_M | — | — | — | **—** |

❌ = not trained for tool calling
— = test pending

**Single-shot (reference):**

| Model | Quant | L0 Pass% | L1 Pass% | L2 Pass% | Overall Score |
|-------|-------|---------|---------|---------|--------------|
| mistralai/ministral-3-3b | Q4_K_M | 100% | 90% | 57% | **89%** |
| mistralai/magistral-small-2509 | Q4_K_M | 100% | 90% | 0% | **78%** |
| mistralai/ministral-3-14b-reasoning | Q4_K_M | 100% | 90% | 0% | **78%** |
| qwen/qwen3-4b-thinking-2507 | Q4_K_M | 100% | 80% | 0% | **74%** |
| essentialai/rnj-1 | Q4_K_M | 100% | 80% | 0% | **74%** |
| ibm/granite-4-h-tiny | Q4_K_M | 100% | 80% | 0% | **73%** |
| openai/gpt-oss-20b | MXFP4 | 100% | 70% | 0% | **72%** |
| qwen/qwen3-coder-30b | Q4_K_M | 100% | 80% | 0% | **71%** |
| bytedance/seed-oss-36b | Q4_K_M | 100% | 80% | 0% | **71%** |
| zai-org/glm-4.6v-flash | Q4_K_M | 82% | 80% | 0% | **67%** |
| nvidia/nemotron-3-nano | Q4_K_M | 91% | 60% | 0% | **59%** |
| microsoft/phi-4-reasoning-plus ❌ | Q4_K_M | 55% | 70% | 0% | **48%** |
| zai-org/glm-4.7-flash | Q4_K_M | 64% | 40% | 0% | **44%** |
| qwen/qwen2.5-coder-32b ❌ | Q4_K_M | 64% | 40% | 0% | **38%** |
| deepseek/deepseek-r1-0528-qwen3-8b ❌ | Q4_K_M | 9% | 0% | 0% | **3%** |
| baidu/ernie-4.5-21b-a3b ❌ | Q4_K_M | 0% | 0% | 0% | **0%** |
| google/gemma-3-12b ❌ | Q4_K_M | 0% | 0% | 0% | **0%** |
| mistralai/devstral-small-2-2512 | Q3_K_L | — | — | — | **—** |
| qwen/qwen3-coder-next | Q4_K_M | — | — | — | **—** |

❌ = not trained for tool calling
— = test pending

Single-shot L2 was 0% for 16 of 17 models. The one exception: mistralai/ministral-3-3b scored 57% (4/7 tasks). On inspection, the 4 tasks it passes don't require ID chaining — they're standalone calls (bootstrap project, find stale work, document a decision, create project with linked asset). The tasks that do require chaining an `id` from one call into the next were 0% across the board in single-shot, as expected: the model has no way to observe intermediate results in a single-response evaluation.

Single-shot L0 and L1 results are directionally consistent with the agentic run, with two notable exceptions: ernie-4.5-21b and gemma-3-12b scored 0% in single-shot (never emitted tool calls at all) but score 83% and 78% respectively in the agentic run. The additional context from seeing tool results in the loop appears to help them emit tool calls on subsequent turns.

---

### Single-shot vs agentic — overall delta

![Single-shot vs Agentic Overall Score — 19 models](images/graph1_ss_vs_ag_overall.png)

### Tool-trained vs not tool-trained

![Tool-trained vs not tool-trained — SS and agentic performance](images/graph3_trained_vs_control.png)

### Key findings

**The evaluation methodology is load-bearing for L2.** Single-shot gives 0% at L2 for 16 of 17 models. The one exception (ministral-3-3b at 57%) passes only the tasks that don't require ID chaining — the chaining tasks are 0% across the board. The agentic loop unlocks L2 for the better models (57% for granite, qwen3-coder, qwen3-thinking), making methodology choice a first-order concern when interpreting tool-calling benchmarks.

**Size does not predict performance.** The top overall performer is ibm/granite-4-h-tiny at 7B (89%). Several models in the 20-32B range score below it. Tool-call fine-tuning is a stronger predictor of L0/L1 performance than raw parameter count.

**Tool training has variable impact depending on methodology.** In single-shot, the models not trained for tool calling that never emitted tool calls (gemma-3-12b, ernie-4.5-21b) score 0%. In the agentic loop, they score 78% and 83% respectively. The agentic loop provides enough additional context that capable base models can figure out the tool call format, partially narrowing the gap with explicitly tool-trained models — though the gap re-opens at L2.

**L2-07 (three-step sequential closeout) passes 0/17 models in the agentic loop.** The task requires: (1) update all tasks to done, (2) save a context atom, (3) mark the workunit completed. Each step depends on state from the previous. No model in this test completes all three reliably. This is either a fundamental limit of 8192-context 3-32B models on 3-step sequential tasks, or a prompting/task-design issue — the data doesn't distinguish.

**glm-4.7-flash L2 > L0/L1.** This model scores 55% at L0, 50% at L1, and 71% at L2 — the only model with an inverted difficulty curve. The specific L2 tasks it passes (bootstrap project, break down feature, find stale work, architectural decision, project with linked asset) are open-ended reasoning tasks, while the L0/L1 tasks it fails involve specific format requirements. Hypothesis: the model was fine-tuned more heavily on open-ended agentic scenarios than on structured tool-call format compliance.

---

### Limitations

- **Single hardware configuration**: all results on one 4080 16GB system; different quantizations or hardware may produce different results
- **8192 fixed context**: some models may perform better with longer context; the limit was chosen to fit all 19 models on the GPU
- **Single run per model**: no statistical averaging across multiple runs; results should be treated as a point estimate
- **LM Studio tool-training labels**: "tool-trained" classification is LM Studio's metadata, not independently verified
- **Single API schema**: the API schema (update_mask pattern, context atoms, etc.) is specific to the project management server used; results may not generalize to other MCP servers

---

### Reproduce it

Everything is open source:

```bash
git clone https://github.com/3615-computer/workunit-benchmarks
cd workunit-benchmarks/local-llm-mcp-calling
pip install openai rich requests

python scripts/runner_v2_agentic.py --models models.txt --token <mcp-token> --refresh-token <refresh-token>
```

Requires LM Studio with the target models available locally. The benchmark runs against a real project management MCP server. See the repo README for setup options (local dev stack or production endpoint). The tasks exercise a real API that needs to authenticate calls and maintain state between tool invocations.

Task definitions: `tasks/*.json` (plain JSON, every prompt and validation criterion)
Results: `results/v2_agentic/*.json` (per-model, per-level)
Aggregated report: `results/v2_agentic/aggregated_report.md`

Happy to answer questions about methodology or share raw result files.

— Alyx

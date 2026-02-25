# Reddit Post — r/LocalLLaMA
# https://www.reddit.com/r/LocalLLaMA/

---

## TITLE

I tested 21 local LLMs on real MCP tool calling — 3B to 80B, single-shot vs agentic. qwen3-coder ties at 92%, a 4B model matches a 7B at 85%, and two "not tool-trained" models beat most of the field.

---

## POST BODY

I benchmarked 21 local LLMs on real MCP tool calling — not synthetic function-calling evals, but actual calls against a live API with 19 tools, real validation, and real results.

Each model was tested twice: single-shot (one API call, score the first response) and agentic (model gets tool results back, keeps going until it passes or times out). Same 21 models, same 28 tasks, same MCP server.

---

### The setup

**21 models** on a 4080 16GB + 64GB RAM, running via LM Studio, talking to a real MCP server (a project management API with 19 tools) through a custom Python runner. All models at Q4_K_M quantization unless noted otherwise. Temperature 0.0 across the board.

5 models are **not trained for tool calling** (per LM Studio metadata) — included as a control group to see if raw reasoning compensates for missing fine-tuning.

**Three difficulty levels:**

**Level 0 — Explicit** (11 tasks): I tell the model exactly which tool to call and what parameters to use. Tests: can it follow instructions and emit a valid tool call?
> *"Call `create_workunit` with name='Hello World', problem_statement='Users can't track work', success_criteria='Workunit visible in dashboard', priority='normal'"*

**Level 1 — Natural language** (10 tasks): I describe what I want in plain English. The model figures out which tool to use and maps my words to the right parameters.
> *"Create a workunit called 'Fix Login Page Bug'. Problem: users can't log in with special characters. Done when all character types work with regression tests. High priority."*

**Level 2 — Reasoning** (7 tasks): High-level goal. The model has to plan multiple steps, call tools in sequence, and pass IDs from one call to the next. This is where most models fall apart.
> *"End of sprint. Mark all todo tasks done, save a summary of what was accomplished, and complete the workunit."*

**Two methods:**

**Single-shot**: One chance. Send the task, score the response. No feedback, no retries.

**Agentic loop**: The model calls a tool, gets the real result back, and can keep going — correcting mistakes, chaining results, calling more tools. 5 minute timeout per task.

---

### Results — Agentic loop (primary)

![Single-shot vs Agentic Overall Score — 21 models](images/graph1_ss_vs_ag_overall.png)

| Model | Size | Quant | Tool | SS Overall | AG Overall |
|-------|------|-------|------|-----------|-----------|
| qwen/qwen3-coder-30b | 30B | Q4_K_M | Yes | 73% | **92%** |
| qwen/qwen3-coder-next | 80B | Q4_K_M | Yes | 81% | **92%** |
| baidu/ernie-4.5-21b-a3b | 21B | Q4_K_M | No* | 0% | **85%** |
| qwen/qwen3-4b-thinking-2507 | 4B | Q4_K_M | Yes | 37% | **85%** |
| ibm/granite-4-h-tiny | 7B | Q4_K_M | Yes | 73% | **85%** |
| openai/gpt-oss-20b | 20B | MXFP4 | Yes | 76% | **85%** |
| mistralai/ministral-3-14b-reasoning | 14B | Q4_K_M | Yes | 78% | **84%** |
| mistralai/magistral-small-2509 | 24B | Q4_K_M | Yes | 78% | **82%** |
| mistralai/devstral-small-2-2512 | 24B | Q3_K_L | Yes | 79% | **82%** |
| mistralai/ministral-3-3b | 3B | Q4_K_M | Yes | 76% | **81%** |
| google/gemma-3-12b | 12B | Q4_K_M | No* | 0% | **80%** |
| qwen/qwen3.5-35b-a3b | 35B | Q4_K_M | Yes | 65% | **77%** |
| nvidia/nemotron-3-nano | 30B | Q4_K_M | Yes | 51% | **77%** |
| essentialai/rnj-1 | 8.3B | Q4_K_M | Yes | 74% | **77%** |
| liquid/lfm2-24b-a2b | 24B | Q4_K_M | Yes | 78% | **73%** |
| zai-org/glm-4.6v-flash | 9.4B | Q4_K_M | Yes | 61% | **70%** |
| zai-org/glm-4.7-flash | 30B | Q4_K_M | Yes | 44% | **63%** |
| microsoft/phi-4-reasoning-plus | 15B | Q4_K_M | No* | 38% | **62%** |
| qwen/qwen2.5-coder-32b | 32B | Q4_K_M | No* | 38% | **58%** |
| deepseek/deepseek-r1-0528-qwen3-8b | 8B | Q4_K_M | No* | 3% | **0%** |
| bytedance/seed-oss-36b | 36B | Q4_K_M | Yes | 71% | **0%** |

*\* = not trained for tool calling (per LM Studio metadata)*

**How scoring works:** L0/L1/L2 columns show binary pass rates — percentage of tasks fully passed. The Overall column averages each level's mean *score* (including partial credit), then averages those three level scores. So Overall can be higher than pass rates suggest because partial completions count. Full breakdown in the repo's `aggregated_report.md`.

---

### Level breakdown (agentic)

![Agentic pass rate by difficulty level](images/graph2_level_breakdown_agentic.png)

### Tool-trained vs not tool-trained

![Tool-trained vs not tool-trained — SS and agentic performance](images/graph3_trained_vs_control.png)

---

### What I found

**qwen3-coder leads at 92%.** Both the 30B and the 80B (CPU-offloaded) variant tie at the top. They're the only models hitting 71% at L2 — they handle multi-step ID chaining and complex reasoning tasks where most models plateau at 29-43%.

**A 4B model ties with a 7B at 85%.** qwen3-4b-thinking (4B) matches granite-4-h-tiny (7B) and gpt-oss (20B). Size isn't the predictor — tool-call fine-tuning and architecture matter more. The 32B qwen2.5-coder scores 58%.

**The agentic loop changes everything for L2.** In single-shot, 20 of 21 models scored 0% at L2. The exception: lfm2-24b hit 57%, the only model managing L2 tasks without seeing intermediate results. With the agentic loop, the top models reach 71% at L2 because they can observe IDs returned from one call and feed them into the next. That's the fundamental unlock — single-shot L2 is structurally impossible for tasks that require ID chaining.

**Two "not tool-trained" models outperform most of the field.** ernie-4.5-21b scored 0% in single-shot — never emitted a tool call, just wrote helpful text. In the agentic loop: 85%, tied for 3rd place. gemma-3-12b: same pattern, 0% → 80%. The agentic context apparently gives them enough signal to figure out they're supposed to call tools. Whether that's a win for agentic evaluation or exposes single-shot as insufficient is worth discussing.

**Not tool-trained still hurts at L2.** ernie and gemma both fall to 29-43% at L2. The tool-trained models that score well at L2 (qwen3-coder at 71%, qwen3-4b at 57%) have a clear edge on multi-step reasoning chains.

**DeepSeek-R1 (8B, not tool-trained) hallucinated tool names.** It called a tool literally named `tool_name` on most tasks. Understood the shape of a tool call — format, structure, everything — but never read the actual function names from the tool list.

**phi-4-reasoning-plus has an inverted difficulty curve.** 46% at L0 (explicit instructions), 80% at L1 (natural language), 43% at L2. It does worst when told exactly what to do. Something about the explicit instruction format likely conflicts with its training distribution.

**glm-4.7-flash scores higher at L2 (71%) than L0 (55%) or L1 (60%).** It passes 5 of 7 reasoning tasks while fumbling basic explicit tool calls. The reasoning tasks seem to activate something that the simpler tasks don't.

**seed-oss-36b is still the most bizarre result.** 71% overall in single-shot (100% L0, 80% L1). 0% across all 28 tasks in the agentic loop — never emitted a single tool call. The only difference: the agentic runner feeds tool results back. Somehow receiving tool results caused the model to completely stop calling tools.

**L2-07 (sprint closeout) remains unsolved.** Three sequential calls with state threading — mark tasks done, save a context summary, complete the workunit. 0/21 models fully pass it, though ernie-4.5 gets closest at 95% task score.

**Reproducibility note:** I retested 17 models across two runs. Agentic results are stable — mean delta of 2 percentage points, 67% of models identical. Single-shot has more variance, especially reasoning/thinking models (qwen3-4b dropped from 74% to 37% across runs due to nondeterministic empty responses, despite temperature=0.0). Treat results as point estimates.

---

### What I couldn't test

My 4080 16GB tops out around 36B at Q4 (80B with heavy CPU offloading). Would love community results for:
- Llama 3.3 70B
- Qwen2.5-72B
- DeepSeek-R1 671B
- Llama 4 Scout/Maverick

The benchmark is ready to run if you have the hardware.

---

### Run it yourself

All code, tasks, and results are open source: https://github.com/3615-computer/workunit-benchmarks

```bash
git clone https://github.com/3615-computer/workunit-benchmarks
cd workunit-benchmarks/local-llm-mcp-calling
pip install openai rich requests
python scripts/runner_v2_agentic.py --models models.txt --token <mcp-token> --refresh-token <refresh-token>
```

Requires LM Studio with the target models available locally. See the repo README for setup options (local dev stack or production endpoint).

---

### Questions for the community

1. **seed-oss-36b** — 71% single-shot, 0% agentic. Anyone run this model successfully in an agentic framework?
2. **L2-07 (sprint closeout)** — 0/21 pass. Is a 3-step sequential task with state threading genuinely too hard for <80B models at 8K context, or is this a prompting issue?
3. **What local models are you using for MCP tool calling in practice?** Especially curious about 70B+ results.

Drop results in the comments if you run it on hardware I don't have. I'll update the repo.

— Alyx

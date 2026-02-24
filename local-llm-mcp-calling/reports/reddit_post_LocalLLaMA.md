# Reddit Post — r/LocalLLaMA (FINAL)
# https://www.reddit.com/r/LocalLLaMA/

---

## TITLE

I tested 19 local LLMs on real tool calling: direct, NLP, and multi-step reasoning (single-shot & agentic). A 7B model topped the leaderboard.

---

## POST BODY

I benchmarked 19 local LLMs on real MCP tool calling — not synthetic function-calling evals, but actual calls against a real API with 19 tools, real validation, and real results.

I ran each model twice. First single-shot (one API call, score the first response). Then agentic (model gets tool results back, keeps going until it passes or times out). Same 19 models, same 28 tasks, same MCP server.

The methodology difference changes everything.

---

### The setup

**19 models** on a 4080 16GB + 64GB RAM, running via LM Studio, talking to a real MCP server (a project management API with 19 tools) through a custom Python runner. All models run at Q4_K_M quantization unless noted otherwise.

5 models are **not trained for tool calling** (per LM Studio metadata) — included to test whether raw reasoning ability compensates for missing fine-tuning.

**Three difficulty levels:**

**Level 0 — Explicit** (11 tasks): I tell the model exactly which tool to call and what parameters to use. Tests: can it follow instructions and emit a valid tool call? Most models nail this.
> *"Call `create_workunit` with name='Hello World', problem_statement='Users can't track work', success_criteria='Workunit visible in dashboard', priority='normal'"*

**Level 1 — Natural language** (10 tasks): I describe what I want in plain English. The model has to figure out which tool to use and map my words to the right parameters. Harder, but most tool-trained models handle it.
> *"Create a workunit called 'Fix Login Page Bug'. Problem: users can't log in with special characters. Done when all character types work with regression tests. High priority."*

**Level 2 — Reasoning** (7 tasks): I give a high-level goal like 'close out the sprint.' The model has to plan multiple steps, call tools in sequence, and pass IDs from one call to the next. This is where most models fall apart.
> *"End of sprint. Mark all todo tasks done, save a summary of what was accomplished, and complete the workunit."*

**Two methods:**

**Single-shot**: The model gets one chance. I send the task, it responds, done. No feedback, no retries. If it gets it wrong, that's the score.

**Agentic loop**: The model calls a tool, gets the real result back, and can keep going (calling more tools, correcting mistakes, chaining results, etc). Like how you'd actually use it in an agent framework. 5 minute timeout per task.

---

### Results — Single-shot vs. Agentic

![Single-shot vs Agentic Overall Score — 19 models](images/graph1_ss_vs_ag_overall.png)

The left column is single-shot (first response only). Right column is agentic (full loop with tool results fed back).

| Model | Size | Quant | Tool-trained | SS L0 | SS L1 | SS L2 | SS Overall | → | AG L0 | AG L1 | AG L2 | AG Overall |
|-------|------|-------|-------------|-------|-------|-------|------------|---|-------|-------|-------|------------|
| ibm/granite-4-h-tiny | 7B | Q4_K_M | ✅ | 100% | 80% | 0% | **73%** | → | 100% | 100% | 57% | **89%** |
| qwen/qwen3-coder-30b | 30B | Q4_K_M | ✅ | 100% | 80% | 0% | **71%** | → | 100% | 90% | 57% | **88%** |
| mistralai/magistral-small-2509 | 24B | Q4_K_M | ✅ | 100% | 90% | 0% | **78%** | → | 100% | 100% | 43% | **85%** |
| qwen/qwen3-4b-thinking-2507 | 4B | Q4_K_M | ✅ | 100% | 80% | 0% | **74%** | → | 100% | 80% | 57% | **85%** |
| openai/gpt-oss-20b | 20B | MXFP4 | ✅ | 100% | 70% | 0% | **72%** | → | 100% | 80% | 43% | **85%** |
| mistralai/ministral-3-14b-reasoning | 14B | Q4_K_M | ✅ | 100% | 90% | 0% | **78%** | → | 100% | 90% | 29% | **84%** |
| baidu/ernie-4.5-21b-a3b | 21B | Q4_K_M | ❌* | 0% | 0% | 0% | **0%** | → | 100% | 100% | 29% | **83%** |
| mistralai/ministral-3-3b | 3B | Q4_K_M | ✅ | 100% | 90% | 57% | **89%** | → | 91% | 90% | 29% | **81%** |
| google/gemma-3-12b | 12B | Q4_K_M | ❌* | 0% | 0% | 0% | **0%** | → | 91% | 80% | 29% | **78%** |
| essentialai/rnj-1 | 8.3B | Q4_K_M | ✅ | 100% | 80% | 0% | **74%** | → | 100% | 80% | 0% | **77%** |
| nvidia/nemotron-3-nano | 30B | Q4_K_M | ✅ | 91% | 60% | 0% | **59%** | → | 100% | 60% | 14% | **71%** |
| zai-org/glm-4.6v-flash | 9.4B | Q4_K_M | ✅ | 82% | 80% | 0% | **67%** | → | 91% | 60% | 14% | **68%** |
| microsoft/phi-4-reasoning-plus | 15B | Q4_K_M | ❌* | 55% | 70% | 0% | **48%** | → | 46% | 80% | 43% | **64%** |
| zai-org/glm-4.7-flash | 30B | Q4_K_M | ✅ | 64% | 40% | 0% | **44%** | → | 55% | 50% | 71% | **61%** |
| qwen/qwen2.5-coder-32b | 32B | Q4_K_M | ❌* | 64% | 40% | 0% | **38%** | → | 91% | 50% | 14% | **58%** |
| deepseek/deepseek-r1-0528-qwen3-8b | 8B | Q4_K_M | ❌* | 9% | 0% | 0% | **3%** | → | 18% | 0% | 0% | **6%** |
| bytedance/seed-oss-36b | 36B | Q4_K_M | ✅ | 100% | 80% | 0% | **71%** | → | 0% | 0% | 0% | **0%** |
| mistralai/devstral-small-2-2512 | 24B | Q3_K_L | ✅ | — | — | — | **—** | → | — | — | — | **—** |
| qwen/qwen3-coder-next | 80B | Q4_K_M | ✅ | — | — | — | **—** | → | — | — | — | **—** |

*\* = not trained for tool calling (per LM Studio metadata)*
*— = test pending*

**How scoring works:** The L0/L1/L2 columns show **binary pass rates** — the percentage of tasks the model fully passed at each level. The **Overall** column is different: it averages each level's *score* (which includes partial credit for completing some steps of a multi-step task), then averages those three level scores. This is why Overall can be higher than you'd expect from the pass rate columns alone — a model that partially completes several tasks gets credit even if it doesn't fully pass them. The repo's `aggregated_report.md` shows both pass rates and scores per level.

---

### Level breakdown (agentic)

![Agentic pass rate by difficulty level](images/graph2_level_breakdown_agentic.png)

### Tool-trained vs not tool-trained

![Tool-trained vs not tool-trained — SS and agentic performance](images/graph3_trained_vs_control.png)

### What I found

**The agentic loop is the difference between L2 being hard and L2 being solvable.**

In single-shot, 16 of 17 models scored 0% at L2. The one exception: ministral-3-3b hit 57% — because 4 of its 7 passes don't require ID chaining (bootstrap project, find stale work, document a decision, create project with linked asset). The ID-chaining tasks (where you need the `id` from `create_project` to pass into `create_workunit`) were 0% across the board in single-shot. With the agentic loop, granite, qwen3-coder-30b, and qwen3-4b-thinking all hit 57% at L2 including the chaining tasks. The model calls a tool, gets an ID back, uses it in the next call. That's the whole unlock.

**A 7B model tops the overall leaderboard.** ibm/granite-4-h-tiny at 89%, beating every model up to 32B. It's consistent, doesn't hallucinate tool names, handles multi-step sequences cleanly, and is fast. If you need reliable local MCP tool calling today, start here.

**The not-tool-trained plot twist.** In single-shot, ernie-4.5-21b (21B) and gemma-3-12b (12B) scored 0% — they never emitted tool calls at all, just wrote helpful text. In the agentic loop: ernie hits 83%, gemma hits 78%. The agentic runner apparently gives them enough context to figure out they're supposed to call tools. Whether that's a win for the agentic methodology or an indictment of the single-shot format is worth debating.

**Not being tool-trained still hurts at L2.** Both ernie and gemma fall to 29% at L2 — capable of basic tool use when the context is clear, but struggle with multi-step reasoning chains. The tool-trained models that score well at L2 (granite, qwen3-coder, qwen3-thinking) have a clear edge there.

**DeepSeek-R1 (8B, not tool-trained) called a tool named `tool_name`.** Literally that string, on most tasks. It understood the shape of a tool call response — format, structure, everything — but hallucinated a generic placeholder instead of reading the actual function names from the tool list. Fascinating failure mode.

**phi-4-reasoning-plus is inverted.** 46% at L0 (explicit instructions), 80% at L1 (natural language), 43% at L2. It struggles most when told exactly what to do. This is unusual enough that I suspect something about the explicit instruction format conflicts with its training distribution.

**glm-4.7-flash scores higher at L2 (71%) than L0 (55%) or L1 (50%).** It passes L2-01 through L2-05 while fumbling basic explicit tool calls. I don't have a good explanation. The reasoning tasks seem to activate something that the simpler tasks don't.

**Two tasks are the universal wall.** L1-03 ("add three tasks to a workunit") — most models call `create_task` once and stop. L1-05 ("search for a workunit then retrieve its details") — models do the search but almost universally skip the follow-up `get_workunit`. Both require deciding to make multiple sequential calls from a single user message, which appears to be a reliably hard mental model. And L2-07 (end-of-sprint closeout: mark tasks done + save context + complete workunit) — 0/17 models fully pass it even in the agentic loop. Three sequential calls with state threading. Nobody nails all three.

**seed-oss-36b is the most bizarre result.** In single-shot it scored 100% L0 and 80% L1 (71% overall) — among the better results in the single-shot run. In the agentic loop it scored 0% across all 28 tasks and never emitted a single tool call. The only thing different between runs is that the agentic runner feeds tool results back as context. Somehow receiving tool results caused the model to completely stop calling tools. If you've run this model in an agentic setup successfully, I'd genuinely like to know what setup you used.

---

### What I couldn't test

My 4080 16GB tops out around 32-36B at Q4 (80B with CPU offloading). Would love community results for:
- Llama 3.3 70B
- Qwen2.5-72B
- DeepSeek-R1 671B
- Llama 4 Scout/Maverick

**The benchmark is ready to run if you have the hardware.**

---

### Run it yourself

You can find all the code and instructions to run this yourself on the repository https://github.com/3615-computer/workunit-benchmarks

---

### Questions for the community

1. **seed-oss-36b paradox** — scored 71% overall in single-shot but 0% in the agentic loop. The only difference is getting tool results back. Anyone run this successfully in an agentic framework?
2. **L2-07 (sprint closeout)** — 0/17 pass in the agentic loop. Is a 3-step sequential task with state threading genuinely unsolvable in a single session, or is this a prompting issue?
3. **What are you actually using for local MCP in production?** Especially curious about 70B+ results.

Drop results in the comments if you run it on hardware I don't have. I'll update the repo.

— Alyx

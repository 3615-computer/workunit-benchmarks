# Reddit Post — Agentic Run Draft
# Primary target: r/LocalLLaMA
# Secondary: r/selfhosted, r/LMStudio, r/OpenSourceAI

---

## TITLE OPTIONS

1. `I benchmarked 17 local LLMs on real MCP tool calling — agentic loop, real API, full results`
2. `Which local LLMs can actually use MCP tools in an agentic loop? I tested 17 models`
3. `MCP tool calling benchmark v2: 17 local models, agentic loop (not single-shot), real results`

---

## POST BODY

---

I've been building [Workunit](https://workunit.app), a project manager designed for AI agents. You connect any AI via MCP and it can do real things — create tasks, save decisions, close out sprints. Not describe what it would do. Actually do it.

The question people always ask: *"Does it work with local models?"*

I ran a benchmark to find out. **This is v2 — agentic loop**, not single-shot. The model gets real tool results back after each call and can continue until it passes or times out.

---

### The setup

**17 models** running locally via LM Studio on a 4080 16GB + 64GB RAM. All talking to Workunit's real MCP server through a custom Python agentic runner.

5 models are a **control group** — explicitly not trained for tool use in LM Studio. Included to answer: does reasoning ability substitute for tool-call fine-tuning?

**Spoiler: mostly no. But this run is more nuanced than v1.**

---

### Three difficulty levels, 28 tasks

**Level 0 — Explicit** (11 tasks): Tell the model exactly which tool to call and all parameters.

> *"Call `create_workunit` with name='Hello World', problem_statement='...', success_criteria='...', priority='normal'"*

**Level 1 — Natural language** (10 tasks): Human-style request, unstructured. Model picks the right tool and maps description to parameters.

> *"Create a workunit called 'Fix Login Page Bug'. Problem is users can't log in with special characters. Done when all character types work with regression tests. High priority."*

**Level 2 — Reasoning** (7 tasks): High-level goal only. No tool names, no parameter hints. Model must plan the sequence and chain IDs across calls.

> *"End of sprint. Mark all todo tasks done, save a summary of what was accomplished, and complete the workunit."*

Key difference from v1: **the model gets tool results back**. If it calls `create_workunit` and gets an ID back, it can use that ID in the next call. The agentic loop stops as soon as the task passes — no need to wait for the model to stop on its own.

---

### Results

| Model | Size | Tool-trained | L0 | L1 | L2 | Overall |
|-------|------|-------------|----|----|----|----|
| ibm/granite-4-h-tiny | 7B | ✅ | 100% | 100% | 57% | **89%** |
| qwen/qwen3-coder-30b | 30B | ✅ | 100% | 90% | 57% | **88%** |
| mistralai/magistral-small-2509 | 24B | ✅ | 100% | 100% | 43% | **85%** |
| qwen/qwen3-4b-thinking-2507 | 4B | ✅ | 100% | 80% | 57% | **85%** |
| openai/gpt-oss-20b | 20B | ✅ | 100% | 80% | 43% | **85%** |
| mistralai/ministral-3-14b-reasoning | 14B | ✅ | 100% | 90% | 29% | **84%** |
| baidu/ernie-4.5-21b-a3b | 21B | ❌* | 100% | 100% | 29% | **83%** |
| mistralai/ministral-3-3b | 3B | ✅ | 91% | 90% | 29% | **81%** |
| google/gemma-3-12b | 12B | ❌* | 91% | 80% | 29% | **78%** |
| essentialai/rnj-1 | 8.3B | ✅ | 100% | 80% | 0% | **77%** |
| nvidia/nemotron-3-nano | 30B | ✅ | 100% | 60% | 14% | **71%** |
| zai-org/glm-4.6v-flash | 9.4B | ✅ | 91% | 60% | 14% | **68%** |
| microsoft/phi-4-reasoning-plus | 15B | ❌* | 46% | 80% | 43% | **64%** |
| zai-org/glm-4.7-flash | 30B | ✅ | 55% | 50% | 71% | **61%** |
| qwen/qwen2.5-coder-32b | 32B | ❌* | 91% | 50% | 14% | **58%** |
| deepseek/deepseek-r1-0528-qwen3-8b | 8B | ❌* | 18% | 0% | 0% | **6%** |
| bytedance/seed-oss-36b | 36B | ✅ | 0% | 0% | 0% | **0%** |

*\* = control group, not trained for tool use*

---

### What changed vs. single-shot

*(fill in after comparing with v1 results)*

---

### Observations

*(fill in — key things to note:)*
- granite-4-h-tiny 7B tops the leaderboard overall
- L2 is no longer 0% for everyone — several models crack it in the agentic loop
- glm-4.7-flash anomaly: 55% L0, 50% L1, but 71% L2 — better at reasoning than basics
- ernie-4.5 and gemma-3-12b (control group) scoring well at L0/L1 — worth discussing
- seed-oss-36b: 0% across the board despite being tool-trained — investigate why
- L2-07 (end-of-sprint closeout): hardest task, essentially nobody passes it

---

### What I couldn't test

My 4080 16GB tops out around 32-36B at Q4. Would love results for:
- Llama 3.3 70B
- Qwen2.5-72B
- DeepSeek-R1 671B
- Mistral Large / Mixtral 8x22B
- Llama 4 Scout/Maverick

**If you have the hardware, the benchmark is ready to run.**

---

### Reproduce it

```bash
git clone https://github.com/3615-computer/workunit-benchmarks
cd workunit-benchmarks/local-llm-mcp-calling
pip install openai rich

# Single model
python scripts/runner_v2_agentic.py --model mistralai/ministral-3-3b --token <your-token>

# All models
python scripts/runner_v2_agentic.py --models models.txt --token <your-token>
```

Requires LM Studio running locally. The runner loads/unloads models automatically, resets the DB between each model, and stops each task as soon as it passes. Task definitions are plain JSON in `benchmark/tasks/`.

---

### About Workunit

Project manager built around AI context. Each workunit has a problem statement, tasks, and a trail-of-thought the AI writes back as it works — decisions made, approaches tried, progress notes. Define the work once, any AI (Claude, GPT, local) picks it up with full context via MCP.

Built it because I was tired of re-explaining my codebase every morning. Free to start at [workunit.app](https://workunit.app).

---

### Questions for the community

1. **seed-oss-36b at 0%** — anyone else seen this? It's listed as tool-trained in LM Studio but emitted zero tool calls.
2. **glm-4.7-flash** scores higher on L2 reasoning (71%) than L0 basics (55%) — unusual pattern, curious if others have seen this with GLM models.
3. **What are you actually using for MCP in production?** Especially anything in the 70B range.

Drop results in the comments if you run it on hardware I don't have.

— Alyx

---

## NOTES FOR FINAL DRAFT

- Compare numbers directly with v1 single-shot results — the delta is the story
- Investigate seed-oss-36b 0% — was it a model load issue or genuine failure?
- L2-07 (sprint closeout): 0/17 pass — is this a task design issue or genuinely hard?
- Add screenshot of results table
- Consider framing: "agentic loop vs single-shot" angle is the hook for people who saw v1

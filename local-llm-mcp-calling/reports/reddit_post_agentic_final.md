# Reddit Post — Agentic Run Final
# Primary target: r/LocalLLaMA
# Secondary: r/selfhosted, r/LMStudio, r/OpenSourceAI

---

## TITLE

I benchmarked 17 local LLMs on real MCP tool calling — this time with a proper agentic loop. Results are surprising.

---

## POST BODY

---

I've been building [Workunit](https://workunit.app), a project manager designed for AI agents. Connect any AI via MCP and it can actually do things — create tasks, save decisions, close out sprints. The question people always ask: *"Does it work with local models?"*

I ran a benchmark to find out. Last time I used single-shot evaluation (one API call, score the first response). This time: **a real agentic loop**. The model gets tool results back after each call and can keep going until it passes or hits a 5-minute timeout. Closer to how you'd actually use these models.

The results are genuinely interesting.

---

### The setup

**17 models** on a 4080 16GB + 64GB RAM, running locally via LM Studio, all talking to Workunit's real MCP server through a custom Python runner. 5 models included as a **control group** (not trained for tool use) to test whether raw reasoning compensates for missing fine-tuning.

---

### Three difficulty levels, 28 tasks

**Level 0 — Explicit** (11 tasks): Exact tool name and parameters given. Tests whether the model can emit a valid tool call at all.

**Level 1 — Natural language** (10 tasks): Human-style request, unstructured. Model picks the right tool and maps the description to parameter names.

**Level 2 — Reasoning** (7 tasks): High-level goal only. No tool names. Model must plan the sequence, chain IDs across calls, and make decisions.

The hardest patterns across all levels:
- `update_mask: { paths: ["status", "completion_notes"] }` — nested object most models get wrong
- **ID chaining**: use the `id` from `create_project` as `project_id` in `create_workunit`
- **Multiple sequential calls from one prompt**: "add three tasks" → most models call `create_task` once and stop
- **Two-step retrieval**: "search for a workunit then get its details" → models do the search but skip the follow-up `get_workunit`

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

### What happened

**The agentic loop changed everything at L2.** In single-shot evaluation, L2 was 0% across all 17 models — harsh but fair, because complex multi-step tasks are nearly impossible without seeing intermediate results. With the agentic loop, several models crack it: granite-4-h-tiny at 57%, qwen3-coder-30b at 57%, qwen3-4b-thinking at 57%. The model calls a tool, gets the ID back, uses it in the next call. That's how agents actually work.

**A 7B model tops the leaderboard.** ibm/granite-4-h-tiny at 89% overall, beating every larger model. It's consistent, doesn't hallucinate tool names, and handles multi-step sequences cleanly. If you need reliable local MCP tool calling today, start here.

**The control group is more interesting this time.** ernie-4.5-21b-a3b (21B, not tool-trained) scores 83% — higher than most tool-trained models. gemma-3-12b (12B, not tool-trained) scores 78%. The agentic loop gives these models more chances to self-correct, and apparently their raw capability is enough at L0/L1. They both fall off at L2 (29%) but they're not the dead weight they were in single-shot.

**phi-4-reasoning-plus has an inverted score distribution.** 46% at L0 (explicit instructions), 80% at L1 (natural language), 43% at L2. It genuinely struggles when told exactly what to do but does better with human-phrased requests. Unusual, and probably says something about its training distribution.

**glm-4.7-flash is backwards.** 55% L0, 50% L1, 71% L2. It performs *better* at reasoning tasks than basic explicit tool calls. L2-02 (break down a feature into tasks), L2-03 (find stale work), L2-04 (document an architectural decision), L2-07 (sprint closeout) — it passes several of these while fumbling simple L0 tasks. I don't have a great explanation for this.

**Two L2 tasks are the universal wall.** L2-06 (triage tasks by keyword matching priority rules) and L2-07 (end-of-sprint closeout: mark tasks done + save context + complete workunit) — essentially nobody passes these. L2-07 in particular: 0/17 models fully pass it. It requires three sequential tool calls with correct state threading, and even in an agentic loop, models consistently miss the final step. This might be a task design issue; it might be genuinely hard. The data doesn't distinguish.

**seed-oss-36b scored 0% despite being listed as tool-trained.** Never emitted a single tool call across all 28 tasks. Either the LM Studio label is wrong, the model needs specific prompting I didn't provide, or it genuinely can't use tools at this quantization. If anyone has run this model successfully with MCP, I'd like to know what prompt setup you used.

**L1-03 and L1-05 remain universal trip points.** L1-03: "add three tasks to a workunit" — most models call `create_task` once and stop, apparently not inferring that "three tasks" means three separate calls. L1-05: "search for a workunit then retrieve it" — models do the search but almost universally fail to follow up with `get_workunit`. These patterns feel like training distribution issues more than capability limits.

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
python scripts/runner_v2_agentic.py --model mistralai/ministral-3-3b --token <your-mcp-token>

# All models in a file
python scripts/runner_v2_agentic.py --models models.txt --token <your-token> --refresh-token <refresh>
```

Requires LM Studio running locally. The runner:
- Unloads all models at start (clean VRAM)
- Loads each model at 8192 context via the management API
- Resets the database between models (no bleed-through)
- Stops each task as soon as it passes (no waiting for timeout)
- Saves results per model/level as JSON, commits to git incrementally

Task definitions are plain JSON in `benchmark/tasks/` — you can read every prompt and every validation criterion. Methodology is fully transparent.

---

### About Workunit

Project manager built around AI context. Each workunit has a problem statement, tasks, and a trail-of-thought the AI writes back as it works — decisions made, approaches tried, progress checkpoints. Define the work once, any AI (Claude, GPT, Gemini, or local via MCP) picks it up with full context, does the work, leaves notes for the next session.

Built it because I was tired of re-explaining my codebase every morning. Free to start at [workunit.app](https://workunit.app). The MCP server is what all these models were talking to.

---

### Questions for the community

1. **seed-oss-36b at 0%** — anyone running this successfully with tool use? What's your setup?
2. **Is L2-07 (sprint closeout) actually solvable** in a single agentic session with a 5-minute budget, or does it need a smarter prompting strategy?
3. **What are you using for MCP tool calling in production?** Especially curious about 70B+ results.

Drop your results in the comments if you run it on hardware I don't have. I'll update the repo.

— Alyx

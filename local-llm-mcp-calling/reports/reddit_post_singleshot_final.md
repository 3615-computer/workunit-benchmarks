# Reddit Post — Final Draft
# Primary target: r/LocalLLaMA
# Secondary: r/selfhosted, r/LMStudio, r/OpenSourceAI

---

## TITLE

I benchmarked 17 local LLMs on real MCP tool calling. The results are a bloodbath.

---

## POST BODY

---

I've been building [Workunit](https://workunit.app), a project manager designed for AI agents. The idea: define your work once, connect any AI via MCP, and it can actually do things — create tasks, save decisions, close out sprints. Not describe what it would do. Actually do it.

The obvious question when people try it: *"Does it work with local models?"*

I didn't know. So I spent a weekend finding out.

---

### The setup

**17 models** running locally via LM Studio on a 4080 16GB + 64GB RAM. All talking to Workunit's MCP server through a custom Python runner using LM Studio's OpenAI-compatible API.

I included 5 models as a **control group** — explicitly marked as not trained for tool use in LM Studio — to answer the question: does raw reasoning ability compensate for missing tool-call fine-tuning?

**Spoiler: no.**

---

### Three difficulty levels, 28 tasks total

**Level 0 — Explicit** (11 tasks): Tell the model exactly which tool to call and all the parameters. This tests whether it can emit a valid tool call at all.

> *"Call `create_workunit` with name='Hello World', problem_statement='Users can't track work', success_criteria='Workunit is visible in the dashboard', priority='normal'"*

**Level 1 — Natural language** (10 tasks): Human-style request with the information present but unstructured. The model has to pick the right tool and map the description to parameter names.

> *"Create a workunit called 'Fix Login Page Bug'. The problem is users can't log in with special characters in their password. It's done when all character types work and there are regression tests. High priority."*

**Level 2 — Reasoning** (7 tasks): High-level goal only. No tool names, no parameter hints. The model has to figure out the sequence, chain IDs across calls, and make decisions.

> *"End of sprint. Mark all todo tasks done, save a summary of what was accomplished, and complete the workunit."*

The hard parts that trip models up:
- `update_mask: { paths: ["status", "completion_notes"] }` — a nested object most models get wrong
- ID chaining: use the `id` from `create_project` as the `project_id` in `create_workunit`
- Multiple sequential calls from a single prompt (e.g. create 3 tasks)
- Conditional fields: `completion_notes` only when `status="completed"`

---

### Results

| Model | Size | Tool-trained | L0 | L1 | L2 | Overall |
|-------|------|-------------|----|----|----|----|
| mistralai/ministral-3-14b-reasoning | 14B | ✅ | 100% | 90% | 0% | **78%** |
| mistralai/magistral-small-2509 | 24B | ✅ | 100% | 90% | 0% | **78%** |
| mistralai/ministral-3-3b | 3B | ✅ | 100% | 90% | 0% | **76%** |
| qwen/qwen3-4b-thinking-2507 | 4B | ✅ | 100% | 80% | 0% | **74%** |
| essentialai/rnj-1 | 8.3B | ✅ | 100% | 80% | 0% | **74%** |
| ibm/granite-4-h-tiny | 7B | ✅ | 100% | 80% | 0% | **73%** |
| openai/gpt-oss-20b | 20B | ✅ | 100% | 70% | 0% | **72%** |
| qwen/qwen3-coder-30b | 30B | ✅ | 100% | 80% | 0% | **71%** |
| bytedance/seed-oss-36b | 36B | ✅ | 100% | 80% | 0% | **71%** |
| zai-org/glm-4.6v-flash | 9.4B | ✅ | 82% | 80% | 0% | **67%** |
| nvidia/nemotron-3-nano | 30B | ✅ | 91% | 60% | 0% | **59%** |
| microsoft/phi-4-reasoning-plus* | 15B | ❌ | 55% | 70% | 0% | **48%** |
| zai-org/glm-4.7-flash | 30B | ✅ | 64% | 40% | 0% | **44%** |
| qwen/qwen2.5-coder-32b* | 32B | ❌ | 64% | 40% | 0% | **38%** |
| deepseek/deepseek-r1-0528-qwen3-8b* | 8B | ❌ | 9% | 0% | 0% | **3%** |
| google/gemma-3-12b* | 12B | ❌ | 0% | 0% | 0% | **0%** |
| baidu/ernie-4.5-21b-a3b* | 21B | ❌ | 0% | 0% | 0% | **0%** |

*\* = control group, not trained for tool use*

---

### What actually happened

**Tool training is not optional.** This is the clearest finding. A 3B Mistral that's been fine-tuned for tool calling (76%) beats a 32B Qwen coder model that hasn't (38%). A 12B Gemma and 21B Ernie scored 0% — not because they're dumb, they just never emitted a tool call. They wrote helpful text descriptions of what they would do instead.

DeepSeek-R1 (8B, control group) at least tried — it called a tool named `tool_name` on most tasks. Literally `tool_name`. It understood the shape of the response but hallucinated a generic placeholder instead of reading the actual function names. Fascinating failure mode.

Qwen2.5-coder-32b called `get_weather` when asked to save a context atom. I don't know where that came from.

**L1-03 and L1-05 are the universal trip points for everyone.** L1-03 asks for three tasks to be created from a single prompt — most models call `create_task` once and stop. L1-05 asks the model to search for a workunit and then retrieve it — almost every model does the search but never follows up with `get_workunit`. Both require the model to decide to make multiple calls from a single user message, which is apparently a hard mental model to adopt.

**Level 2 was a wall for everyone. Literally everyone. 0/17 models passed a single L2 task.**

But this might be a benchmark design issue more than a model capability issue. L2 tasks require the model to plan a 3-4 step sequence and chain IDs — but the benchmark makes a single API call and evaluates the first response. Real agentic usage gives the model tool results back and lets it continue. My guess is several of these models would handle L2 fine in a real agentic loop. The single-shot evaluation is harsh.

That said — if you're plugging a local model directly into MCP with no agentic framework, single-shot is exactly what you get on complex tasks.

**The Mistral family is suspiciously good across all sizes.** 3B, 14B, and 24B all land in the top 3. Consistent, reliable, minimal hallucination. If you're building something that needs local MCP tool calling today, start here.

---

### What I couldn't test

My 4080 16GB tops out around 32-36B at Q4. I'd love results for:
- Llama 3.3 70B
- Qwen2.5-72B
- DeepSeek-R1 671B (obviously)
- Mistral Large / Mixtral 8x22B
- Llama 4 Scout/Maverick

**If you have the hardware, the benchmark is ready to run.** Everything is in the repo — task definitions, validation logic, runner script, the works. Just point it at your LM Studio instance.

---

### Reproduce it

```bash
git clone https://github.com/3615-computer/workunit
cd workunit/benchmark
pip install openai rich

# Single model
python scripts/runner.py --model mistralai/ministral-3-3b

# All models in models.txt
python scripts/runner.py --models models.txt
```

Requires LM Studio running locally with your models loaded. The runner handles model switching automatically — it just changes the `model` field in the API request and LM Studio unloads/loads accordingly.

Task definitions are plain JSON in `benchmark/tasks/` — you can read exactly what each prompt says and what the validation criteria are. Methodology is fully transparent.

---

### About Workunit

It's a project manager built around AI context. Each workunit has a problem statement, tasks, and a trail-of-thought that the AI writes back as it works — decisions made, approaches tried, progress checkpoints. The idea is you define the work once and any AI (Claude, GPT, Gemini, or local via MCP) picks it up with full context, does the work, and leaves notes for the next session.

I built it because I was tired of re-explaining my codebase to Claude every morning.

Free to start at [workunit.app](https://workunit.app). The MCP server is what all these models were talking to.

---

### Questions I'd love the community's take on

1. **Is L2 actually a fair test?** Single-shot multi-step tool chaining vs. agentic loop — are these even the same task?
2. **Which models are you using successfully with MCP today?** Especially curious about anything in the 70B range.
3. **Does the control group surprise you?** phi-4-reasoning-plus is a genuinely capable reasoning model and it scored 48%. DeepSeek-R1 at 3%. Raw reasoning does not substitute for tool-call training.

Drop your results in the comments if you run it on hardware I don't have. I'll update the repo.

— Alyx

---

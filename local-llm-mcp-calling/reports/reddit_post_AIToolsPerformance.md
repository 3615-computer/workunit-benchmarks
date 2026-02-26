<!-- Target: r/AIToolsPerformance -->
<!-- Tone: First-person, methodology-focused, evaluation insights -->
<!-- Graphs: graph1 (hero), graph4 (agentic lift) -->

# I benchmarked 21 local LLMs on real MCP tool calling — single-shot evals understate real performance by 37pp on reasoning tasks

![Single-shot vs agentic overall scores for all 21 models](images/graph1_ss_vs_ag_overall.png)

*Single-shot (orange) vs agentic (blue) overall scores. Every model improved with agentic eval — the question is by how much.*

---

**TL;DR**: I built a tool-calling benchmark using a real MCP API (19 tools, real database state) and tested 21 local LLMs under two methodologies: single-shot (one response, no feedback) and agentic loop (iterative with real API responses). The agentic methodology produced higher scores for every model — +5.0pp on explicit tasks, +12.6pp on natural language tasks, and **+37.3pp on multi-step reasoning tasks**. Single-shot L2 (reasoning) pass rate: 2.0%. Agentic L2 pass rate: 49.7%. If you're evaluating models for agent deployment using single-shot benchmarks, you're likely making wrong decisions.

---

## The evaluation problem

Most tool-calling benchmarks give the model one shot: here's the prompt, emit your tool call, we score it. This made sense when tool calling was a formatting exercise. But as we deploy models in agentic loops where they receive real API responses and iterate, single-shot evaluation stops measuring the thing that matters.

I wanted to quantify exactly how much the evaluation methodology affects the results — and whether it affects all models equally, or changes the rankings.

---

## Setup

**Target API**: A real MCP-enabled project management system with 19 tools across projects, workunits, tasks, assets, and cross-cutting operations (search, context saving, directories). Real state — entities persist across tasks within a run. The database is cleaned between models.

**28 tasks, 3 difficulty levels**:
- **L0 (Explicit, 11 tasks)**: Prompt names the tool and all params. Tests formatting.
- **L1 (Natural language, 10 tasks)**: Prompt describes intent in plain language. Tests tool selection and parameter inference.
- **L2 (Multi-step reasoning, 7 tasks)**: Prompt describes a high-level goal. Tests multi-step planning, ID chaining across calls, conditional logic, semantic content generation.

**Two methodologies**:
- **Single-shot**: One prompt, one response, no feedback. Tool calls scored but not executed until after.
- **Agentic loop**: Prompt → tool call → real API response → iterate until pass or 300s timeout (25-turn cap).

**Scoring**: Task score 0.0-1.0 with partial credit. Pass threshold >= 0.75 (single-tool uses >= 0.6). Level score = mean of task scores. Overall = mean of three level scores.

---

## Hardware

All inference ran locally on consumer hardware. No cloud APIs.

| Component | Spec |
|-----------|------|
| GPU | RTX 4080 SUPER 16GB |
| CPU | Ryzen 7 7800X3D |
| RAM | 64 GB |
| Runtime | LM Studio 0.4.4 / llama.cpp CUDA 12 |
| Quantization | Q4_K_M (19 models), Q3_K_L (devstral), MXFP4 (gpt-oss) |
| Context | 8192 tokens |
| Temperature | 0.0 |

---

## Models tested

21 models, 3B to 80B. 16 tool-trained, 5 control group (not fine-tuned for tools). Most are Q4_K_M; two exceptions noted.

| # | Model | Params | Disk | Quant | Tool |
|---|-------|--------|-----:|-------|:---:|
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

---

## Agentic results

| Rank | Model | Params | Disk | Tool | L0 | L1 | L2 | Overall |
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

---

## The methodology gap: why it matters

Here's the core finding. The agentic lift scales with task difficulty:

| Level | Single-shot (mean) | Agentic (mean) | Lift | SS Pass Rate | Agentic Pass Rate |
|-------|---:|---:|---:|---:|---:|
| L0 (explicit) | 92.4% | 97.4% | +5.0pp | 92.6% | 97.8% |
| L1 (natural language) | 76.2% | 88.8% | +12.6pp | 73.3% | 89.5% |
| L2 (reasoning) | 28.6% | 65.9% | +37.3pp | 2.0% | 49.7% |

That L2 line is the headline: **2.0% single-shot pass rate vs 49.7% agentic pass rate.** Multi-step tool chains are essentially impossible in single-shot — the model would need to predict UUIDs for entities it hasn't created yet.

But the more important insight is that the methodology doesn't just raise all scores uniformly. **It changes the rankings.**

![Agentic lift per model](images/graph4_agentic_lift.png)

*Agentic lift varies from +0.6pp (deepseek-r1) to +56.3pp (phi-4-reasoning-plus).*

Three cases illustrate why this matters for evaluation:

**phi-4-reasoning-plus (15B): +56.3pp lift.** Single-shot rank: 21st (dead last). Agentic rank: 8th. This model has strong reasoning but poor zero-shot tool-call formatting. A single-shot benchmark would tell you to skip it entirely. An agentic benchmark correctly identifies it as a top-10 model.

**qwen3-4b-thinking-2507: +49.6pp lift.** Single-shot rank: 18th. Agentic rank: 10th. Another model whose single-shot results dramatically understate its actual capability in an agentic setting.

**deepseek-r1-0528-qwen3-8b: +0.6pp lift.** Single-shot rank: 19th. Agentic rank: 21st. The agentic loop doesn't help here — the model's failure mode isn't formatting, it's fundamental reasoning gaps (0% on L2). Single-shot and agentic evaluations agree this model can't do tool calling.

The pattern: **models with strong reasoning but poor formatting benefit massively from agentic evaluation. Models with fundamental reasoning gaps don't.** A single-shot benchmark conflates these two very different failure modes.

---

## What this means for tool-calling evaluation

**If you're evaluating models for agentic deployment, use agentic evaluation.** This sounds obvious, but most published tool-calling benchmarks are single-shot. The rankings change. phi-4-reasoning-plus goes from last to 8th. A model you'd reject in single-shot might be your best option in production.

**L0/L1 tasks have ceiling effects in agentic mode.** 16/21 models score 100% on L0. 8/21 score 100% on L1. If your benchmark is mostly explicit or simple natural language tasks, you're not measuring anything useful in agentic mode. You need multi-step reasoning tasks (our L2) to discriminate between capable models.

**Tool training provides floor, not ceiling.** Tool-trained models average 88.7% (SD 7.2pp). Control group averages 69.3% (SD 25.4pp). Tool training makes results more consistent, but the best untrained model (phi-4, 91.4%) outperforms most trained ones. The variability in the control group suggests that raw reasoning ability varies more than tool-trained competence.

---

## Infrastructure matters: the Jinja lesson

One model (seed-oss-36b, 36B) initially scored 0% on every agentic task — not because the model was bad, but because LM Studio's Jinja template engine doesn't support Python's `in` operator for tuple/array membership testing. Three constructs in the chat template were incompatible. After rewriting them, it scored 66.6%.

If you're benchmarking tool calling, you're benchmarking the entire stack: model weights + quantization + inference engine + template rendering + tool-call formatting. A "model" failure might be an infrastructure failure. Debugging infrastructure should be part of the evaluation methodology.

---

## Full data

Everything is open — source code, task definitions, runner scripts, all result JSONs with complete audit trails:

**Repository**: [github.com/3615-computer/workunit-benchmarks](https://github.com/3615-computer/workunit-benchmarks)

The full research paper with formal methodology, all five graphs, statistical breakdowns, and appendices is at `reports/research_paper.md` in the repo. For hardware-focused discussion and VRAM recommendations, see the [r/LocalLLaMA post](https://reddit.com/r/LocalLLaMA).

---

## Questions for the community

1. **How do you evaluate tool calling?** Are you using single-shot, agentic, or something else? Do your findings match this pattern where the methodology changes rankings?
2. **Anyone comparing local models against cloud APIs?** I only tested local/quantized models. Curious where they sit relative to GPT-4o, Claude, Gemini on the same tasks.
3. **What other MCP domains would be interesting to benchmark?** This is project management tools. Code execution, web browsing, data analysis could show different strengths.
4. **Does quantization level affect tool calling?** Most of my results are Q4_K_M (two exceptions: devstral at Q3_K_L, gpt-oss at MXFP4). If you've tested different quant levels, I'd like to compare.

Caveats: single hardware config, mostly Q4_K_M quantization (two exceptions noted), single MCP domain, temperature 0.0, single run per model. Full limitations in the research paper. The absolute numbers have uncertainty — the relative findings (agentic > single-shot, methodology changes rankings, L2 discriminates) should be robust.

---

**Disclosure**: I built the MCP server used in this benchmark ([workunit.app](https://workunit.app)). I chose it because I wanted to figure out if and how local LLMs were working with the tools, and because I had full control over the test environment — not to promote it.

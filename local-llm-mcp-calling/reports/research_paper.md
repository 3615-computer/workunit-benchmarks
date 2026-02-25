<!-- REGENERATE AFTER FULL BENCHMARK RUN -->
<!--
  Target: standalone research paper / blog post
  Audience: Researchers, AI engineers, people evaluating LLMs for tool use
  Tone: Academic, rigorous, evidence-based. No marketing language.
  Images: All three graphs from reports/images/

  WHAT CHANGED SINCE LAST VERSION (v1):
  - This is v2 of the benchmark with significant validation improvements
  - Must clearly distinguish v1 vs v2 methodology and explain why scores differ

  STRUCTURE TO FOLLOW:
  1. Title: "MCP Tool Calling Performance of Local LLMs: Single-shot vs Agentic
     Evaluation Across N Models"
  2. Abstract (~150 words):
     - What was tested (N models, 3B-80B, MCP tool calling)
     - How (28 tasks, 3 difficulty levels, 2 methodologies)
     - Key finding (methodology effect, tool-training effect, size relationship)
  3. Section 1 — Introduction:
     - Why tool calling matters for agentic workflows
     - Gap in empirical data for local/quantized models
     - What this benchmark measures (task difficulty x evaluation methodology)
  4. Section 2 — Experimental Setup:
     - 2.1 Hardware and Runtime (table)
     - 2.2 MCP Server (19 tools, project management API, real state)
     - 2.3 Models Tested (table sorted by size, with quant and tool-trained flag)
     - 2.4 Task Design (3 levels with examples, explain each)
     - 2.5 Scoring (task score, pass rate, level score, overall score)
     - 2.6 Evaluation Methodologies (single-shot vs agentic, with details)
     - 2.7 v2 Methodology Improvements:
       * Semantic validation (name_must_relate_to, query_must_contain, etc.)
       * call_count_min enforcement
       * Placeholder substitution with real entity IDs
       * L2 fixture seeding for tasks requiring pre-existing data
       * Impact: L2 scores more discriminating, overall scores more accurate
  5. Section 3 — Results:
     - 3.1 Agentic Loop Overall Rankings (table with all models)
     - 3.2 Single-shot Overall Rankings (table)
     - 3.3 Single-shot vs Agentic Comparison (graph1, analysis)
     - 3.4 Per-Level Analysis (graph2, L0/L1/L2 breakdown)
     - 3.5 Tool-trained vs Control Group (graph3, statistical comparison)
     - 3.6 Size-Performance Analysis
  6. Section 4 — Discussion:
     - 4.1 Methodology Effect: why agentic > single-shot, magnitude by level
     - 4.2 L2 as Discriminator: multi-step reasoning separates models
     - 4.3 Tool Training: fine-tuning vs raw reasoning ability
     - 4.4 Small Models: when do small models compete with large ones?
     - 4.5 Anomalies: models with inverted difficulty, 0% SS but high AG, etc.
     - 4.6 v1 vs v2 Comparison: how stricter validation changed the picture
  7. Section 5 — Limitations:
     - Single hardware config (4080 16GB)
     - Q4_K_M quantization (not native precision)
     - 8192 context (some models support more)
     - Single MCP domain (project management)
     - Temperature 0.0 (no stochasticity, but also no sampling diversity)
  8. Section 6 — Conclusion:
     - Key takeaways
     - What this means for practitioners choosing local models for tool use
  9. Appendix:
     - Full per-task results for top 5 models
     - Task definitions summary
     - Repo link for full reproducibility

  DATA SOURCES:
  - All three graph scripts in reports/images/
  - Result JSONs via _load_results.py
  - Per-task detail from individual result JSON files
-->

# MCP Tool Calling Performance of Local LLMs: Single-shot vs Agentic Evaluation

> **Status: PENDING** — regenerate after full benchmark run with updated validators (v2)

## Abstract

TODO: Write after benchmark run. ~150 words summarizing models tested, methodology, and key findings.

---

## 1. Introduction

TODO: Motivate the benchmark — tool calling in agentic workflows, gap in local model evaluation, what we measure.

## 2. Experimental Setup

### 2.1 Hardware and Runtime

| Component | Specification |
|-----------|--------------|
| GPU | NVIDIA RTX 4080 16GB |
| System RAM | 64GB |
| Model runtime | LM Studio (local, OpenAI-compatible API) |
| Context length | 8192 tokens (all models) |
| Temperature | 0.0 (all models) |
| Quantization | Q4_K_M (default); exceptions noted per model |
| Task timeout | 300s per task (agentic only) |

### 2.2 MCP Server

19-tool project management API. Real state within each model's run, database reset between models.

### 2.3 Models Tested

TODO: Table from results (sorted by size, with quant and tool-trained flag)

### 2.4 Task Design

28 tasks across 3 difficulty levels. TODO: examples from task JSONs.

### 2.5 Scoring

- **Task score** (0-100%): partial credit for multi-step tasks
- **Pass rate**: binary, task passes at >= 75% score
- **Level score**: mean task score across all tasks at that level
- **Overall score**: mean of three level scores

### 2.6 Evaluation Methodologies

**Single-shot**: one response, no tool results returned, score what the model emits.

**Agentic loop**: model calls tool -> gets real result -> continues until pass or 300s timeout. Early exit on task completion.

### 2.7 v2 Methodology Improvements

Key changes from v1 that affect scores:

1. **Semantic validation enforced**: name_must_relate_to, query_must_contain, query_must_relate_to, atom_type_must_be, content_must_mention, update_mask_must_contain, and ID chaining (*_must_match) validators are now active. v1 had these defined in task JSONs but never checked.
2. **call_count_min fixed**: tasks requiring multiple calls of the same tool (e.g., create_task x3) now correctly enforce the minimum count. v1 silently defaulted to 1.
3. **Placeholder substitution**: tasks referencing entities from earlier tasks ({{project_id}}, {{workunit_id}}) now receive real UUIDs instead of literal placeholder strings.
4. **L2 fixture seeding**: L2 tasks that require pre-existing data (e.g., "triage the tasks in this workunit") now have fixture data created before the level runs.
5. **L2-03 prompt clarity**: atom_type expectation made unambiguous.
6. **L2-07 ordering relaxed**: multiple valid step orderings accepted.

**Impact**: L2 scores are more discriminating (semantic correctness matters, not just tool name matching). Some models may score lower than v1 on tasks where they were getting credit for structurally correct but semantically wrong calls.

## 3. Results

### 3.1 Agentic Loop — Overall Rankings

TODO: Full table from results

### 3.2 Single-shot — Overall Rankings

TODO: Full table from results

### 3.3 Single-shot vs Agentic Comparison

TODO: Analysis with graph1 image

### 3.4 Per-Level Analysis

TODO: Analysis with graph2 image

### 3.5 Tool-trained vs Control Group

TODO: Analysis with graph3 image

### 3.6 Size-Performance Analysis

TODO: Correlations and tier analysis

## 4. Discussion

TODO: Analysis of findings

## 5. Limitations

- Single hardware configuration (RTX 4080 16GB + 64GB RAM)
- Q4_K_M quantization for most models (not native precision)
- Fixed 8192 context length (some models support more)
- Single MCP domain (project management)
- Temperature 0.0 (deterministic but no sampling diversity)
- LM Studio-specific tool call formatting (may affect some models)

## 6. Conclusion

TODO: Key takeaways for practitioners choosing local models for tool use.

---

*Full results, task definitions, and runner scripts: github.com/3615-computer/workunit-benchmarks*

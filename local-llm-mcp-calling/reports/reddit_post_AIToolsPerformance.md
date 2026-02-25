<!-- REGENERATE AFTER FULL BENCHMARK RUN -->
<!--
  Target: r/AIToolsPerformance
  Audience: Technical, methodology-focused, values rigor and reproducibility
  Tone: Structured, precise, academic-adjacent. Full methodology disclosure.
  Hero image: images/graph2_level_breakdown_agentic.png

  WHAT CHANGED SINCE LAST VERSION (v1):
  - Same validation/scoring changes as LocalLLaMA post (see that file for details)
  - This post should emphasize the METHODOLOGY improvements specifically

  STRUCTURE TO FOLLOW:
  1. Title: descriptive, include model count, mention methodology and difficulty levels
     - Format: "Benchmark: N local LLMs on MCP tool calling — explicit, natural language,
       and multi-step reasoning tasks, evaluated single-shot and agentic."
  2. Overview: what this benchmark measures and why
  3. Hardware and Infrastructure table:
     - GPU, RAM, runtime, context length, temperature, quantization, timeout
  4. Models Tested table:
     - Model | Size | Quant | Tool-trained
     - Sorted by size ascending
  5. Task Design section:
     - 28 tasks across 3 levels with examples
     - Explain what each level tests
     - Mention the 19-tool API (project management: create/get/update for
       projects, workunits, tasks, assets; search; save_context; directories; links)
  6. Scoring methodology:
     - Task score (0-100%, partial credit)
     - Pass rate (binary, >=75% threshold)
     - Level score (mean task score per level)
     - Overall score (mean of three level scores)
  7. Evaluation methodologies:
     - Single-shot: one response, no feedback
     - Agentic: iterative with real API responses, 300s timeout, early exit
  8. Results:
     - Full ranking table: Rank | Model | Size | Tool-trained | L0% | L1% | L2% | Overall
     - Level breakdown analysis with graph2 image
     - Statistical observations (correlations, group differences)
  9. Key findings (structured, numbered):
     - Methodology effect (SS vs AG delta by level)
     - Task complexity discrimination
     - Tool-training effect (with/without, control group analysis)
     - Size-performance relationship
     - Anomalies and edge cases
  10. v2 methodology improvements:
      - Semantic validation now enforced
      - call_count_min bug fixed
      - Placeholder substitution working
      - L2 fixture seeding
      - What this means for score comparisons with v1
  11. Reproducibility:
      - Repo link, instructions to reproduce
      - MCP server (workunit.app free tier or local dev stack)
  12. Graph 3 (tool-trained vs control) with analysis

  DATA SOURCES:
  - All three graph scripts in reports/images/
  - Result JSONs via _load_results.py
  - aggregated_report.md (generate from runner output)
-->

# Reddit Post — r/AIToolsPerformance

> **Status: PENDING** — regenerate after full benchmark run with updated validators

---

## TITLE

Benchmark: N local LLMs on MCP tool calling — explicit, natural language, and multi-step reasoning tasks, evaluated single-shot and agentic. Full methodology and v2 validation improvements.

---

## POST BODY

TODO: Write after benchmark run completes. Follow structure above.

Key data points to extract from results:
- [ ] Full ranking table with all models
- [ ] Per-level pass rates for each model
- [ ] SS vs AG delta statistics (mean, median, std dev by level)
- [ ] Tool-trained vs control group comparison (with graph3)
- [ ] Size tier analysis (3-8B, 8-15B, 15-24B, 24-36B, 36B+)
- [ ] Correlation between SS and AG scores
- [ ] Which validation changes had the biggest impact on scores vs v1

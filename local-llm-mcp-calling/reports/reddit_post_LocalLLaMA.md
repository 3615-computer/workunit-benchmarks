<!-- REGENERATE AFTER FULL BENCHMARK RUN -->
<!--
  Target: r/LocalLLaMA (https://www.reddit.com/r/LocalLLaMA/)
  Audience: Local LLM enthusiasts, practical users, hobbyists
  Tone: Conversational, direct, opinionated. Show personality.
  Hero image: images/graph1_ss_vs_ag_overall.png

  WHAT CHANGED SINCE LAST VERSION (v1):
  - Validation overhaul: semantic validators now enforced (name_must_relate_to,
    query_must_contain, atom_type_must_be, content_must_mention, ID chaining, etc.)
  - call_count_min bug fixed (was silently defaulting to 1)
  - L2 tasks now use real placeholder substitution ({{project_id}} etc. replaced
    with actual UUIDs from earlier task results)
  - L2-06/L2-07 get fixture data seeded before run (workunit with tasks to triage/close)
  - L2-03 prompt rewritten for clearer atom_type expectation
  - L2-07 ordering_matters removed (multiple valid orderings accepted)
  - Scores will differ from v1 — this is expected and more accurate

  STRUCTURE TO FOLLOW:
  1. Title: punchy, include model count, highlight surprising finding
     - Format: "I tested N local LLMs on real MCP tool calling — [surprising result]"
  2. Opening paragraph: what this is, why it matters, what's different from v1
  3. "The setup" section:
     - Hardware (4080 16GB + 64GB RAM, LM Studio, Q4_K_M)
     - Model count, size range, control group (not-tool-trained)
     - Three difficulty levels with examples (L0 explicit, L1 natural language, L2 reasoning)
     - Two methods (single-shot vs agentic) with brief explanation
  4. Results table: Model | Size | Quant | Tool | SS Overall | AG Overall
     - Sorted by AG Overall descending
     - Bold the AG Overall column
     - Footnote explaining scoring (partial credit, level averaging)
  5. Level breakdown section with graph2 image
  6. Key findings (3-5 bullet points):
     - Best performers and why
     - Size vs performance (small models punching above weight?)
     - Tool-trained vs not-tool-trained delta
     - Single-shot vs agentic gap (which models benefit most from feedback?)
     - Any anomalies (L2 > L0, 0% SS but high AG, etc.)
  7. Methodology changes from v1:
     - Brief note about validation fixes making scores more rigorous
     - Note that v1 scores had inflated L2 due to unimplemented validators
  8. Link to repo, research paper, reproducibility instructions

  DATA SOURCES:
  - Run `python gen_graph1_ss_vs_ag.py` and `python gen_graph2_level_breakdown.py`
    from reports/images/ to generate hero images
  - Result JSONs in results/v1_singleshot/latest/ and results/v2_agentic/latest/
  - Use _load_results.py to programmatically extract all numbers
-->

# Reddit Post — r/LocalLLaMA

> **Status: PENDING** — regenerate after full benchmark run with updated validators

---

## TITLE

I tested N local LLMs on real MCP tool calling — [highlight surprising finding from new results]

---

## POST BODY

TODO: Write after benchmark run completes. Follow structure above.

Key data points to extract from results:
- [ ] Total model count
- [ ] Top 3 models by AG Overall
- [ ] Biggest SS-to-AG jumps
- [ ] Not-tool-trained models that still perform well
- [ ] Smallest model with competitive scores
- [ ] Any models that regressed vs v1 (expected due to stricter validation)
- [ ] L2 pass rate changes (should be more discriminating now)

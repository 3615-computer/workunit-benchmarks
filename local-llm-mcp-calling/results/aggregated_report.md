## Benchmark Results

*Generated: 2026-02-25 03:23*

| Model | L0 Pass% | L0 Score | L1 Pass% | L1 Score | L2 Pass% | L2 Score | Overall |
|-------|---------|---------|---------|---------|---------|---------|---------|
| qwen/qwen3-coder-next | 100% | 100% | 90% | 95% | 71% | 82% | **92%** |
| qwen/qwen3-coder-30b | 100% | 100% | 90% | 95% | 71% | 82% | **92%** |
| qwen/qwen3.5-35b-a3b | 100% | 100% | 50% | 57% | 71% | 74% | **77%** |
| nvidia/nemotron-3-nano | 100% | 100% | 60% | 67% | 43% | 63% | **77%** |
| liquid/lfm2-24b-a2b | 82% | 82% | 90% | 81% | 29% | 57% | **73%** |
| zai-org/glm-4.7-flash | 55% | 55% | 60% | 58% | 71% | 75% | **63%** |
| qwen/qwen2.5-coder-32b | — | — | — | — | 14% | 21% | **21%** |
| bytedance/seed-oss-36b | 0% | 0% | 0% | 0% | 0% | 0% | **0%** |


### Level 0 — Task Breakdown

| Task | seed-oss-36b | lfm2-24b-a2b | nemotron-3-nano | qwen3-coder-30b | qwen3-coder-next | qwen3.5-35b-a3b | glm-4.7-flash |
|------|--------|--------|--------|--------|--------|--------|--------|
| L0-01: Ping the MCP server | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| L0-02: Get authenticated user | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| L0-03: Create a project | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| L0-04: Create a workunit | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| L0-05: Create a task in a workunit | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ❌ 0% |
| L0-06: Get a workunit with tasks | ❌ 0% | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ❌ 0% |
| L0-07: Update a task status | ❌ 0% | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ❌ 0% |
| L0-08: Save a context atom | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ❌ 0% |
| L0-09: Search for workunits | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| L0-10: Create a knowledge asset | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| L0-11: Update a workunit status to completed | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ❌ 0% |

### Level 1 — Task Breakdown

| Task | seed-oss-36b | lfm2-24b-a2b | nemotron-3-nano | qwen3-coder-30b | qwen3-coder-next | qwen3.5-35b-a3b | glm-4.7-flash |
|------|--------|--------|--------|--------|--------|--------|--------|
| L1-01: Create a project from natural language | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| L1-02: Create a workunit with full details | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| L1-03: Add three tasks to a workunit | ❌ 0% | ✅ 100% | ❌ 17% | ✅ 100% | ✅ 100% | ❌ 17% | ❌ 0% |
| L1-04: Update task to in-progress | ❌ 0% | ✅ 100% | ❌ 0% | ✅ 100% | ✅ 100% | ❌ 0% | ❌ 0% |
| L1-05: Search and retrieve a workunit | ❌ 0% | ✅ 100% | ❌ 50% | ❌ 50% | ❌ 50% | ❌ 50% | ✅ 100% |
| L1-06: Save a decision context atom | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ❌ 0% |
| L1-07: Create a product asset | ❌ 0% | ✅ 85% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 85% |
| L1-08: Get project details with stats | ❌ 0% | ❌ 0% | ❌ 0% | ✅ 100% | ✅ 100% | ❌ 0% | ❌ 0% |
| L1-09: Update workunit priority and tags | ❌ 0% | ✅ 60% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| L1-10: Complete a workunit with notes | ❌ 0% | ✅ 65% | ✅ 100% | ✅ 100% | ✅ 100% | ❌ 0% | ✅ 100% |

### Level 2 — Task Breakdown

| Task | seed-oss-36b | lfm2-24b-a2b | nemotron-3-nano | qwen2.5-coder-32b | qwen3-coder-30b | qwen3-coder-next | qwen3.5-35b-a3b | glm-4.7-flash |
|------|--------|--------|--------|--------|--------|--------|--------|--------|
| L2-01: Bootstrap a new feature project | ❌ 0% | ✅ 88% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| L2-02: Break down a feature into tasks | ❌ 0% | ❌ 50% | ❌ 50% | ❌ 50% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| L2-03: Find and update stale work | ❌ 0% | ❌ 50% | ❌ 50% | ❌ 0% | ❌ 50% | ✅ 100% | ✅ 100% | ✅ 100% |
| L2-04: Document an architectural decision | ❌ 0% | ❌ 50% | ✅ 100% | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 100% | ✅ 100% |
| L2-05: Create a project with linked asset | ❌ 0% | ✅ 100% | ✅ 93% | ❌ 0% | ✅ 100% | ✅ 100% | ✅ 93% | ✅ 100% |
| L2-06: Triage and prioritize tasks | ❌ 0% | ❌ 0% | ❌ 50% | ❌ 0% | ✅ 100% | ❌ 50% | ❌ 0% | ❌ 0% |
| L2-07: End-of-sprint workunit closeout | ❌ 0% | ❌ 65% | ❌ 0% | ❌ 0% | ❌ 25% | ❌ 25% | ❌ 25% | ❌ 25% |
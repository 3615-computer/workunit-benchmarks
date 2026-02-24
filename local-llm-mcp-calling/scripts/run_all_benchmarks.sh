#!/usr/bin/env bash
# Run full benchmark suite: single-shot + agentic for all models
# Uses --force to re-run even if results exist (needed after validation fix)
set -euo pipefail

cd "$(dirname "$0")/.."

TOKEN="$1"
REFRESH_TOKEN="${2:-}"

export LMSTUDIO_HOST=100.82.136.63:1234

echo "============================================"
echo " FULL BENCHMARK RE-RUN (validation fix v2)"
echo " $(date)"
echo "============================================"
echo ""

# ── Phase 1: Single-shot (all models) ──────────────────────────────────────
echo "╔══════════════════════════════════════════╗"
echo "║  Phase 1: Single-shot (all 19 models)   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

python3 scripts/runner_v1_singleshot.py \
    --models models.txt \
    --force \
    --no-git

echo ""
echo "Single-shot complete at $(date)"
echo ""

# ── Phase 2: Agentic (all models, local MCP) ──────────────────────────────
echo "╔══════════════════════════════════════════╗"
echo "║  Phase 2: Agentic (all 19 models)       ║"
echo "╚══════════════════════════════════════════╝"
echo ""

python3 scripts/runner_v2_agentic.py \
    --models models.txt \
    --token "$TOKEN" \
    --refresh-token "$REFRESH_TOKEN" \
    --local \
    --force \
    --no-git \
    --yes

echo ""
echo "Agentic complete at $(date)"
echo ""

# ── Phase 3: Aggregate reports ─────────────────────────────────────────────
echo "╔══════════════════════════════════════════╗"
echo "║  Phase 3: Aggregate reports              ║"
echo "╚══════════════════════════════════════════╝"
echo ""

python3 scripts/aggregate_results.py

echo ""
echo "============================================"
echo " ALL DONE at $(date)"
echo "============================================"

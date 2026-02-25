#!/usr/bin/env bash
# Run full benchmark suite: single-shot + agentic for all models
# Uses --force to re-run even if results exist
#
# Usage:
#   ./scripts/run_all_benchmarks.sh <token> [refresh_token]
#   LMSTUDIO_HOST=192.168.1.50:1234 ./scripts/run_all_benchmarks.sh <token>
#
# Faster iteration (single model / single level):
#   BENCH_MODEL=mistralai/ministral-3-3b ./scripts/run_all_benchmarks.sh <token>
#   BENCH_LEVEL=0 ./scripts/run_all_benchmarks.sh <token>
#   BENCH_MODEL=mistralai/ministral-3-3b BENCH_LEVEL=2 ./scripts/run_all_benchmarks.sh <token>
#
# Resume a crashed run (skips already-completed model+level combos):
#   BENCH_RESUME=20260225_143000 ./scripts/run_all_benchmarks.sh <token>
#
# Environment variables:
#   LMSTUDIO_HOST   - LM Studio host:port (default: 127.0.0.1:1234)
#   BENCH_MODEL     - Run only this model (default: all models from models.txt)
#   BENCH_LEVEL     - Run only this level 0|1|2 (default: all levels)
#   BENCH_PHASES    - Comma-separated phases to run: ss,ag,report (default: all)
#   BENCH_RESUME    - Resume a previous run by timestamp (e.g., 20260225_143000)
#                     Reuses existing run dirs and skips completed model+level combos
set -euo pipefail

cd "$(dirname "$0")/.."

TOKEN="$1"
REFRESH_TOKEN="${2:-}"

export LMSTUDIO_HOST="${LMSTUDIO_HOST:-127.0.0.1:1234}"

# Count models from models.txt (non-empty, non-comment lines)
MODEL_COUNT=$(grep -cvE '^\s*(#|$)' models.txt || echo 0)

# Build model/level flags for runners
MODEL_FLAG="--models models.txt"
LEVEL_FLAG=""
if [[ -n "${BENCH_MODEL:-}" ]]; then
    MODEL_FLAG="--model $BENCH_MODEL"
    MODEL_COUNT=1
fi
if [[ -n "${BENCH_LEVEL:-}" ]]; then
    LEVEL_FLAG="--level $BENCH_LEVEL"
fi

# Determine which phases to run
PHASES="${BENCH_PHASES:-ss,ag,report}"

# Create or reuse run directories
if [[ -n "${BENCH_RESUME:-}" ]]; then
    RUN_TS="$BENCH_RESUME"
    FORCE_FLAG=""  # Don't force when resuming — skip completed levels
    echo " Resuming run: $RUN_TS"
else
    RUN_TS=$(date +%Y%m%d_%H%M%S)
    FORCE_FLAG="--force"
fi
SS_DIR="results/v1_singleshot/run_${RUN_TS}"
AG_DIR="results/v2_agentic/run_${RUN_TS}"
mkdir -p "$SS_DIR" "$AG_DIR"

# Update "latest" symlinks for easy access
ln -sfn "run_${RUN_TS}" results/v1_singleshot/latest
ln -sfn "run_${RUN_TS}" results/v2_agentic/latest

echo "============================================"
echo " BENCHMARK RUN"
echo " $(date)"
echo " Models: $MODEL_COUNT | Host: $LMSTUDIO_HOST"
echo " Run ID: $RUN_TS"
[[ -n "${BENCH_MODEL:-}" ]] && echo " Filter: $BENCH_MODEL"
[[ -n "${BENCH_LEVEL:-}" ]] && echo " Level:  $BENCH_LEVEL only"
echo " Phases: $PHASES"
echo "============================================"
echo ""

# ── Phase 1: Single-shot ─────────────────────────────────────────────────
if [[ "$PHASES" == *"ss"* ]]; then
    echo "╔══════════════════════════════════════════╗"
    echo "║  Phase 1: Single-shot ($MODEL_COUNT models)"
    echo "╚══════════════════════════════════════════╝"
    echo ""

    python3 scripts/runner_v1_singleshot.py \
        $MODEL_FLAG \
        $LEVEL_FLAG \
        --token "$TOKEN" \
        --refresh-token "$REFRESH_TOKEN" \
        --results-dir "$SS_DIR" \
        --local \
        $FORCE_FLAG \
        --no-git \
        --yes

    echo ""
    echo "Single-shot complete at $(date)"
    echo ""
fi

# ── Phase 2: Agentic ─────────────────────────────────────────────────────
if [[ "$PHASES" == *"ag"* ]]; then
    echo "╔══════════════════════════════════════════╗"
    echo "║  Phase 2: Agentic ($MODEL_COUNT models)"
    echo "╚══════════════════════════════════════════╝"
    echo ""

    python3 scripts/runner_v2_agentic.py \
        $MODEL_FLAG \
        $LEVEL_FLAG \
        --token "$TOKEN" \
        --refresh-token "$REFRESH_TOKEN" \
        --results-dir "$AG_DIR" \
        --local \
        $FORCE_FLAG \
        --no-git \
        --yes

    echo ""
    echo "Agentic complete at $(date)"
    echo ""
fi

# ── Phase 3: Aggregate reports ────────────────────────────────────────────
if [[ "$PHASES" == *"report"* ]]; then
    echo "╔══════════════════════════════════════════╗"
    echo "║  Phase 3: Aggregate reports              ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""

    python3 scripts/aggregate_results.py --run "$RUN_TS"
fi

echo ""
echo "============================================"
echo " ALL DONE at $(date)"
echo " Results: results/*/run_${RUN_TS}/"
echo "============================================"

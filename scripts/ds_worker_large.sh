#!/usr/bin/env bash
# DeepSeek baselines -- WORKER B (uses ONLY the large model, :8001).
#
# 1. `large` baseline            (large only)   -- runs concurrently with worker A
# 2. wait for worker A's traces
# 3. or -> orr -> repair_once    (large only, small traces REUSED so the small server
#                                 is never touched) -- run strictly one at a time.
#
# Fairness: exactly one run uses the large model at any moment, and steps 3's runs
# reuse worker A's traces rather than re-running the small model.
set -euo pipefail

cd /home/ssn899/Desktop/LargeModelFix
PY=/home/ssn899/miniforge3/envs/largemodelfix/bin/python
export HF_HOME=/hdd1/ssn899/hf_cache

RESULTS=/home/ssn899/Desktop/LargeModelFix/results
SMALL_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
LARGE_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
DATASETS="aime2024 aime2025 gpqa"
SMALL_TAG=ds_small_base

COMMON="--datasets $DATASETS --limit 10000 \
        --small-model $SMALL_MODEL --large-model $LARGE_MODEL \
        --small-url http://localhost:8000 --large-url http://localhost:8001 \
        --out-dir $RESULTS --save-traces"

echo "=== [B1] large baseline ($LARGE_MODEL)  $(date) ==="
$PY scripts/run_eval.py --strategies large $COMMON \
    --max-tokens 16384 --tag ds_large_base

echo "=== [B] waiting for worker A's small traces ...  $(date) ==="
while [ ! -f "$RESULTS/$SMALL_TAG/.done" ]; do sleep 20; done
echo "=== [B] small traces ready  $(date) ==="

REUSE="--small-traces $RESULTS/$SMALL_TAG --max-tokens 16384 --repair-max-tokens 16384"

echo "=== [B2] or  $(date) ==="
$PY scripts/run_eval.py --strategies or          $COMMON $REUSE --tag ds_or
echo "=== [B3] orr  $(date) ==="
$PY scripts/run_eval.py --strategies orr         $COMMON $REUSE --tag ds_orr
echo "=== [B4] repair_once  $(date) ==="
$PY scripts/run_eval.py --strategies repair_once $COMMON $REUSE --tag ds_repair_once

echo "=== [B] all done  $(date) ==="

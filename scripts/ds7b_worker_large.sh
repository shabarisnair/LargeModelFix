#!/usr/bin/env bash
# DeepSeek 7B/32B baselines -- WORKER B (uses ONLY the large model, :8001 = 32B on GPU1).
#
# The `large` baseline is NOT re-run here: it depends only on the 32B (not on the small
# model), so the existing `ds_large_base` run (same model, same datasets, same params)
# serves as the large baseline for this pair too.
#
# 1. wait for worker A's 7B traces
# 2. or -> orr -> repair_once  (large only; the 7B traces are REUSED so the small server
#                               is never touched) -- strictly one at a time.
#
# Fairness: exactly one run uses the large model at any moment.
set -euo pipefail

cd /home/ssn899/Desktop/LargeModelFix
PY=/home/ssn899/miniforge3/envs/largemodelfix/bin/python
export HF_HOME=/hdd1/ssn899/hf_cache

RESULTS=/home/ssn899/Desktop/LargeModelFix/results
SMALL_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-7B
LARGE_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
DATASETS="aime2024 aime2025 gpqa"
SMALL_TAG=ds7b_small_base

COMMON="--datasets $DATASETS --limit 10000 \
        --small-model $SMALL_MODEL --large-model $LARGE_MODEL \
        --small-url http://localhost:8000 --large-url http://localhost:8001 \
        --out-dir $RESULTS --save-traces"

echo "=== [B] waiting for worker A's 7B traces ...  $(date) ==="
while [ ! -f "$RESULTS/$SMALL_TAG/.done" ]; do sleep 20; done
echo "=== [B] 7B traces ready  $(date) ==="

REUSE="--small-traces $RESULTS/$SMALL_TAG --max-tokens 16384 --repair-max-tokens 16384"

echo "=== [B1] or  $(date) ==="
$PY scripts/run_eval.py --strategies or          $COMMON $REUSE --tag ds7b_or
echo "=== [B2] orr  $(date) ==="
$PY scripts/run_eval.py --strategies orr         $COMMON $REUSE --tag ds7b_orr
echo "=== [B3] repair_once  $(date) ==="
$PY scripts/run_eval.py --strategies repair_once $COMMON $REUSE --tag ds7b_repair_once

echo "=== [B] all done  $(date) ==="

#!/usr/bin/env bash
# DeepSeek 7B/32B baselines -- WORKER A (uses ONLY the small model, :8000 = 7B on GPU0).
#
# Runs the `small` baseline on all three datasets, then writes a .done marker that
# worker B waits for (its or/orr/repair_once runs reuse these traces).
#
# Fairness: this worker is the ONLY user of the small model while it runs, and never
# touches the large model -- so it runs concurrently with worker B's `large` baseline
# without either contending for a server.
set -euo pipefail

cd /home/ssn899/Desktop/LargeModelFix
PY=/home/ssn899/miniforge3/envs/largemodelfix/bin/python
export HF_HOME=/hdd1/ssn899/hf_cache

RESULTS=/home/ssn899/Desktop/LargeModelFix/results
SMALL_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-7B
LARGE_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
DATASETS="aime2024 aime2025 gpqa"
TAG=ds7b_small_base

echo "=== [A] small baseline ($SMALL_MODEL)  $(date) ==="
$PY scripts/run_eval.py --strategies small \
    --datasets $DATASETS --limit 10000 --max-tokens 16384 \
    --small-model "$SMALL_MODEL" --large-model "$LARGE_MODEL" \
    --small-url http://localhost:8000 --large-url http://localhost:8001 \
    --out-dir "$RESULTS" --tag "$TAG" --save-traces

touch "$RESULTS/$TAG/.done"          # signal worker B that the traces are ready
echo "=== [A] done  $(date) -> traces in $RESULTS/$TAG ==="

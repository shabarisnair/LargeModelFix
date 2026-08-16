#!/usr/bin/env bash
# Terminal 2: run OR, then (only after it finishes) ORR.
# Large model on :8002 (so it runs in parallel with worker 1 on :8001).
# Both reuse the saved small traces -- the 8B is not run.
set -euo pipefail

cd /home/ssn899/Desktop/LargeModelFix
PY=/home/ssn899/miniforge3/envs/largemodelfix/bin/python   # named env
export HF_HOME=/hdd1/ssn899/hf_cache

RESULTS=/home/ssn899/Desktop/LargeModelFix/results
SMALL_TRACES=$RESULTS/small_base_extended
COMMON="--datasets aime2024 gpqa --limit 10000 --out-dir $RESULTS --save-traces \
        --small-url http://localhost:8000 --large-url http://localhost:8002 \
        --max-tokens 16384 --repair-max-tokens 16384 --small-traces $SMALL_TRACES"

echo "=== [1/2] or  $(date) ==="
$PY scripts/run_eval.py --strategies or $COMMON --tag or_extended

echo "=== [2/2] orr  $(date) ==="
$PY scripts/run_eval.py --strategies orr $COMMON --tag orr_extended

echo "=== worker 2 done  $(date) ==="

#!/usr/bin/env bash
# Terminal 1: run repair_once, then (only after it finishes) periodic mentor@512.
# Large model on :8001, small model on :8000 (periodic needs the 8B live).
# repair_once reuses the saved small traces; periodic runs the 8B itself.
set -euo pipefail

cd /home/ssn899/Desktop/LargeModelFix
PY=/home/ssn899/miniforge3/envs/largemodelfix/bin/python   # named env
export HF_HOME=/hdd1/ssn899/hf_cache

RESULTS=/home/ssn899/Desktop/LargeModelFix/results
SMALL_TRACES=$RESULTS/small_base_extended
COMMON="--datasets aime2024 gpqa --limit 10000 --out-dir $RESULTS --save-traces \
        --small-url http://localhost:8000 --large-url http://localhost:8001"

echo "=== [1/2] repair_once  $(date) ==="
$PY scripts/run_eval.py --strategies repair_once $COMMON \
    --max-tokens 16384 --repair-max-tokens 16384 \
    --small-traces "$SMALL_TRACES" \
    --tag repair_once_extended_thinking --repair-thinking

echo "=== [2/2] periodic mentor@512  $(date) ==="
$PY scripts/run_eval.py --strategies periodic $COMMON \
    --max-tokens 16384 --repair-max-tokens 4096 \
    --repair-trigger interval --repair-intervener mentor --repair-intervals 512 \
    --tag periodic512_extended_thinking --repair-thinking

echo "=== worker 1 done  $(date) ==="

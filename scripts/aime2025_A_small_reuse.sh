#!/usr/bin/env bash
# AIME-2025, Terminal A (large model on :8001).
# Runs small FIRST (produces the reusable traces), then the reuse strategies
# (or, orr, repair_once, repair_once-thinking) on large :8001.
# Independent of script B -> start both terminals at the same time.
set -euo pipefail

cd /home/ssn899/Desktop/LargeModelFix
PY=/home/ssn899/miniforge3/envs/largemodelfix/bin/python
export HF_HOME=/hdd1/ssn899/hf_cache
RESULTS=/home/ssn899/Desktop/LargeModelFix/results

echo "=== [1/5] small (produces reusable traces)  $(date) ==="
$PY scripts/run_eval.py --strategies small --datasets aime2025 --limit 10000 \
    --max-tokens 16384 --small-url http://localhost:8000 \
    --out-dir "$RESULTS" --tag small_aime2025 --save-traces

CMN="--datasets aime2025 --limit 10000 --max-tokens 16384 --repair-max-tokens 16384 \
     --small-traces $RESULTS/small_aime2025 \
     --small-url http://localhost:8000 --large-url http://localhost:8001 \
     --out-dir $RESULTS --save-traces"

echo "=== [2/5] or  $(date) ==="
$PY scripts/run_eval.py --strategies or          $CMN --tag or_aime2025
echo "=== [3/5] orr  $(date) ==="
$PY scripts/run_eval.py --strategies orr         $CMN --tag orr_aime2025
echo "=== [4/5] repair_once  $(date) ==="
$PY scripts/run_eval.py --strategies repair_once $CMN --tag repair_once_aime2025
echo "=== [5/5] repair_once (thinking)  $(date) ==="
$PY scripts/run_eval.py --strategies repair_once $CMN --tag repair_once_thinking_aime2025 --repair-thinking

echo "=== worker A done  $(date) ==="

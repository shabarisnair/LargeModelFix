#!/usr/bin/env bash
# AIME-2025, Terminal B (large model on :8002).
# Runs the large baseline, then periodic@512 and periodic@1024.
# Needs no saved small traces (large is standalone; periodic runs the 8B live on
# :8000), so it can run in parallel with script A from the start.
set -euo pipefail

cd /home/ssn899/Desktop/LargeModelFix
PY=/home/ssn899/miniforge3/envs/largemodelfix/bin/python
export HF_HOME=/hdd1/ssn899/hf_cache
RESULTS=/home/ssn899/Desktop/LargeModelFix/results

echo "=== [1/3] large  $(date) ==="
$PY scripts/run_eval.py --strategies large --datasets aime2025 --limit 10000 \
    --max-tokens 16384 --large-url http://localhost:8002 \
    --out-dir "$RESULTS" --tag large_aime2025 --save-traces

PCMN="--datasets aime2025 --limit 10000 --max-tokens 16384 --repair-max-tokens 4096 \
      --repair-trigger interval --repair-intervener mentor \
      --small-url http://localhost:8000 --large-url http://localhost:8002 \
      --out-dir $RESULTS --save-traces"

echo "=== [2/3] periodic@512  $(date) ==="
$PY scripts/run_eval.py --strategies periodic $PCMN --repair-intervals 512  --tag periodic512_aime2025
echo "=== [3/3] periodic@1024  $(date) ==="
$PY scripts/run_eval.py --strategies periodic $PCMN --repair-intervals 1024 --tag periodic1024_aime2025

echo "=== worker B done  $(date) ==="

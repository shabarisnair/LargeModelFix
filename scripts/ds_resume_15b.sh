#!/usr/bin/env bash
# Resume the two remaining 1.5B-pair runs. Both reuse saved traces -> 32B only.
set -euo pipefail
cd /home/ssn899/Desktop/LargeModelFix
PY=/home/ssn899/miniforge3/envs/largemodelfix/bin/python
export HF_HOME=/hdd1/ssn899/hf_cache
R=/home/ssn899/Desktop/LargeModelFix/results
L=deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
S15=deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
until curl -sf -m3 localhost:8001/v1/models >/dev/null 2>&1; do sleep 20; done
echo "=== 32B ready  $(date) ==="
for s in orr repair_once; do
  echo "=== [1.5B pair] $s  $(date) ==="
  $PY scripts/run_eval.py --strategies $s --datasets aime2024 aime2025 gpqa --limit 10000 \
      --max-tokens 32768 --repair-max-tokens 32768 \
      --small-model $S15 --large-model $L \
      --small-traces "$R/ds15b_small_base_32k" \
      --small-url http://localhost:8002 --large-url http://localhost:8001 \
      --out-dir "$R" --tag "ds15b_${s}_32k" --save-traces
done
echo "=== 1.5B pair complete  $(date) ==="

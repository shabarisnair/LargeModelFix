#!/usr/bin/env bash
# Worker: the ONLY user of the 32B (:8001, GPU1).
#  1. large baseline (concurrent with both small workers -- different models)
#  2. wait for the 7B traces  -> or, orr, repair_once   (7B pair)
#  3. wait for the 1.5B traces -> or, orr, repair_once  (1.5B pair)
# The reuse runs consume saved traces, so this worker never touches :8000/:8002.
# Exactly one run uses the 32B at any moment.
set -euo pipefail
cd /home/ssn899/Desktop/LargeModelFix
PY=/home/ssn899/miniforge3/envs/largemodelfix/bin/python
export HF_HOME=/hdd1/ssn899/hf_cache
R=/home/ssn899/Desktop/LargeModelFix/results
L=deepseek-ai/DeepSeek-R1-Distill-Qwen-32B
S7=deepseek-ai/DeepSeek-R1-Distill-Qwen-7B
S15=deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
DS="aime2024 aime2025 gpqa"
BUDGET="--max-tokens 32768 --repair-max-tokens 32768"

echo "=== [1] 32B large baseline @32768  $(date) ==="
$PY scripts/run_eval.py --strategies large --datasets $DS --limit 10000 \
    --max-tokens 32768 --small-model $S7 --large-model $L \
    --small-url http://localhost:8000 --large-url http://localhost:8001 \
    --out-dir "$R" --tag ds_large_base_32k --save-traces

echo "=== waiting for 7B traces ...  $(date) ==="
while [ ! -f "$R/ds7b_small_base_32k/.done" ]; do sleep 30; done
for s in or orr repair_once; do
  echo "=== [7B pair] $s  $(date) ==="
  $PY scripts/run_eval.py --strategies $s --datasets $DS --limit 10000 $BUDGET \
      --small-model $S7 --large-model $L \
      --small-traces "$R/ds7b_small_base_32k" \
      --small-url http://localhost:8000 --large-url http://localhost:8001 \
      --out-dir "$R" --tag "ds7b_${s}_32k" --save-traces
done

echo "=== waiting for 1.5B traces ...  $(date) ==="
while [ ! -f "$R/ds15b_small_base_32k/.done" ]; do sleep 30; done
for s in or orr repair_once; do
  echo "=== [1.5B pair] $s  $(date) ==="
  $PY scripts/run_eval.py --strategies $s --datasets $DS --limit 10000 $BUDGET \
      --small-model $S15 --large-model $L \
      --small-traces "$R/ds15b_small_base_32k" \
      --small-url http://localhost:8002 --large-url http://localhost:8001 \
      --out-dir "$R" --tag "ds15b_${s}_32k" --save-traces
done
echo "=== large worker all done  $(date) ==="

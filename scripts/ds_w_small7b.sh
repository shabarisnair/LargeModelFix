#!/usr/bin/env bash
# Worker: 7B small baseline only (:8000, GPU0). Never touches the large model.
set -euo pipefail
cd /home/ssn899/Desktop/LargeModelFix
PY=/home/ssn899/miniforge3/envs/largemodelfix/bin/python
export HF_HOME=/hdd1/ssn899/hf_cache
R=/home/ssn899/Desktop/LargeModelFix/results
TAG=ds7b_small_base_32k
echo "=== 7B small baseline @32768  $(date) ==="
$PY scripts/run_eval.py --strategies small \
    --datasets aime2024 aime2025 gpqa --limit 10000 --max-tokens 32768 \
    --small-model deepseek-ai/DeepSeek-R1-Distill-Qwen-7B \
    --large-model deepseek-ai/DeepSeek-R1-Distill-Qwen-32B \
    --small-url http://localhost:8000 --large-url http://localhost:8001 \
    --out-dir "$R" --tag "$TAG" --save-traces
touch "$R/$TAG/.done"
echo "=== 7B small done  $(date) ==="

#!/usr/bin/env bash
# Sample run: serve each model on one GPU in turn, generate a few problems from both
# AIME sets, grade, then free the GPU before the next model.
#   bash run_sample.sh <gpu> [n_problems] [n_seeds]
set -uo pipefail

GPU="${1:-1}"; NPROB="${2:-4}"; NSEED="${3:-2}"
PORT=8020
ENV_PY=/home/ssn899/envs/largemodelfix/bin/python
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/results/sample"
mkdir -p "$OUT/generations" "$OUT/graded"
cd "$HERE"

MODELS=(
  "Qwen/Qwen3-1.7B:0.85"
  "Qwen/Qwen3-8B:0.85"
  "Qwen/Qwen3-14B:0.88"
  "Qwen/Qwen3-30B-A3B-Instruct-2507:0.92"
)

for entry in "${MODELS[@]}"; do
  M="${entry%%:*}"; UTIL="${entry##*:}"
  TAG="$(basename "$M")"
  echo "================ $TAG ================"
  pkill -f "api_server.*--port $PORT" 2>/dev/null; sleep 6
  bash serve.sh "$GPU" "$PORT" "$M" 40960 "$UTIL"

  ready=0
  for i in $(seq 1 90); do
    if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:$PORT/v1/models 2>/dev/null)" = "200" ]; then
      ready=1; break
    fi
    if grep -q "Engine core initialization failed\|ValueError" "$HERE/results/serve/serve_$PORT.log" 2>/dev/null; then
      echo "  SERVER FAILED TO START"; tail -5 "$HERE/results/serve/serve_$PORT.log"; break
    fi
    sleep 10
  done
  [ "$ready" != "1" ] && { echo "  skipping $TAG"; continue; }

  for DS in aime2024 aime2025; do
    $ENV_PY generate.py --model "$M" --dataset "$DS" \
      --base-url "http://127.0.0.1:$PORT" \
      --out "$OUT/generations/${TAG}__${DS}.jsonl" \
      --limit "$NPROB" --seeds "$NSEED" --concurrency 8 --timeout 3600 \
      2>&1 | grep -E "to generate|done:|FAIL"
    $ENV_PY grade.py --gen "$OUT/generations/${TAG}__${DS}.jsonl" --outdir "$OUT/graded" 2>&1 | tail -2
  done
done

pkill -f "api_server.*--port $PORT" 2>/dev/null
echo "================ sample run complete ================"

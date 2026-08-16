#!/usr/bin/env bash
# Full sweep for one GPU: serve each assigned model in turn, generate all 30 problems x
# 8 seeds on both AIME sets, grade, then free the GPU for the next model.
#
#   bash run_full.sh <gpu> <port> <model>[:util] [<model>[:util] ...]
#
# Run one instance per free GPU to parallelise across models. generate.py is resumable,
# so re-issuing the same command after an interruption only fills the gaps.
set -uo pipefail

GPU="$1"; PORT="$2"; shift 2
ENV_PY=/home/ssn899/envs/largemodelfix/bin/python
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/results/full"
mkdir -p "$OUT/generations" "$OUT/graded"
cd "$HERE"

for entry in "$@"; do
  M="${entry%%:*}"
  UTIL="${entry##*:}"; [ "$UTIL" = "$M" ] && UTIL=0.90
  TAG="$(basename "$M")"
  echo "[gpu$GPU] ======== $TAG ========"
  pkill -f "api_server.*--port $PORT" 2>/dev/null; sleep 6
  bash serve.sh "$GPU" "$PORT" "$M" 40960 "$UTIL"

  ready=0
  for i in $(seq 1 120); do
    if [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:$PORT/v1/models 2>/dev/null)" = "200" ]; then
      ready=1; break
    fi
    if grep -q "Engine core initialization failed\|ValidationError" "$HERE/results/serve/serve_$PORT.log" 2>/dev/null; then
      echo "[gpu$GPU]   SERVER FAILED"; tail -4 "$HERE/results/serve/serve_$PORT.log"; break
    fi
    sleep 10
  done
  [ "$ready" != "1" ] && { echo "[gpu$GPU]   skipping $TAG"; continue; }

  for DS in aime2024 aime2025; do
    echo "[gpu$GPU] --- $TAG / $DS ---"
    $ENV_PY generate.py --model "$M" --dataset "$DS" \
      --base-url "http://127.0.0.1:$PORT" \
      --out "$OUT/generations/${TAG}__${DS}.jsonl" \
      --concurrency 32 --timeout 3600 2>&1 | grep -E "to generate|done:|FAIL"
    $ENV_PY grade.py --gen "$OUT/generations/${TAG}__${DS}.jsonl" \
      --outdir "$OUT/graded" 2>&1 | tail -1
  done
done

pkill -f "api_server.*--port $PORT" 2>/dev/null
echo "[gpu$GPU] ======== worker done ========"

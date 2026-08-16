#!/usr/bin/env bash
# Unbatched baseline sweep for one GPU.
#
#   bash run_baseline.sh <gpu> <port> <model>[:util] [<model>[:util] ...]
#
# One model resident on the GPU at a time, and one query in flight at a time
# (--concurrency 1). Concurrency 1 is the point of this run: it makes per-query latency
# meaningful, which batched runs cannot give. Uses the steps-only prompt (a plain JSON
# list of reasoning steps, no step ids or dependencies).
#
# generate.py is resumable, so re-issuing the same command fills only the gaps.
set -uo pipefail

GPU="$1"; PORT="$2"; shift 2
ENV_PY=/home/ssn899/envs/largemodelfix/bin/python
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/results/baseline"
mkdir -p "$OUT/generations" "$OUT/graded"
cd "$HERE"

for entry in "$@"; do
  M="${entry%%:*}"
  UTIL="${entry##*:}"; [ "$UTIL" = "$M" ] && UTIL=0.90
  TAG="$(basename "$M")"
  echo "[gpu$GPU] ======== $TAG ========"
  pkill -f "api_server.*--port $PORT" 2>/dev/null; sleep 8
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
      --prompt-style stepsonly --max-tokens 38000 \
      --concurrency 1 --timeout 3600 2>&1 | grep -E "to generate|done:|FAIL"
    $ENV_PY grade.py --gen "$OUT/generations/${TAG}__${DS}.jsonl" \
      --outdir "$OUT/graded" 2>&1 | tail -1
  done
done

pkill -f "api_server.*--port $PORT" 2>/dev/null
echo "[gpu$GPU] ======== worker done ========"

#!/usr/bin/env bash
# Launch the two vLLM OpenAI-compatible servers used by run_eval.py.
#
# GPUs / ports / models are passable as flags (or env vars). Defaults:
#   small model -> GPU 0, port 8000 ;  large model -> GPU 3, port 8001
#
# Examples:
#   bash serve_models.sh                                  # defaults
#   bash serve_models.sh --small-gpu 1 --large-gpu 2      # pick GPUs
#   bash serve_models.sh --large-gpu 2,3 --large-tp 2     # 32B across 2 GPUs
#   SMALL_GPU=1 LARGE_GPU=2 bash serve_models.sh          # env vars also work
#
# Weights are cached on /hdd1; prefix caching is on. Logs -> results/serve_*.log;
# stop with stop_models.sh.
set -euo pipefail

ENV_PY=/home/ssn899/envs/largemodelfix/bin/python
export HF_HOME=${HF_HOME:-/hdd1/ssn899/hf_cache}

# defaults (env-var overridable, then flag-overridable below)
SMALL_MODEL=${SMALL_MODEL:-Qwen/Qwen3-8B}
LARGE_MODEL=${LARGE_MODEL:-Qwen/Qwen3-32B}
SMALL_GPU=${SMALL_GPU:-0}
LARGE_GPU=${LARGE_GPU:-3}
SMALL_PORT=${SMALL_PORT:-8000}
LARGE_PORT=${LARGE_PORT:-8001}
SMALL_TP=${SMALL_TP:-1}          # tensor-parallel size (GPUs per model)
LARGE_TP=${LARGE_TP:-1}
MAX_LEN=${MAX_LEN:-40960}
GPU_MEM_UTIL=${GPU_MEM_UTIL:-0.90}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --small-gpu)   SMALL_GPU="$2"; shift 2;;
    --large-gpu)   LARGE_GPU="$2"; shift 2;;
    --small-port)  SMALL_PORT="$2"; shift 2;;
    --large-port)  LARGE_PORT="$2"; shift 2;;
    --small-model) SMALL_MODEL="$2"; shift 2;;
    --large-model) LARGE_MODEL="$2"; shift 2;;
    --small-tp)    SMALL_TP="$2"; shift 2;;
    --large-tp)    LARGE_TP="$2"; shift 2;;
    --max-len)     MAX_LEN="$2"; shift 2;;
    --gpu-mem-util) GPU_MEM_UTIL="$2"; shift 2;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "unknown arg: $1" >&2; exit 1;;
  esac
done

LOGDIR="$(dirname "$0")/../results"
mkdir -p "$LOGDIR"

launch () {  # $1=model $2=gpu(s) $3=port $4=tp $5=logfile
  echo "$1 on GPU(s) $2 :$3 (tp=$4)"
  CUDA_VISIBLE_DEVICES="$2" "$ENV_PY" -m vllm.entrypoints.openai.api_server \
      --model "$1" --port "$3" \
      --tensor-parallel-size "$4" \
      --max-model-len "$MAX_LEN" --enable-prefix-caching \
      --gpu-memory-utilization "$GPU_MEM_UTIL" \
      > "$5" 2>&1 &
  echo "  pid $! (log: $(basename "$5"))"
}

launch "$SMALL_MODEL" "$SMALL_GPU" "$SMALL_PORT" "$SMALL_TP" "$LOGDIR/serve_small.log"
launch "$LARGE_MODEL" "$LARGE_GPU" "$LARGE_PORT" "$LARGE_TP" "$LOGDIR/serve_large.log"

echo
echo "Waiting for servers to become ready (first run downloads weights)..."
"$ENV_PY" - "$SMALL_PORT" "$LARGE_PORT" <<'PY'
import sys, time, urllib.request
ports = sys.argv[1:]
deadline = time.time() + 3600
ready = set()
while time.time() < deadline and len(ready) < len(ports):
    for port in ports:
        if port in ready:
            continue
        try:
            urllib.request.urlopen(f"http://localhost:{port}/v1/models", timeout=5)
            ready.add(port); print(f"  :{port} ready")
        except Exception:
            pass
    time.sleep(5)
print("all ready" if len(ready) == len(ports) else "TIMEOUT waiting for servers")
PY

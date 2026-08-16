#!/usr/bin/env bash
# Launch one vLLM server for this experiment.
#   bash serve.sh <gpus> <port> <model> [max_model_len] [gpu_mem_util]
# <gpus> may be a comma list ("0,1"); tensor-parallel size is inferred from its length.
# 40960 is the native context of Qwen3-1.7B/8B/14B and so the binding limit for this
# sweep; prompts run ~5k tokens, leaving ~35k for generation.
set -euo pipefail

GPU="$1"; PORT="$2"; MODEL="$3"; MAXLEN="${4:-40960}"; MEMUTIL="${5:-0.90}"
TP=$(awk -F, '{print NF}' <<< "$GPU")

# PREFIX_CACHE=0 disables prefix caching. Every prompt here shares a ~4.8k-token demo
# block, so the cache is exercised extremely hard; Qwen3-30B-A3B (MoE) began emitting
# "!!!!" and multilingual gibberish partway through a run with it on, while returning
# HTTP 200 the whole time. Leave it off for that model.
PREFIX_CACHE="${PREFIX_CACHE:-1}"
CACHE_FLAG="--enable-prefix-caching"
[ "$PREFIX_CACHE" = "0" ] && CACHE_FLAG="--no-enable-prefix-caching"

ENV_PY=/home/ssn899/envs/largemodelfix/bin/python
export HF_HOME=${HF_HOME:-/hdd1/ssn899/hf_cache}
export VLLM_LOGGING_LEVEL=${VLLM_LOGGING_LEVEL:-WARNING}

LOGDIR="$(dirname "$0")/results/serve"
mkdir -p "$LOGDIR"

echo "launching $MODEL on GPU(s) $GPU -> :$PORT (tp=$TP len=$MAXLEN util=$MEMUTIL)"
CUDA_VISIBLE_DEVICES="$GPU" nohup "$ENV_PY" -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" --port "$PORT" \
    --tensor-parallel-size "$TP" \
    --max-model-len "$MAXLEN" \
    --gpu-memory-utilization "$MEMUTIL" \
    $CACHE_FLAG \
    --disable-log-requests \
    > "$LOGDIR/serve_${PORT}.log" 2>&1 &
echo "pid $!"

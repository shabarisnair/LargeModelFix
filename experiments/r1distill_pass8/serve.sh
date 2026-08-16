#!/usr/bin/env bash
# Launch one vLLM server.
#   bash serve.sh <gpus> <port> <model> [max_model_len] [gpu_mem_util]
# <gpus> may be a comma list ("2,3"); tensor-parallel size is inferred from its length.
# gpu_mem_util is a fraction of TOTAL device memory and must fit in what is FREE --
# other users' jobs share these GPUs, so check nvidia-smi before raising it.
# Logs -> $RESULTS/serve/serve_<port>.log
set -euo pipefail

GPU="$1"; PORT="$2"; MODEL="$3"; MAXLEN="${4:-40960}"; MEMUTIL="${5:-0.92}"
TP=$(awk -F, '{print NF}' <<< "$GPU")

ENV_PY=/home/ssn899/envs/largemodelfix/bin/python
export HF_HOME=${HF_HOME:-/hdd1/ssn899/hf_cache}
export VLLM_LOGGING_LEVEL=${VLLM_LOGGING_LEVEL:-WARNING}

LOGDIR=/hdd1/ssn899/LargeModelFix/results/r1distill_pass8/serve
mkdir -p "$LOGDIR"

echo "launching $MODEL on GPU(s) $GPU -> :$PORT (tp=$TP, max_model_len=$MAXLEN, util=$MEMUTIL)"
CUDA_VISIBLE_DEVICES="$GPU" nohup "$ENV_PY" -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" --port "$PORT" \
    --tensor-parallel-size "$TP" \
    --max-model-len "$MAXLEN" \
    --gpu-memory-utilization "$MEMUTIL" \
    --enable-prefix-caching \
    --disable-log-requests \
    > "$LOGDIR/serve_${PORT}.log" 2>&1 &
echo "pid $! ; log $LOGDIR/serve_${PORT}.log"

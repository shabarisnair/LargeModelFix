#!/usr/bin/env bash
# Stop the vLLM servers started by serve_models.sh.
pkill -f "vllm.entrypoints.openai.api_server" && echo "stopped vLLM servers" \
    || echo "no vLLM servers running"

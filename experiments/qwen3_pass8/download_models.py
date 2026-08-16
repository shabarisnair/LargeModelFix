"""Fetch the four Qwen3 models. Qwen3-8B is already cached."""
from huggingface_hub import snapshot_download
for m in ["Qwen/Qwen3-1.7B", "Qwen/Qwen3-14B", "Qwen/Qwen3-30B-A3B-Instruct-2507"]:
    print("downloading", m, flush=True)
    snapshot_download(repo_id=m, ignore_patterns=["*.pth", "original/*"])
    print("done", m, flush=True)

"""Download evaluation (test) sets from the HF hub into datasets/.

Files are fetched verbatim from each repo, keeping the repo-relative path so the
provenance stays obvious. Re-running is cheap: existing files are skipped.

    python scripts/download_eval_sets.py [gsm8k] [webinstruct] [livecodebench]

With no arguments all three are downloaded.
"""

from __future__ import annotations

import sys
from pathlib import Path

from huggingface_hub import hf_hub_download

DEST = Path(__file__).resolve().parent.parent / "datasets"

# LiveCodeBench's loading script maps release_v6 (== release_latest) to these six
# cumulative files; see code_generation_lite.py in the repo.
LCB_V6_FILES = ["test.jsonl", "test2.jsonl", "test3.jsonl",
                "test4.jsonl", "test5.jsonl", "test6.jsonl"]

TARGETS = {
    "gsm8k": ("openai/gsm8k", ["main/test-00000-of-00001.parquet"]),
    "webinstruct": ("TIGER-Lab/WebInstruct-verified", ["data/test-00000-of-00001.parquet"]),
    "livecodebench": ("livecodebench/code_generation_lite", LCB_V6_FILES),
}


def main(names: list[str]) -> None:
    for name in names:
        repo_id, files = TARGETS[name]
        out_dir = DEST / name
        for f in files:
            print(f"[{name}] {repo_id}/{f}", flush=True)
            hf_hub_download(repo_id=repo_id, filename=f, repo_type="dataset",
                            local_dir=out_dir)


if __name__ == "__main__":
    args = sys.argv[1:] or list(TARGETS)
    unknown = [a for a in args if a not in TARGETS]
    if unknown:
        raise SystemExit(f"unknown target(s) {unknown}; options: {list(TARGETS)}")
    main(args)

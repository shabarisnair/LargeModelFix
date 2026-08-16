"""Verify each prompt version reproduces the prompts actually sent on disk.

Every generation row stores its `user_prompt`, so the restored v1 text can be checked
byte-for-byte against the production run, and v2 against the test run.
"""
import json
import sys
from pathlib import Path

from prompts import build_prompt

RES = Path("/hdd1/ssn899/LargeModelFix/results/r1distill_pass8/generations")
SUBSETS = Path("/hdd1/ssn899/LargeModelFix/datasets/subsets")
DATASETS = ["gsm8k", "webinstruct", "livecodebench"]

subsets = {d: {json.loads(l)["id"]: json.loads(l)
               for l in open(SUBSETS / f"{d}_first_100.jsonl")} for d in DATASETS}

checked = mismatched = 0
for version, pattern in [("v1", "{tag}__{d}.jsonl"), ("v2", "v2test_{tag}__{d}.jsonl")]:
    for d in DATASETS:
        for tag in ["ds32b", "ds15b"]:
            path = RES / pattern.format(tag=tag, d=d)
            if not path.exists():
                continue
            n = bad = 0
            with open(path) as fh:
                for line in fh:
                    r = json.loads(line)
                    want = build_prompt(subsets[d][r["id"]], version=version)
                    n += 1
                    if want != r["user_prompt"]:
                        bad += 1
            checked += n
            mismatched += bad
            flag = "OK " if bad == 0 else "MISMATCH"
            print(f"  {flag} {version} {d:14s} {tag:6s} {n:4d} rows, {bad} mismatched")

print(f"\n{checked} stored prompts checked, {mismatched} mismatched")
sys.exit(1 if mismatched else 0)

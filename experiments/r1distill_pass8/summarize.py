"""Aggregate every *.summary.json into one table + results.json.

    python summarize.py [--tags ds32b,ds15b]
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

ROOT = Path("/hdd1/ssn899/LargeModelFix/results/r1distill_pass8")
DATASETS = ["gsm8k", "webinstruct", "livecodebench"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", default="ds32b,ds15b")
    args = ap.parse_args()
    tags = args.tags.split(",")

    rows, blob = [], {}
    for tag in tags:
        for d in DATASETS:
            f = ROOT / "graded" / f"{tag}__{d}.summary.json"
            if not f.exists():
                continue
            s = json.load(open(f))
            blob[f"{tag}/{d}"] = s
            rows.append((tag, s))

    if not rows:
        raise SystemExit("no summaries found yet")

    hdr = (f"{'model tag':10s} {'dataset':15s} {'pass@1':>8s} {'std':>7s} "
           f"{'queries':>8s} {'seeds':>6s} {'trunc':>6s} {'mean_tok':>9s}")
    print(hdr)
    print("-" * len(hdr))
    for tag, s in rows:
        print(f"{tag:10s} {s['dataset']:15s} {s['pass@1_mean']*100:7.1f}% "
              f"{s['pass@1_std']*100:6.1f}% {s['n_queries']:8d} {s['n_seeds']:6d} "
              f"{s['truncated_at_max_tokens']:6d} {s['mean_completion_tokens']:9.0f}")

    out = ROOT / "results.json"
    json.dump(blob, open(out, "w"), indent=2)
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()

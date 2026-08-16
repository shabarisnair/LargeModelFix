"""Aggregate graded summaries into one table.

    python summarize.py [--dir results/sample/graded]

Reports accuracy and DAG health side by side, because a model can solve the problem while
ignoring the structure the prompt asks for (and vice versa).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ORDER = ["Qwen3-1.7B", "Qwen3-8B", "Qwen3-14B", "Qwen3-30B-A3B-Instruct-2507"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="results/sample/graded")
    args = ap.parse_args()
    files = sorted(Path(args.dir).glob("*.summary.json"))
    if not files:
        raise SystemExit(f"no summaries in {args.dir}")
    rows = [json.load(open(f)) for f in files]
    rows.sort(key=lambda s: (ORDER.index(s["model"].split("/")[-1])
                             if s["model"].split("/")[-1] in ORDER else 99,
                             s["dataset"]))

    hdr = (f"{'model':30s}{'dataset':10s}{'pass@1':>9s}{'json':>7s}"
           f"{'ids':>6s}{'topo':>6s}{'closed':>8s}{'cites':>7s}{'plural':>8s}"
           f"{'cite/step':>11s}{'steps':>7s}{'trunc':>6s}{'tokens':>8s}")
    print(hdr)
    print("-" * len(hdr))
    for s in rows:
        print(f"{s['model'].split('/')[-1]:30s}{s['dataset']:10s}"
              f"{s['pass@1_mean']*100:8.1f}%{s['valid_json_rate']*100:6.0f}%"
              f"{s.get('contiguous_ids_rate', 0)*100:5.0f}%{s['topological_rate']*100:5.0f}%"
              f"{s['closure_rate']*100:7.0f}%{s['citations_ok_rate']*100:6.0f}%"
              f"{s.get('plural_citation_rate', 0)*100:7.0f}%"
              f"{s.get('step_citation_rate', 0)*100:10.0f}%"
              f"{s['median_steps']:7.0f}{s['truncated']:6d}"
              f"{s['mean_completion_tokens']:8.0f}")
    print("""
pass@1     mean over the 8 seeds of that seed's accuracy across problems
json       response parsed, after repairing LaTeX backslashes that are illegal JSON escapes

The five prompt rules, each reported on its own (share of responses satisfying it):
  ids      step_id values contiguous and strictly increasing
  topo     every dependency id < the step's own id, listed ascending
  closed   every non-final step is used by some later step
  cites    every dependency also named as "Step N" in that step's edge prose
  plural   responses using the banned grouping "Steps 8, 9, and 10"  (lower is better)
cite/step  per-step citation compliance, over all dependency-bearing steps""")


if __name__ == "__main__":
    main()

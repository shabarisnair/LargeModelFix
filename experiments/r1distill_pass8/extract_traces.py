"""Extract successful 32B vs 1.5B traces on the *same* queries, for side-by-side reading.

    python extract_traces.py [--per-dataset 4] [--outdir trace_samples]

Only queries both models solved are eligible, so every pair is a like-for-like
comparison. For each query the lowest successful seed is taken from each model, which
makes the selection deterministic and re-runnable.

Queries are chosen evenly spaced along the 1.5B/32B reasoning-length ratio, so the sample
spans both "both models reason similarly" and "the small model rambles" cases rather than
clustering on one behaviour.

Writes, per dataset, one markdown file per query (question, gold, then each model's
reasoning broken into numbered steps), plus a machine-readable steps.jsonl and an index.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

GEN = Path("/hdd1/ssn899/LargeModelFix/results/r1distill_pass8/generations")
GRADED = Path("/hdd1/ssn899/LargeModelFix/results/r1distill_pass8/graded")
SUBSETS = Path("/hdd1/ssn899/LargeModelFix/datasets/subsets")
DATASETS = ["gsm8k", "webinstruct", "livecodebench"]
TAGS = {"ds32b": "32B", "ds15b": "1.5B"}


def split_steps(thinking: str) -> list[str]:
    """The prompt asks for one blank line between reasoning steps."""
    return [s.strip() for s in thinking.split("\n\n") if s.strip()]


def load_correct(dataset: str) -> dict[str, dict[str, list[int]]]:
    """{tag: {query_id: [seeds that were correct]}}"""
    out = {}
    for tag in TAGS:
        ok = defaultdict(list)
        with open(GRADED / f"{tag}__{dataset}.graded.jsonl") as fh:
            for line in fh:
                r = json.loads(line)
                if r["correct"]:
                    ok[r["id"]].append(r["seed"])
        out[tag] = {k: sorted(v) for k, v in ok.items()}
    return out


def load_gen(dataset: str, tag: str, wanted: set) -> dict:
    """{(id, seed): row} for just the rows we need."""
    keep = {}
    with open(GEN / f"{tag}__{dataset}.jsonl") as fh:
        for line in fh:
            r = json.loads(line)
            key = (r["id"], r["seed"])
            if key in wanted:
                keep[key] = r
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-dataset", type=int, default=4)
    ap.add_argument("--outdir", default="trace_samples")
    args = ap.parse_args()

    out_root = Path(__file__).resolve().parent / args.outdir
    out_root.mkdir(parents=True, exist_ok=True)
    steps_fh = open(out_root / "steps.jsonl", "w")
    index_rows = []

    for dataset in DATASETS:
        subset = {json.loads(l)["id"]: json.loads(l)
                  for l in open(SUBSETS / f"{dataset}_first_100.jsonl")}
        correct = load_correct(dataset)
        both = sorted(set(correct["ds32b"]) & set(correct["ds15b"]))
        if not both:
            continue

        # lowest successful seed per model -> deterministic choice
        picks = {qid: {t: correct[t][qid][0] for t in TAGS} for qid in both}
        rows = {}
        for tag in TAGS:
            rows[tag] = load_gen(dataset, tag,
                                 {(q, picks[q][tag]) for q in both})

        # rank by how much longer the small model's reasoning is, then sample evenly
        def ratio(qid):
            a = len(split_steps(rows["ds32b"][(qid, picks[qid]["ds32b"])]["thinking"]))
            b = len(split_steps(rows["ds15b"][(qid, picks[qid]["ds15b"])]["thinking"]))
            return b / max(a, 1)

        ranked = sorted(both, key=ratio)
        n = min(args.per_dataset, len(ranked))
        chosen = [ranked[round(i * (len(ranked) - 1) / max(n - 1, 1))] for i in range(n)]
        chosen = list(dict.fromkeys(chosen))       # de-dup if the list is short

        ddir = out_root / dataset
        ddir.mkdir(exist_ok=True)
        for qid in chosen:
            rec = subset[qid]
            md = [f"# {dataset} — `{qid}`", ""]
            gold = rec.get("gold")
            md += ["## Question", "", "```", rec["question"].strip()[:4000], "```", ""]
            if gold is not None:
                md += [f"**Gold answer:** `{gold}`", ""]
            else:
                md += [f"**Graded by:** LiveCodeBench executor "
                       f"({rec['meta']['platform']}, {rec['meta']['difficulty']})", ""]

            summary = []
            for tag, label in TAGS.items():
                r = rows[tag][(qid, picks[qid][tag])]
                summary.append((label, len(split_steps(r["thinking"])),
                                r["completion_tokens"], r["seed"]))
            md += ["## Comparison", "",
                   "| model | reasoning steps | completion tokens | seed |",
                   "|---|---|---|---|"]
            md += [f"| {l} | {s} | {t} | {sd} |" for l, s, t, sd in summary]
            md += [""]

            for tag, label in TAGS.items():
                r = rows[tag][(qid, picks[qid][tag])]
                steps = split_steps(r["thinking"])
                md += [f"## {label} — seed {r['seed']} — {len(steps)} steps "
                       f"({r['completion_tokens']} tokens)", ""]
                for i, s in enumerate(steps, 1):
                    md += [f"**Step {i}**", "", s, ""]
                md += ["### Final answer (after `</think>`)", "",
                       "```", r["final_answer"].strip()[:3000], "```", ""]
                steps_fh.write(json.dumps({
                    "dataset": dataset, "id": qid, "model": label,
                    "seed": r["seed"], "correct": True,
                    "n_steps": len(steps), "completion_tokens": r["completion_tokens"],
                    "steps": steps, "final_answer": r["final_answer"],
                }) + "\n")

            (ddir / f"{qid}.md").write_text("\n".join(md))
            index_rows.append((dataset, qid, summary))

    steps_fh.close()

    idx = ["# Sampled reasoning traces: 32B vs 1.5B", "",
           "Successful traces only, on queries **both** models solved, so each row is a",
           "like-for-like comparison. Lowest correct seed per model. Reasoning is split on",
           "the blank line the prompt asks for between steps.", "",
           "Generated by `extract_traces.py`. Structured version: `steps.jsonl`.", "",
           "| dataset | query | 32B steps | 1.5B steps | 32B tokens | 1.5B tokens | file |",
           "|---|---|---|---|---|---|---|"]
    for dataset, qid, summary in index_rows:
        d = dict((l, (s, t)) for l, s, t, _ in summary)
        idx.append(f"| {dataset} | `{qid}` | {d['32B'][0]} | {d['1.5B'][0]} | "
                   f"{d['32B'][1]} | {d['1.5B'][1]} | [{qid}.md]({dataset}/{qid}.md) |")
    (out_root / "README.md").write_text("\n".join(idx) + "\n")
    print(f"wrote {len(index_rows)} query comparisons -> {out_root}")


if __name__ == "__main__":
    main()

"""Export the v2 prompt test traces next to their v1 counterparts.

    python export_v2_traces.py [--outdir trace_samples_v2]

Answers two questions:
  1. Compliance -- is the section after </think> now *only* the final answer?
  2. Did the stricter prompt change accuracy on the same queries?
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

RES = Path("/hdd1/ssn899/LargeModelFix/results/r1distill_pass8")
SUBSETS = Path("/hdd1/ssn899/LargeModelFix/datasets/subsets")
DATASETS = ["gsm8k", "webinstruct", "livecodebench"]
TAGS = {"ds32b": "32B", "ds15b": "1.5B"}

_BOXED_ONLY = re.compile(r"^\s*\\boxed\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}\s*$")
_CODE_ONLY = re.compile(r"^\s*```(?:python)?\s*\n.*?\n```\s*$", re.S)


def compliant(answer: str, grader: str) -> bool:
    """True when the answer section is *exactly* the required final answer, nothing else."""
    return bool((_CODE_ONLY if grader == "codegen" else _BOXED_ONLY).match(answer))


def extra_chars(answer: str, grader: str) -> int:
    """How much text surrounds the required answer."""
    a = answer.strip()
    if grader == "codegen":
        m = re.search(r"```(?:python)?\s*\n.*?\n```", a, re.S)
    else:
        m = re.search(r"\\boxed\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", a)
    return len(a) - (len(m.group(0)) if m else 0)


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in open(path)] if path.exists() else []


def split_steps(t: str) -> list[str]:
    return [s.strip() for s in t.split("\n\n") if s.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="trace_samples_v2")
    args = ap.parse_args()
    out = Path(__file__).resolve().parent / args.outdir
    out.mkdir(parents=True, exist_ok=True)

    stats, acc = [], []
    for dataset in DATASETS:
        subset = {json.loads(l)["id"]: json.loads(l)
                  for l in open(SUBSETS / f"{dataset}_first_100.jsonl")}
        ddir = out / dataset
        ddir.mkdir(exist_ok=True)

        v2rows, v1rows, v2ok, v1ok = {}, {}, {}, {}
        for tag in TAGS:
            v2 = load(RES / "generations" / f"v2test_{tag}__{dataset}.jsonl")
            qids = {r["id"] for r in v2}
            v2rows[tag] = v2
            v1rows[tag] = [r for r in load(RES / "generations" / f"{tag}__{dataset}.jsonl")
                           if r["id"] in qids]
            v2ok[tag] = {(r["id"], r["seed"]): r["correct"] for r in
                         load(RES / "graded_v2test" / f"v2test_{tag}__{dataset}.graded.jsonl")}
            v1ok[tag] = {(r["id"], r["seed"]): r["correct"] for r in
                         load(RES / "graded" / f"{tag}__{dataset}.graded.jsonl")
                         if r["id"] in qids}

        for tag, label in TAGS.items():
            for ver, rows in (("v1", v1rows[tag]), ("v2", v2rows[tag])):
                if not rows:
                    continue
                g = subset[rows[0]["id"]]["meta"]["grader"]
                cs = [compliant(r["final_answer"], g) for r in rows]
                ex = [extra_chars(r["final_answer"], g) for r in rows]
                stats.append((dataset, label, ver, len(rows), sum(cs),
                              sorted(ex)[len(ex) // 2]))
            ok1, ok2 = v1ok[tag], v2ok[tag]
            shared = set(ok1) & set(ok2)
            if shared:
                acc.append((dataset, label,
                            sum(ok1[k] for k in shared) / len(shared),
                            sum(ok2[k] for k in shared) / len(shared), len(shared)))

        # per-query markdown: v2 traces for both models, with the v1 answer section for contrast
        for qid in sorted({r["id"] for r in v2rows["ds32b"]}):
            rec = subset[qid]
            g = rec["meta"]["grader"]
            md = [f"# {dataset} — `{qid}` (prompt v2)", "", "## Question", "",
                  "```", rec["question"].strip()[:3000], "```", ""]
            if rec.get("gold") is not None:
                md += [f"**Gold answer:** `{rec['gold']}`", ""]
            for tag, label in TAGS.items():
                cand = sorted([r for r in v2rows[tag] if r["id"] == qid],
                              key=lambda r: (not v2ok[tag].get((r["id"], r["seed"])), r["seed"]))
                if not cand:
                    continue
                r = cand[0]
                steps = split_steps(r["thinking"])
                ok = v2ok[tag].get((r["id"], r["seed"]))
                md += [f"## {label} — seed {r['seed']} — {len(steps)} steps, "
                       f"{r['completion_tokens']} tokens — correct: {ok}", "",
                       f"**Answer section is exactly the final answer:** "
                       f"`{compliant(r['final_answer'], g)}`", ""]
                v1c = [x for x in v1rows[tag] if x["id"] == qid]
                if v1c:
                    md += ["<details><summary>v1 answer section (old prompt) — for "
                           "contrast</summary>", "", "```",
                           v1c[0]["final_answer"].strip()[:1500], "```", "", "</details>", ""]
                md += ["### v2 answer section (after `</think>`)", "", "```",
                       r["final_answer"].strip()[:2000], "```", "", "### Reasoning steps", ""]
                for i, s in enumerate(steps, 1):
                    md += [f"**Step {i}**", "", s, ""]
            (ddir / f"{qid}.md").write_text("\n".join(md))

    lines = ["# Prompt v2 test run", "",
             "12 queries (the ones sampled in `trace_samples/`), both models, 8 seeds each",
             "= 192 traces. Generated with `PROMPT_VERSION = v2`, which requires the section",
             "after `</think>` to be *only* the final answer.", "",
             "## Compliance: is the answer section exactly the final answer?", "",
             "| dataset | model | prompt | traces | compliant | median extra chars |",
             "|---|---|---|---|---|---|"]
    for d, m, v, n, c, e in stats:
        lines.append(f"| {d} | {m} | **{v}** | {n} | {c}/{n} ({c/n*100:.0f}%) | {e} |")
    lines += ["", "## Accuracy on the same (query, seed) pairs", "",
              "| dataset | model | v1 | v2 | n |", "|---|---|---|---|---|"]
    for d, m, a1, a2, n in acc:
        lines.append(f"| {d} | {m} | {a1*100:.0f}% | {a2*100:.0f}% | {n} |")
    lines += ["", "Per-query traces are in the dataset subfolders; each file shows the v2",
              "reasoning steps and answer section, with the v1 answer section collapsed",
              "underneath for contrast.", ""]
    (out / "README.md").write_text("\n".join(lines))
    print("\n".join(lines[:40]))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()

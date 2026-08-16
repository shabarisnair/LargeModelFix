"""Normalise AIME 2024 / 2025 into one schema and pick the demonstration examples.

Writes into datasets/:
    aime2024.jsonl, aime2025.jsonl   {id, dataset, question, gold}
    demos.json                        4 gold-standard DAG demonstrations
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pyarrow.parquet as pq

D = Path(__file__).resolve().parent / "datasets"


def build_aime2024():
    rows = pq.read_table(D / "raw/aime_2024_problems.parquet").to_pylist()
    return [{"id": f"aime2024-{r['ID']}", "dataset": "aime2024",
             "question": r["Problem"].strip(), "gold": str(r["Answer"]).strip()}
            for r in rows]


def build_aime2025():
    rows = [json.loads(l) for l in open(D / "raw/test.jsonl")]
    return [{"id": f"aime2025-{r['id']}", "dataset": "aime2025",
             "question": r["problem"].strip(), "gold": str(r["answer"]).strip()}
            for r in rows]


# --- demonstration selection -----------------------------------------------------
def well_formed(steps: list[dict]) -> bool:
    """The demos must obey every rule the prompt asks the model to follow."""
    ids = [s["step_id"] for s in steps]
    if ids != sorted(ids) or len(set(ids)) != len(ids):
        return False
    cited = set()
    for s in steps:
        dd = s.get("direct_dependent_steps")
        if dd is not None:
            if dd != sorted(dd) or any(d >= s["step_id"] for d in dd):
                return False           # topological order
            cited |= set(dd)
            # every dependency must be named as "Step N" in the edge prose
            named = {int(m) for m in re.findall(r"Step\s+(\d+)", s["edge"])}
            if not set(dd).issubset(named):
                return False
        # the bad examples show plural grouping ("Steps 8, 9 and 10") being rejected
        if re.search(r"\bSteps\s+\d+", s["edge"]):
            return False
    # closure: every non-final step is used later
    if any(sid not in cited for sid in ids[:-1]):
        return False
    return steps[-1]["node"].strip().lower().startswith("the final answer is")


_INT_ANSWER = re.compile(r"^\s*\\boxed\{\s*-?\d+\s*\}\s*\.?\s*$")


def integer_answer(rec: dict) -> bool:
    """AIME answers are always integers 0-999.

    problems_merged contains symbolic answers too (e.g. \\boxed{\\binom{\\binom{n}{k}}{m}}).
    Demonstrating those would teach the wrong final-answer shape for this benchmark.
    """
    tail = rec["final_answer"].replace("The final answer is", "").strip()
    return bool(_INT_ANSWER.match(tail.replace("$", "")))


def pick_demos(n=4, lo=6, hi=12):
    rows = [json.loads(l) for l in
            open(D / "problems_merged.jsonl", encoding="utf-8-sig")]
    cands = [r for r in rows
             if lo <= len(r["steps"]) <= hi and integer_answer(r) and well_formed(r["steps"])]
    cands.sort(key=lambda r: (len(r["steps"]), len(r["problem_text"])))
    picked, seen = [], set()
    for r in cands:                       # spread across topics
        topic = (r.get("domain") or ["?"])[0].split("->")[1].strip() if r.get("domain") else "?"
        if topic in seen:
            continue
        seen.add(topic)
        picked.append(r)
        if len(picked) == n:
            break
    while len(picked) < n and cands:      # fall back if topics are too few
        r = cands[len(picked)]
        if r not in picked:
            picked.append(r)
    return picked


def main():
    for name, rows in [("aime2024", build_aime2024()), ("aime2025", build_aime2025())]:
        p = D / f"{name}.jsonl"
        with open(p, "w") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        print(f"{name}: {len(rows)} problems -> {p}")

    demos = pick_demos()
    (D / "demos.json").write_text(json.dumps(demos, indent=1))
    print(f"\ndemonstrations: {len(demos)}")
    for r in demos:
        topic = (r.get("domain") or ["?"])[0]
        print(f"  problem_id={r['problem_id']:5d} steps={len(r['steps']):3d} "
              f"chars={len(json.dumps(r['steps'])):6d}  {topic[:58]}")


if __name__ == "__main__":
    main()

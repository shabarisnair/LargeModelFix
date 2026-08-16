"""Grade a generation jsonl. CPU only -- runs alongside generation.

    python grade.py --gen <generations.jsonl> --outdir <dir>

Writes <outdir>/<stem>.graded.jsonl (one row per query x seed) and
<outdir>/<stem>.summary.json (per-seed accuracy + mean/std across seeds).

pass@1 is measured directly: each of the 8 samples is graded independently, the
accuracy of each seed is computed over the queries, and those 8 accuracies are averaged.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

LCB_REPO = "/hdd1/ssn899/LargeModelFix/datasets/livecodebench/LiveCodeBench"
SUBSETS = Path("/hdd1/ssn899/LargeModelFix/datasets/subsets")

# --- answer extraction ------------------------------------------------------------
def extract_boxed(text: str) -> str | None:
    """Content of the last \\boxed{...}, brace-balanced."""
    key = "\\boxed{"
    start = text.rfind(key)
    if start == -1:
        return None
    i, depth, out = start + len(key), 1, []
    while i < len(text) and depth > 0:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
        out.append(c)
        i += 1
    return "".join(out).strip()


_NUM = r"[+-]?(?:\d+\.?\d*|\.\d+)"
# Accepts 2.1e-5, "21 x 10^-6", and LaTeX "2.1 \times 10^{-5}" / "\cdot 10^{-5}".
_SCI_RE = re.compile(
    rf"^({_NUM})\s*(?:(?:\\times|\\cdot|[x×*])\s*10\s*\^?\s*{{?({_NUM})}}?"
    rf"|[eE]([+-]?\d+))"
)


def parse_number(s: str):
    """Best-effort float from a model's boxed answer (strips LaTeX/units)."""
    if s is None:
        return None
    s = s.strip()
    for pat, rep in [(r"\\text\{[^}]*\}", ""), (r"\\mathrm\{[^}]*\}", ""),
                     (r"\\,|\\;|\\!|\\ ", ""), (r"\\%", ""), (r"[,\$]", ""),
                     (r"\\left|\\right", "")]:
        s = re.sub(pat, rep, s)
    s = s.replace("−", "-").replace("^{\\circ}", "").strip()
    m = re.match(rf"^\\d?frac\{{({_NUM})\}}\{{({_NUM})\}}$", s) or \
        re.match(rf"^\\frac\{{({_NUM})\}}\{{({_NUM})\}}$", s)
    if m:
        try:
            return float(m.group(1)) / float(m.group(2))
        except (ValueError, ZeroDivisionError):
            return None
    m = _SCI_RE.match(s)
    if m:
        exp = m.group(2) if m.group(2) is not None else m.group(3)
        try:
            return float(m.group(1)) * 10 ** int(float(exp))
        except ValueError:
            return None
    m = re.match(rf"^({_NUM})", s)
    return float(m.group(1)) if m else None


REL_TOL = 1e-2   # golds are rounded to 2-3 significant figures


def grade_numeric(row, meta) -> tuple[bool, str | None]:
    boxed = extract_boxed(row["final_answer"])
    pred = parse_number(boxed)
    if pred is None:
        return False, boxed
    gold = meta["gold_value"]
    if meta.get("is_integer"):
        return abs(pred - gold) < 1e-6, boxed
    if gold == 0:
        return abs(pred) < 1e-9, boxed
    return abs(pred - gold) / abs(gold) <= REL_TOL, boxed


def grade_mcq(row, meta) -> tuple[bool, str | None]:
    boxed = extract_boxed(row["final_answer"]) or ""
    m = re.search(r"[A-E]", boxed.upper())
    pred = m.group(0) if m else None
    return pred is not None and pred == row["gold"].strip().upper(), pred


# --- main -------------------------------------------------------------------------
def load_gen(path: Path) -> list[dict]:
    rows = []
    with open(path) as fh:
        for line in fh:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def grade_codegen(rows_by_id, subset, order, nproc):
    """Run the official LiveCodeBench executor. Returns {id: {seed: bool}}."""
    sys.path.insert(0, LCB_REPO)
    from lcb_runner.benchmarks.code_generation import CodeGenerationProblem
    from lcb_runner.evaluation import codegen_metrics, extract_instance_results
    from lcb_runner.utils.extraction_utils import extract_code
    from lcb_runner.lm_styles import LMStyle

    ids = [i for i in order if i in rows_by_id]
    samples, generations, seeds_per_id = [], [], []
    for qid in ids:
        prob = CodeGenerationProblem(**subset[qid]["meta"]["raw"])
        samples.append(prob.get_evaluation_sample())
        srows = sorted(rows_by_id[qid], key=lambda r: r["seed"])
        seeds_per_id.append([r["seed"] for r in srows])
        # OpenAIChat style => take the last ```...``` block, which is what we asked for.
        generations.append([extract_code(r["final_answer"], LMStyle.OpenAIChat)
                            for r in srows])
    _, results, _ = codegen_metrics(samples, generations, k_list=[1],
                                    num_process_evaluate=nproc, timeout=6)
    graded = extract_instance_results(results)
    out = {}
    for qid, seeds, flags, gens in zip(ids, seeds_per_id, graded, generations):
        out[qid] = {s: (bool(f), g) for s, f, g in zip(seeds, flags, gens)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--nproc", type=int, default=32, help="LCB executor processes")
    args = ap.parse_args()

    gen_path = Path(args.gen)
    rows = load_gen(gen_path)
    if not rows:
        raise SystemExit(f"no rows in {gen_path}")
    dataset = rows[0]["dataset"]
    model = rows[0]["model"]

    with open(SUBSETS / f"{dataset}_first_100.jsonl") as fh:
        subset = {}
        order = []
        for line in fh:
            r = json.loads(line)
            subset[r["id"]] = r
            order.append(r["id"])

    # Keep one row per (id, seed). Sharding a dataset across two endpoints, or resuming
    # an interrupted run, can append the same sample twice; counting both would skew the
    # per-seed accuracy.
    seen, rows_by_id = set(), defaultdict(list)
    dupes = 0
    for r in rows:
        key = (r["id"], r["seed"])
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        rows_by_id[r["id"]].append(r)
    if dupes:
        print(f"  (dropped {dupes} duplicate (id, seed) rows)")

    graded_rows = []
    if dataset == "livecodebench":
        cg = grade_codegen(rows_by_id, subset, order, args.nproc)
        for qid, srows in rows_by_id.items():
            for r in srows:
                ok, code = cg.get(qid, {}).get(r["seed"], (False, ""))
                graded_rows.append({**{k: r[k] for k in
                                       ("id", "dataset", "model", "seed",
                                        "finish_reason", "closed_think",
                                        "completion_tokens")},
                                    "correct": ok, "extracted": code[:2000],
                                    "gold": None})
    else:
        for qid, srows in rows_by_id.items():
            meta = subset[qid]["meta"]
            fn = grade_mcq if meta["grader"] == "mcq" else grade_numeric
            for r in srows:
                ok, pred = fn(r, meta)
                graded_rows.append({**{k: r[k] for k in
                                       ("id", "dataset", "model", "seed",
                                        "finish_reason", "closed_think",
                                        "completion_tokens")},
                                    "correct": bool(ok), "extracted": pred,
                                    "gold": r["gold"]})

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = gen_path.name.replace(".jsonl", "")
    graded_path = outdir / f"{stem}.graded.jsonl"
    with open(graded_path, "w") as fh:
        for r in sorted(graded_rows, key=lambda x: (x["id"], x["seed"])):
            fh.write(json.dumps(r) + "\n")

    # per-seed accuracy over queries, then mean across seeds = pass@1
    by_seed = defaultdict(list)
    for r in graded_rows:
        by_seed[r["seed"]].append(r["correct"])
    per_seed = {s: sum(v) / len(v) for s, v in sorted(by_seed.items())}
    accs = list(per_seed.values())
    per_query = {qid: sum(x["correct"] for x in g) / len(g)
                 for qid, g in
                 [(q, [r for r in graded_rows if r["id"] == q]) for q in rows_by_id]}
    truncated = sum(1 for r in graded_rows if r["finish_reason"] == "length")
    summary = {
        "model": model, "dataset": dataset,
        "n_queries": len(rows_by_id), "n_seeds": len(per_seed),
        "n_rows": len(graded_rows),
        "pass@1_mean": statistics.mean(accs),
        "pass@1_std": statistics.pstdev(accs) if len(accs) > 1 else 0.0,
        "per_seed_accuracy": per_seed,
        "truncated_at_max_tokens": truncated,
        "unclosed_think": sum(1 for r in graded_rows if not r["closed_think"]),
        "mean_completion_tokens": statistics.mean(
            [r["completion_tokens"] for r in graded_rows if r["completion_tokens"]] or [0]),
        "per_query_pass_rate": per_query,
    }
    with open(outdir / f"{stem}.summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)

    print(f"{model} | {dataset}: pass@1 = {summary['pass@1_mean']:.3f} "
          f"+/- {summary['pass@1_std']:.3f}  (n={len(rows_by_id)} queries, "
          f"{len(per_seed)} seeds, {truncated} truncated)")
    print(f"  -> {graded_path}")


if __name__ == "__main__":
    main()

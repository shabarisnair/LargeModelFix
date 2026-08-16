"""Grade AIME answers and validate the emitted DAG.

    python grade.py --gen <generations.jsonl> --outdir <dir>

Two independent things are measured, because a run can be right for the wrong reasons:
  * accuracy   -- does the final step's answer match the AIME gold integer?
  * DAG health -- is the output valid JSON, are step_ids contiguous, are dependencies
                  topological, is every non-final step actually used later, and does the
                  edge prose cite each dependency as "Step N" as the prompt demands?

pass@1 is the mean over seeds of each seed's accuracy across problems.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from collections import defaultdict
from pathlib import Path

FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)
BOXED_RE = re.compile(r"\\boxed\{([^{}]*)\}")
FINAL_RE = re.compile(r"final answer is\s*:?\s*(.*)", re.I)

_VALID_ESC = set('"\\/bfnrtu')
_HEX = set("0123456789abcdefABCDEF")
# \b \f \r \t are legal JSON escapes, so json.loads happily turns single-backslash LaTeX
# into control characters: \frac -> FF+"rac", \boxed -> BS+"oxed", \right -> CR+"ight",
# \times -> TAB+"imes". That silently destroys the command name (and defeats \boxed
# extraction). In this corpus a control character followed by a lowercase letter is
# always mangled LaTeX, never an intended backspace/formfeed, so those are re-escaped.
# \n is deliberately excluded: real newlines inside strings are common and legitimate,
# and losing \neq / \nabla is the lesser evil.
_LATEX_AMBIGUOUS = set("bfrt")


def repair_json_escapes(s: str) -> str:
    """Escape stray backslashes inside JSON string literals.

    The prompt asks for LaTeX in dollar signs *and* strict JSON, which conflict: the
    models write "$S = \\{1,\\ldots,10\\}$" with single backslashes, and \\{ / \\l are not
    legal JSON escapes, so the whole object fails to parse. Doubling only the invalid
    backslashes leaves the LaTeX intact and the JSON loadable. Valid escapes (including
    well-formed \\uXXXX) are left untouched.
    """
    out, i, n, instr = [], 0, len(s), False
    while i < n:
        c = s[i]
        if not instr:
            out.append(c)
            if c == '"':
                instr = True
            i += 1
            continue
        if c == "\\":
            nxt = s[i + 1] if i + 1 < n else ""
            after = s[i + 2] if i + 2 < n else ""
            good = nxt in _VALID_ESC and (
                nxt != "u" or all(ch in _HEX for ch in s[i + 2:i + 6]))
            # \frac, \boxed, \right, \times ... : a LaTeX command, not a control char
            if good and nxt in _LATEX_AMBIGUOUS and after.isalpha():
                good = False
            if good:
                out.append(c)
                out.append(nxt)
                i += 2
            else:
                out.append("\\\\")
                i += 1
        elif c == '"':
            out.append(c)
            instr = False
            i += 1
        else:
            # a raw newline inside a string is also illegal; keep the text, fix the syntax
            out.append("\\n" if c == "\n" else c)
            i += 1
    return "".join(out)


def extract_json(text: str):
    """Return the steps list, or None. Tolerates code fences and trailing prose."""
    for cand in ([m.group(1) for m in FENCE_RE.finditer(text)] + [text]):
        cand = cand.strip()
        start = cand.find("{")
        if start == -1:
            continue
        # walk braces to find the end of the first complete object
        depth, instr, esc = 0, False, False
        for i, ch in enumerate(cand[start:], start):
            if instr:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    instr = False
                continue
            if ch == '"':
                instr = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    blob = cand[start:i + 1]
                    obj = None
                    for attempt in (blob, repair_json_escapes(blob)):
                        try:
                            obj = json.loads(attempt)
                            break
                        except json.JSONDecodeError:
                            continue
                    if obj is None:
                        break
                    steps = obj.get("steps") if isinstance(obj, dict) else None
                    if isinstance(steps, list) and steps:
                        return steps
                    break
    return None


def step_text(s) -> str:
    """A step is a dict with a `node` in the DAG prompt, or a plain string in steps-only."""
    if isinstance(s, dict):
        return str(s.get("node", ""))
    return str(s)


def answer_of(steps: list) -> str | None:
    """AIME answers are integers 0-999; take them from the final step."""
    for s in reversed(steps):
        node = step_text(s)
        m = BOXED_RE.search(node)
        if m:
            digits = re.findall(r"-?\d+", m.group(1))
            if digits:
                return digits[-1]
        m = FINAL_RE.search(node)
        if m:
            digits = re.findall(r"-?\d+", m.group(1))
            if digits:
                return digits[0]
    return None


def dag_health(steps: list) -> dict:
    # The steps-only prompt emits bare strings: there is no step_id, edge or dependency
    # list to check, so only the step count and the final-answer form are meaningful.
    if not all(isinstance(s, dict) for s in steps):
        return {"n_steps": len(steps), "contiguous_ids": None, "topological": None,
                "closure": None, "citations_ok": None, "plural_citation": None,
                "roots": None, "dep_steps": 0, "cited_steps": 0, "well_formed": None}
    ids = [s.get("step_id") for s in steps]
    contiguous = ids == list(range(1, len(ids) + 1)) or ids == list(range(len(ids)))
    topo = True
    cited_all = set()
    citations_ok = True
    plural = False
    for s in steps:
        dd = s.get("direct_dependent_steps")
        if dd in (None, []):
            continue
        if not isinstance(dd, list):
            topo = False
            continue
        if dd != sorted(dd) or any(d >= s.get("step_id", 0) for d in dd):
            topo = False
        cited_all |= set(dd)
        named = {int(m) for m in re.findall(r"Step\s+(\d+)", str(s.get("edge", "")))}
        if not set(dd).issubset(named):
            citations_ok = False
        if re.search(r"\bSteps\s+\d+", str(s.get("edge", ""))):
            plural = True
    closure = all(i in cited_all for i in ids[:-1]) if len(ids) > 1 else True
    roots = sum(1 for s in steps if s.get("direct_dependent_steps") in (None, []))
    # per-step citation counts: the response-level flag is all-or-nothing, so one missed
    # citation in twenty steps looks identical to citing nothing at all.
    dep_steps = cited_steps = 0
    for s in steps:
        dd = s.get("direct_dependent_steps")
        if not isinstance(dd, list) or not dd:
            continue
        dep_steps += 1
        named = {int(m) for m in re.findall(r"Step\s+(\d+)", str(s.get("edge", "")))}
        if set(dd).issubset(named):
            cited_steps += 1
    return {"n_steps": len(steps), "contiguous_ids": contiguous, "topological": topo,
            "closure": closure, "citations_ok": citations_ok, "plural_citation": plural,
            "roots": roots, "dep_steps": dep_steps, "cited_steps": cited_steps,
            "well_formed": bool(contiguous and topo and closure and citations_ok
                                and not plural)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.gen) if l.strip()]
    if not rows:
        raise SystemExit(f"no rows in {args.gen}")

    seen, graded = set(), []
    for r in rows:
        key = (r["id"], r["seed"])
        if key in seen:
            continue
        seen.add(key)
        steps = extract_json(r["response"])
        pred = answer_of(steps) if steps else None
        gold = str(r["gold"]).strip()
        correct = pred is not None and pred.lstrip("0") == gold.lstrip("0") or pred == gold
        health = dag_health(steps) if steps else {"n_steps": 0, "well_formed": False}
        graded.append({**{k: r[k] for k in
                          ("id", "dataset", "model", "seed", "finish_reason",
                           "completion_tokens")},
                       "gold": gold, "pred": pred, "correct": bool(correct),
                       "valid_json": steps is not None, **health})

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = Path(args.gen).name.replace(".jsonl", "")
    with open(outdir / f"{stem}.graded.jsonl", "w") as fh:
        for g in sorted(graded, key=lambda x: (x["id"], x["seed"])):
            fh.write(json.dumps(g) + "\n")

    by_seed = defaultdict(list)
    for g in graded:
        by_seed[g["seed"]].append(g["correct"])
    per_seed = {s: sum(v) / len(v) for s, v in sorted(by_seed.items())}
    accs = list(per_seed.values())
    n = len(graded)
    summary = {
        "model": rows[0]["model"], "dataset": rows[0]["dataset"],
        "n_problems": len({g["id"] for g in graded}), "n_seeds": len(per_seed),
        "n_rows": n,
        "pass@1_mean": statistics.mean(accs) if accs else 0.0,
        "pass@1_std": statistics.pstdev(accs) if len(accs) > 1 else 0.0,
        "per_seed_accuracy": per_seed,
        "valid_json_rate": sum(g["valid_json"] for g in graded) / n,
        # The five prompt rules are reported individually. A single AND of them is
        # uninformative here: citations_ok is ~0 at every model scale, which would pin any
        # composite to 0 and hide the fact that ids/topology are largely satisfied.
        "contiguous_ids_rate": sum(g.get("contiguous_ids", False) for g in graded) / n,
        "topological_rate": sum(g.get("topological", False) for g in graded) / n,
        "closure_rate": sum(g.get("closure", False) for g in graded) / n,
        "citations_ok_rate": sum(g.get("citations_ok", False) for g in graded) / n,
        "plural_citation_rate": sum(g.get("plural_citation", False) for g in graded) / n,
        # per-step citation compliance, which the per-response flag above cannot show
        "step_citation_rate": (
            sum(g.get("cited_steps", 0) for g in graded)
            / max(sum(g.get("dep_steps", 0) for g in graded), 1)),
        "well_formed_dag_rate": sum(g.get("well_formed", False) for g in graded) / n,
        "median_steps": statistics.median([g["n_steps"] for g in graded]),
        "truncated": sum(1 for g in graded if g["finish_reason"] == "length"),
        "mean_completion_tokens": statistics.mean(
            [g["completion_tokens"] for g in graded if g["completion_tokens"]] or [0]),
    }
    with open(outdir / f"{stem}.summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)
    print(f"{summary['model'].split('/')[-1]:28s} {summary['dataset']:9s} "
          f"pass@1={summary['pass@1_mean']*100:5.1f}% +/-{summary['pass@1_std']*100:4.1f} | "
          f"json={summary['valid_json_rate']*100:4.0f}% ids={summary['contiguous_ids_rate']*100:4.0f}% "
          f"topo={summary['topological_rate']*100:4.0f}% closed={summary['closure_rate']*100:4.0f}% "
          f"cites={summary['citations_ok_rate']*100:4.0f}% "
          f"steps={summary['median_steps']:.0f} trunc={summary['truncated']}")


if __name__ == "__main__":
    main()

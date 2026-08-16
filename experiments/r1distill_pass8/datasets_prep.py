"""Build the *_first_100 evaluation subsets.

  gsm8k_first_100          first 100 rows of the GSM8K test split
  webinstruct_first_100    first 100 rows that are *machine-checkable* (see keep_webinstruct)
  livecodebench_first_100  the 100 newest problems by contest_date in release_v6

Each subset is written as jsonl with a uniform envelope:
    {id, dataset, question, gold, meta{...}}
LiveCodeBench additionally keeps the raw problem row under meta["raw"], because the
official evaluator needs the public+private test cases.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pyarrow.parquet as pq

DATA = Path("/hdd1/ssn899/LargeModelFix/datasets")
OUT = DATA / "subsets"
N = 100

# --- numeric gold parsing ---------------------------------------------------------
# A gold is usable only if it contains exactly ONE number; multi-part answers like
# "R_1 = 2.22 Ohm, R_2 = 3.28 Ohm" are not gradeable from a single \boxed{} value.
_SCI = r"[+-]?(?:\d+\.?\d*|\.\d+)\s*(?:[x×*]\s*10\s*\^?\s*|[eE])\s*[+-]?\d+"
_PLAIN = r"[+-]?(?:\d+\.?\d*|\.\d+)"
_NUM_RE = re.compile(f"(?:{_SCI})|(?:{_PLAIN})")
_SCI_RE = re.compile(f"^({_PLAIN})\\s*(?:[x×*]\\s*10\\s*\\^?\\s*|[eE])\\s*([+-]?\\d+)$")


def _clean(s: str) -> str:
    return s.strip().replace(",", "").replace("$", "").replace("\\", "")


def parse_single_number(gold: str):
    """Return float(gold) if the gold contains exactly one number, else None."""
    s = _clean(gold)
    nums = _NUM_RE.findall(s)
    if len(nums) != 1:
        return None
    tok = _NUM_RE.search(s).group(0)
    m = _SCI_RE.match(tok.strip())
    if m:
        return float(m.group(1)) * 10 ** int(m.group(2))
    try:
        return float(tok)
    except ValueError:
        return None


_OPT_RE = re.compile(r"(?:^|[\s|(])([A-E])[\)\.]\s", re.M)


_BARE_INT = re.compile(r"^[+-]?\d+$")
_BARE_DEC = re.compile(f"^(?:{_SCI})$|^{_PLAIN}$")


def keep_webinstruct(row) -> dict | None:
    """Keep only rows whose gold is *semantically* deterministic.

    Deliberately stricter than "the gold parses as a number". Golds that carry a unit
    ("65 m", "21 x 10^-6 T") are dropped: we ask the model for a bare number, so a
    correct answer expressed in a different unit would be scored wrong for a unit
    choice rather than a reasoning error. Prose/multi-part golds are dropped too --
    those need an LLM judge. See probe_tiers.py for the full census.
    """
    at, gold, q = row["answer_type"], row["answer"].strip(), row["question"]
    if at in ("Integer", "Float"):
        g = _clean(gold)
        if _BARE_INT.fullmatch(g):
            return {"grader": "numeric", "gold_value": float(g), "is_integer": True}
        if _BARE_DEC.fullmatch(g):
            val = parse_single_number(gold)
            if val is not None:
                return {"grader": "numeric", "gold_value": val, "is_integer": False}
        return None
    if at == "Multiple Choice":
        # Needs lettered options *in the question* and a single-letter gold, else the
        # model cannot possibly know what the letter refers to.
        if re.fullmatch(r"[A-E]", gold) and len(set(_OPT_RE.findall(q))) >= 2:
            return {"grader": "mcq", "options": sorted(set(_OPT_RE.findall(q)))}
    return None


def build_gsm8k():
    rows = pq.read_table(DATA / "gsm8k/main/test-00000-of-00001.parquet").to_pylist()
    out = []
    for i, r in enumerate(rows[:N]):
        gold = r["answer"].split("####")[-1].strip().replace(",", "")
        out.append({"id": f"gsm8k-{i}", "dataset": "gsm8k", "question": r["question"],
                    "gold": gold, "meta": {"grader": "numeric",
                                           "gold_value": float(gold),
                                           "is_integer": True}})
    return out


def build_webinstruct():
    rows = pq.read_table(DATA / "webinstruct/data/test-00000-of-00001.parquet").to_pylist()
    out, seen = [], {"Integer": 0, "Float": 0, "Multiple Choice": 0}
    for i, r in enumerate(rows):
        meta = keep_webinstruct(r)
        if meta is None:
            continue
        seen[r["answer_type"]] += 1
        meta.update(answer_type=r["answer_type"], category=r["category"],
                    difficulty=r["difficulty"], source_index=i)
        out.append({"id": f"webinstruct-{r['id']}", "dataset": "webinstruct",
                    "question": r["question"], "gold": r["answer"].strip(), "meta": meta})
        if len(out) == N:
            break
    print(f"  webinstruct kept composition: {seen}")
    return out


def build_livecodebench():
    rows = []
    for f in ["test.jsonl", "test2.jsonl", "test3.jsonl",
              "test4.jsonl", "test5.jsonl", "test6.jsonl"]:
        with open(DATA / "livecodebench" / f) as fh:
            rows.extend(json.loads(line) for line in fh)
    rows.sort(key=lambda r: r["contest_date"], reverse=True)
    picked = rows[:N]
    print(f"  livecodebench date span: {picked[-1]['contest_date'][:10]}"
          f" .. {picked[0]['contest_date'][:10]}")
    return [{"id": f"lcb-{r['question_id']}", "dataset": "livecodebench",
             "question": r["question_content"], "gold": None,
             "meta": {"grader": "codegen", "question_id": r["question_id"],
                      "platform": r["platform"], "difficulty": r["difficulty"],
                      "contest_date": r["contest_date"],
                      "starter_code": r["starter_code"], "raw": r}}
            for r in picked]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in [("gsm8k", build_gsm8k),
                     ("webinstruct", build_webinstruct),
                     ("livecodebench", build_livecodebench)]:
        recs = fn()
        path = OUT / f"{name}_first_100.jsonl"
        with open(path, "w") as fh:
            for r in recs:
                fh.write(json.dumps(r) + "\n")
        print(f"{name}_first_100: {len(recs)} rows -> {path}")


if __name__ == "__main__":
    main()

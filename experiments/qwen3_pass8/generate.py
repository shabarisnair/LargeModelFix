"""Sample 8 responses per AIME problem from a vLLM server and record them.

Qwen3 in NON-THINKING mode. Qwen3-30B-A3B-Instruct-2507 is non-thinking by design; the
hybrids (14B / 8B / 1.7B) default to thinking, so their chat template is rendered with
enable_thinking=False, which seeds an empty "<think></think>" pair and leaves the model
answering directly.

Sampling is Qwen's published non-thinking recommendation (temperature 0.7, top_p 0.8,
top_k 20, min_p 0), confirmed from the model cards.

The generation budget is 35000 rather than the 38000 originally intended: Qwen3-1.7B, -8B
and -14B have a native context of 40960 (only the 30B-A3B-2507 reaches 262144), and the
longest resolved prompt is 5785 tokens, which leaves 35175. One budget is used for all
four models so the runs stay comparable. YaRN could extend the hybrids, but Qwen advises
enabling it only when long context is genuinely needed.

One row per (problem, seed). Resumable: rows already present in --out are skipped.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from transformers import AutoTokenizer

import prompts as _p_dag
import prompts_stepsonly as _p_steps

PROMPT_STYLES = {"dag": _p_dag, "stepsonly": _p_steps}

HERE = Path(__file__).resolve().parent
DATASETS = HERE / "datasets"

# Fixed across every model x dataset combination so runs are directly comparable.
SEEDS = [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007]

# Qwen3 non-thinking mode, per the model cards.
TEMPERATURE = 0.7
TOP_P = 0.8
TOP_K = 20
MIN_P = 0.0


def load_dataset(name: str, limit: int | None = None, ids: str | None = None):
    rows = [json.loads(l) for l in open(DATASETS / f"{name}.jsonl")]
    if ids:
        want = set(ids.split(","))
        rows = [r for r in rows if r["id"] in want]
    return rows[:limit] if limit else rows


def is_reusable(r: dict, cfg: dict) -> bool:
    if r.get("model") != cfg["model"]:
        return False
    rc = r.get("config") or {}
    for k in ("temperature", "top_p", "top_k", "min_p", "prompt_version"):
        if rc.get(k) != cfg[k]:
            return False
    if rc.get("max_tokens") == cfg["max_tokens"]:
        return True
    if r.get("finish_reason") == "length":
        return False              # the old cap truncated it, so it must be redone
    return (r.get("completion_tokens") or 0) <= cfg["max_tokens"]


def scan_existing(dataset: str, cfg: dict, root: Path) -> dict:
    found = {}
    for path in sorted(root.rglob("*.jsonl")):
        if path.name.endswith(".graded.jsonl"):
            continue
        try:
            fh = open(path)
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "response" not in r or r.get("dataset") != dataset:
                    continue
                key = (r["id"], r["seed"])
                if key not in found and is_reusable(r, cfg):
                    r["_src"] = str(path)
                    found[key] = r
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--dataset", required=True, choices=["aime2024", "aime2025"])
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=35000)
    ap.add_argument("--concurrency", type=int, default=32)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--ids", default=None)
    ap.add_argument("--seeds", type=int, default=len(SEEDS))
    ap.add_argument("--timeout", type=float, default=3600.0)
    ap.add_argument("--results-root", default=None,
                    help="tree scanned for reusable traces (default: the output's parent)")
    ap.add_argument("--no-reuse", action="store_true")
    ap.add_argument("--prompt-style", default="dag", choices=sorted(PROMPT_STYLES),
                    help="dag = step_id/edge/dependencies; stepsonly = plain step list")
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pmod = PROMPT_STYLES[args.prompt_style]
    cfg = {"model": args.model, "max_tokens": args.max_tokens,
           "temperature": TEMPERATURE, "top_p": TOP_P, "top_k": TOP_K, "min_p": MIN_P,
           "prompt_version": pmod.PROMPT_VERSION}

    tok = AutoTokenizer.from_pretrained(args.model)
    recs = load_dataset(args.dataset, args.limit, args.ids)
    seeds = SEEDS[:args.seeds]

    root = Path(args.results_root) if args.results_root else out_path.parent
    existing = {} if args.no_reuse else scan_existing(args.dataset, cfg, root)
    wanted = {(r["id"], s) for r in recs for s in seeds}

    url = f"{args.base_url.rstrip('/')}/v1/completions"
    lock = threading.Lock()
    fh = open(out_path, "a")

    adopted = 0
    for key in sorted(wanted & set(existing)):
        row = existing[key]
        if row.pop("_src", None) != str(out_path):
            fh.write(json.dumps(row) + "\n")
            adopted += 1
    fh.flush()

    jobs = [(r, s) for r in recs for s in seeds if (r["id"], s) not in existing]
    print(f"{args.dataset} | {len(recs)} problems x {len(seeds)} seeds = {len(wanted)} rows; "
          f"{len(wanted & set(existing))} reused ({adopted} adopted), "
          f"{len(jobs)} to generate", flush=True)
    if not jobs:
        fh.close()
        return

    counter = {"n": 0, "t0": time.time()}

    def run(job):
        rec, seed = job
        user_prompt = pmod.build_prompt(rec["question"])
        # enable_thinking is ignored by templates that do not define it, so the same call
        # works for the natively non-thinking 2507 model and for the hybrids.
        prompt = tok.apply_chat_template(
            [{"role": "user", "content": user_prompt}],
            tokenize=False, add_generation_prompt=True, enable_thinking=False,
        )
        payload = {"model": args.model, "prompt": prompt, "seed": seed,
                   "max_tokens": args.max_tokens, "temperature": TEMPERATURE,
                   "top_p": TOP_P, "top_k": TOP_K, "min_p": MIN_P}
        t0 = time.time()
        resp = requests.post(url, json=payload, timeout=args.timeout)
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["text"]
        return {
            "id": rec["id"], "dataset": args.dataset, "model": args.model, "seed": seed,
            "question": rec["question"], "gold": rec["gold"],
            "response": text,
            "finish_reason": data["choices"][0].get("finish_reason"),
            "config": {"max_tokens": args.max_tokens, "temperature": TEMPERATURE,
                       "top_p": TOP_P, "top_k": TOP_K, "min_p": MIN_P,
                       "prompt_version": pmod.PROMPT_VERSION},
            "prompt_tokens": data.get("usage", {}).get("prompt_tokens"),
            "completion_tokens": data.get("usage", {}).get("completion_tokens"),
            "latency_s": round(time.time() - t0, 2),
        }

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futs = {pool.submit(run, j): j for j in jobs}
        for fut in as_completed(futs):
            rec, seed = futs[fut]
            try:
                row = fut.result()
            except Exception as e:
                print(f"  FAIL {rec['id']} seed={seed}: {type(e).__name__}: {e}", flush=True)
                continue
            with lock:
                fh.write(json.dumps(row) + "\n")
                fh.flush()
                counter["n"] += 1
                if counter["n"] % 25 == 0:
                    el = time.time() - counter["t0"]
                    print(f"  {counter['n']}/{len(jobs)} in {el/60:.1f}m "
                          f"({counter['n']/el*60:.1f}/min)", flush=True)
    fh.close()
    print(f"done: {counter['n']}/{len(jobs)} rows -> {out_path}", flush=True)


if __name__ == "__main__":
    main()

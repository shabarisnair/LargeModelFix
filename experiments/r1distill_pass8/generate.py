"""Sample 8 responses per query from a vLLM server and record them.

One row per (query, seed). Resumable: rows already present in --out are skipped, so a
crashed or interrupted run can simply be re-invoked.

    python generate.py --model deepseek-ai/DeepSeek-R1-Distill-Qwen-32B \
        --dataset livecodebench --base-url http://127.0.0.1:8002 --out <file.jsonl>
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

from prompts import build_prompt, PROMPT_VERSION, VERSIONS, PREFILL

SUBSETS = Path("/hdd1/ssn899/LargeModelFix/datasets/subsets")
RESULTS_ROOT = Path("/hdd1/ssn899/LargeModelFix/results")

# Fixed across every model x dataset combination so runs are directly comparable.
SEEDS = [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007]

# DeepSeek-recommended sampling for the R1-Distill family.
TEMPERATURE = 0.6
TOP_P = 0.95
TOP_K = 20

# Rows written before `config` was recorded came from this setting, under the v1 prompts.
LEGACY_CONFIG = {"max_tokens": 38000, "temperature": TEMPERATURE,
                 "top_p": TOP_P, "top_k": TOP_K, "prompt_version": "v1"}


def split_think(text: str) -> tuple[str, str]:
    """(thinking, final_answer). The chat template opens <think>, so only </think> appears."""
    idx = text.rfind("</think>")
    if idx == -1:
        return text, ""
    return text[:idx], text[idx + len("</think>"):]


def load_subset(dataset: str, limit: int | None) -> list[dict]:
    path = SUBSETS / f"{dataset}_first_100.jsonl"
    with open(path) as fh:
        recs = [json.loads(line) for line in fh]
    return recs[:limit] if limit else recs


def _row_config(r: dict) -> dict:
    return r.get("config") or LEGACY_CONFIG


def is_reusable(r: dict, cfg: dict) -> bool:
    """Can an existing trace stand in for a fresh sample under `cfg`?

    Sampling params and model must match exactly. A different max_tokens is fine only
    when the old cap provably never bound the generation: a trace that stopped on its
    own (finish_reason != "length") and fits inside the new cap is the same sample the
    new setting would have produced, so regenerating it would only burn GPU time.
    """
    if r.get("model") != cfg["model"]:
        return False
    rc = _row_config(r)
    if any(rc.get(k) != cfg[k] for k in ("temperature", "top_p", "top_k")):
        return False
    # A trace generated under different prompt text is a different experiment, however
    # closely the sampling parameters match.
    if rc.get("prompt_version", "v1") != cfg["prompt_version"]:
        return False
    if rc.get("max_tokens") == cfg["max_tokens"]:
        return True
    if r.get("finish_reason") == "length":
        return False                      # the old cap truncated it -> must redo
    return (r.get("completion_tokens") or 0) <= cfg["max_tokens"]


def scan_existing(dataset: str, cfg: dict, root: Path, out_path: Path) -> dict:
    """Index every reusable (id, seed) trace already on disk under `root`.

    Lets a rerun pick up traces produced by an earlier run under a different output
    name, so nothing with a matching configuration and seed is ever recomputed.
    """
    found = {}
    for path in sorted(root.rglob("*.jsonl")):
        if path.name.endswith((".graded.jsonl",)):
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
                    continue          # tolerate a torn final line from a hard kill
                if "response" not in r or r.get("dataset") != dataset:
                    continue
                key = (r["id"], r["seed"])
                if key not in found and is_reusable(r, cfg):
                    r["_reused_from"] = str(path) if path != out_path else None
                    found[key] = r
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--dataset", required=True,
                    choices=["gsm8k", "webinstruct", "livecodebench"])
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=45000)
    ap.add_argument("--concurrency", type=int, default=64)
    ap.add_argument("--limit", type=int, default=None, help="first N queries (test runs)")
    ap.add_argument("--ids", default=None,
                    help="comma-separated query ids to run instead of --limit")
    ap.add_argument("--seeds", type=int, default=len(SEEDS), help="first N seeds")
    ap.add_argument("--timeout", type=float, default=7200.0)
    ap.add_argument("--results-root", default=str(RESULTS_ROOT),
                    help="tree scanned for reusable traces")
    ap.add_argument("--no-reuse", action="store_true",
                    help="ignore existing traces and regenerate everything")
    ap.add_argument("--prompt-version", default=PROMPT_VERSION, choices=sorted(VERSIONS),
                    help="prompt variant; recorded on every row and gates trace reuse")
    args = ap.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cfg = {"model": args.model, "max_tokens": args.max_tokens,
           "temperature": TEMPERATURE, "top_p": TOP_P, "top_k": TOP_K,
           "prompt_version": args.prompt_version}

    tok = AutoTokenizer.from_pretrained(args.model)
    recs = load_subset(args.dataset, None if args.ids else args.limit)
    if args.ids:
        want = set(args.ids.split(","))
        recs = [r for r in recs if r["id"] in want]
    seeds = SEEDS[:args.seeds]

    existing = ({} if args.no_reuse
                else scan_existing(args.dataset, cfg, Path(args.results_root), out_path))
    wanted = {(r["id"], s) for r in recs for s in seeds}

    url = f"{args.base_url.rstrip('/')}/v1/completions"
    lock = threading.Lock()
    fh = open(out_path, "a")
    counter = {"n": 0, "t0": time.time()}

    # Adopt reusable traces that live in some *other* file so this run's output is
    # complete without regenerating them.
    adopted = 0
    for key in sorted(wanted & set(existing)):
        row = existing[key]
        if row.pop("_reused_from", None) is not None:
            fh.write(json.dumps(row) + "\n")
            adopted += 1
    fh.flush()

    jobs = [(r, s) for r in recs for s in seeds if (r["id"], s) not in existing]
    reused = len(wanted & set(existing))
    print(f"{args.dataset} | {len(recs)} queries x {len(seeds)} seeds = {len(wanted)} rows; "
          f"{reused} reused ({adopted} adopted from other files), "
          f"{len(jobs)} to generate", flush=True)
    if not jobs:
        fh.close()
        return

    def run(job):
        rec, seed = job
        user_prompt = build_prompt(rec, version=args.prompt_version)
        prompt = tok.apply_chat_template(
            [{"role": "user", "content": user_prompt}],
            tokenize=False, add_generation_prompt=True,
        )
        # v3/v4 need the first index marker seeded, otherwise the models ignore the
        # step-numbering format entirely. It is prepended to the recorded text so the
        # stored trace is exactly what the parser should see.
        prefill = PREFILL.get(args.prompt_version, "")
        payload = {"model": args.model, "prompt": prompt + prefill, "seed": seed,
                   "max_tokens": args.max_tokens, "temperature": TEMPERATURE,
                   "top_p": TOP_P, "top_k": TOP_K}
        t0 = time.time()
        resp = requests.post(url, json=payload, timeout=args.timeout)
        resp.raise_for_status()
        data = resp.json()
        text = prefill + data["choices"][0]["text"]
        thinking, final = split_think(text)
        return {
            "id": rec["id"], "dataset": args.dataset, "model": args.model, "seed": seed,
            "user_prompt": user_prompt, "response": text,
            "thinking": thinking, "final_answer": final,
            "gold": rec.get("gold"),
            "finish_reason": data["choices"][0].get("finish_reason"),
            "closed_think": "</think>" in text,
            "config": {"max_tokens": args.max_tokens, "temperature": TEMPERATURE,
                       "top_p": TOP_P, "top_k": TOP_K,
                       "prompt_version": args.prompt_version},
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
            except Exception as e:                     # keep the run alive; retry on resume
                print(f"  FAIL {rec['id']} seed={seed}: {type(e).__name__}: {e}",
                      flush=True)
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

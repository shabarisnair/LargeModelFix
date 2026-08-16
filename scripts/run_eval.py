"""Run the thought-repair experiments and write per-example + aggregate results.

Talks to two already-running vLLM servers (see serve_models.sh). Every parameter
is a CLI flag. Example:

  python run_eval.py \
      --datasets math500 aime2024 --strategies small large periodic_replace \
      --limit 5 --repair-intervals 256 512 --small-url http://localhost:8000 \
      --large-url http://localhost:8001

For periodic_* strategies the run is repeated once per --repair-intervals value;
other strategies ignore it. Results:
  results/<tag>/rows.jsonl   -- one line per (run, example)
  results/<tag>/summary.csv  -- accuracy / tokens / latency / cost per (run, dataset)
"""

from __future__ import annotations

# Point HF at the roomy disk before transformers is imported (via common).
import os
os.environ.setdefault("HF_HOME", "/hdd1/ssn899/hf_cache")

import argparse
import fcntl
import json
import time
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path

import pandas as pd

from common import ModelClient
from data_loaders import load_examples, SYSTEM_PROMPTS, DATASETS
from grading import grade
from strategies import GenConfig, STRATEGIES
from triggers import TRIGGERS
from interventions import INTERVENERS


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    # what to run
    p.add_argument("--datasets", nargs="+", default=["math500"],
                   choices=list(DATASETS))
    p.add_argument("--strategies", nargs="+", default=list(STRATEGIES),
                   choices=list(STRATEGIES))
    p.add_argument("--limit", type=int, default=5, help="examples per dataset (None=all)")
    p.add_argument("--seed", type=int, default=0)

    # models + servers
    p.add_argument("--small-model", default="Qwen/Qwen3-8B")
    p.add_argument("--large-model", default="Qwen/Qwen3-32B")
    p.add_argument("--small-url", default="http://localhost:8000")
    p.add_argument("--large-url", default="http://localhost:8001")

    # generation budget
    p.add_argument("--max-tokens", type=int, default=8192,
                   help="small-model reasoning+answer budget")
    p.add_argument("--repair-max-tokens", type=int, default=4096,
                   help="per large-model repair-call budget")

    # periodic intervention: WHEN (trigger) and HOW (intervener)
    p.add_argument("--repair-trigger", default="interval", choices=TRIGGERS,
                   help="when to intervene (periodic only)")
    p.add_argument("--repair-intervener", default="mentor", choices=INTERVENERS,
                   help="how to intervene (periodic only)")
    p.add_argument("--repair-intervals", nargs="+", type=int, default=[512],
                   help="X values to ablate for the interval trigger (periodic only)")
    p.add_argument("--max-repairs", type=int, default=16,
                   help="cap on target-model consultations per example")
    p.add_argument("--repair-thinking", action="store_true",
                   help="let the target model think before answering (default off)")

    # sampling overrides (None -> family default)
    p.add_argument("--temperature", type=float, default=None)
    p.add_argument("--top-p", type=float, default=None)
    p.add_argument("--top-k", type=int, default=None)

    # system prompt overrides
    p.add_argument("--system-math", default=None)
    p.add_argument("--system-mcq", default=None)

    # cost model ($ per 1M tokens); defaults are illustrative -- edit freely.
    p.add_argument("--price-small-in", type=float, default=0.05)
    p.add_argument("--price-small-out", type=float, default=0.20)
    p.add_argument("--price-large-in", type=float, default=0.20)
    p.add_argument("--price-large-out", type=float, default=0.80)

    # reuse a prior run's small-model traces (repair_once/or/orr) instead of re-running 8B
    p.add_argument("--small-traces", default=None,
                   help="path to a prior run's rows.jsonl (or its dir) whose 'small' "
                        "traces are reused for repair_once/or/orr; requires that run "
                        "used --save-traces and matching --datasets/--limit/--seed")

    # output
    p.add_argument("--out-dir", default="results")
    p.add_argument("--tag", default=None, help="run label (default: timestamp)")
    p.add_argument("--save-traces", action="store_true",
                   help="store full generation text in rows.jsonl")
    p.add_argument("--small-logprobs", type=int, default=0,
                   help="periodic only: capture top-k (<=20) logprobs of the 8B's tokens "
                        "(generated + prefill) to results/<tag>/logprobs/<example_id>.json")
    p.add_argument("--overwrite", action="store_true",
                   help="ignore any existing rows.jsonl for this tag and start fresh "
                        "(default: resume, skipping already-completed (run,dataset,example))")
    # parallel workers on the same tag: each worker takes a disjoint slice of units
    p.add_argument("--num-shards", type=int, default=1,
                   help="split the units across this many parallel workers (same tag/folder)")
    p.add_argument("--shard-index", type=int, default=0,
                   help="which shard this worker runs (0..num-shards-1); units are "
                        "assigned by global position so shards are disjoint")
    return p.parse_args()


def load_small_traces(path: str) -> dict:
    """Load {example_id: row} from a prior run's 'small' rows (needs final_text)."""
    p = Path(path)
    if p.is_dir():
        p = p / "rows.jsonl"
    if not p.exists():
        raise FileNotFoundError(f"--small-traces: {p} not found")
    store = {}
    for line in open(p):
        r = json.loads(line)
        if r.get("strategy") != "small":
            continue
        if "final_text" not in r:
            raise ValueError(f"{p}: 'small' rows lack 'final_text' -- re-run the source "
                             f"with --save-traces")
        store[r["example_id"]] = r
    if not store:
        raise ValueError(f"{p}: no rows with strategy=='small' found")
    return store


def make_config(args) -> GenConfig:
    system_prompts = dict(SYSTEM_PROMPTS)
    if args.system_math:
        system_prompts["math"] = args.system_math
    if args.system_mcq:
        system_prompts["mcq"] = args.system_mcq
    return GenConfig(
        max_tokens=args.max_tokens,
        trigger_name=args.repair_trigger,
        intervener_name=args.repair_intervener,
        max_repairs=args.max_repairs,
        repair_thinking=args.repair_thinking,
        repair_max_tokens=args.repair_max_tokens,
        temperature=args.temperature,
        top_p=args.top_p,
        top_k=args.top_k,
        seed=args.seed,
        small_logprobs=min(args.small_logprobs, 20),   # server --max-logprobs default is 20
        system_prompts=system_prompts,
    )


def cost_for(row: dict, args) -> dict:
    """Token-price cost using the KV-aware input (new_prefix = prefill cache misses).

    Input = new_prefix (tokens actually prefilled); output = gen_out. `*_raw_in`
    remains in the row as the pessimistic no-cache upper bound if you prefer it.
    """
    s_in, s_out = row["small_new_prefix"], row["small_gen_out"]
    l_in, l_out = row["large_new_prefix"], row["large_gen_out"]
    small = (s_in * args.price_small_in + s_out * args.price_small_out) / 1e6
    large = (l_in * args.price_large_in + l_out * args.price_large_out) / 1e6
    return {"cost_small": small, "cost_large": large, "cost_total": small + large}


def build_runs(args):
    """Expand strategies x (intervals for periodic) into concrete runs."""
    runs = []
    for strat in args.strategies:
        fn = STRATEGIES[strat]
        if strat == "periodic":
            for interval in args.repair_intervals:
                runs.append((f"{strat}@{interval}", strat, fn, interval))
        else:
            runs.append((strat, strat, fn, None))
    return runs


def main() -> None:
    args = parse_args()
    base_cfg = make_config(args)

    if args.small_traces:
        store = load_small_traces(args.small_traces)
        base_cfg = replace(base_cfg, small_traces=store)
        print(f"Reusing {len(store)} small-model traces from {args.small_traces}", flush=True)

    print(f"Loading tokenizers: {args.small_model} / {args.large_model}", flush=True)
    small = ModelClient(args.small_model, args.small_url)
    large = ModelClient(args.large_model, args.large_url)

    # load datasets (skip gated ones that fail, e.g. GPQA without a token)
    datasets = {}
    for name in args.datasets:
        try:
            datasets[name] = load_examples(name, limit=args.limit, seed=args.seed)
            print(f"  {name}: {len(datasets[name])} examples", flush=True)
        except Exception as e:
            print(f"  [skip] {name}: {e}", flush=True)

    tag = args.tag or datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = Path(args.out_dir) / tag
    out_dir.mkdir(parents=True, exist_ok=True)
    rows_path = out_dir / "rows.jsonl"
    with open(out_dir / "args.json", "w") as f:
        json.dump(vars(args), f, indent=2)

    # Resume: if rows.jsonl exists (and not --overwrite), keep finished units and skip them.
    # A unit is identified by (run, dataset, example_id).
    existing_by_key = {}
    if rows_path.exists() and not args.overwrite:
        for line in open(rows_path):
            r = json.loads(line)
            existing_by_key[(r["run"], r["dataset"], r["example_id"])] = r
        print(f"Resuming: {len(existing_by_key)} unit(s) already in {rows_path} "
              f"will be skipped (use --overwrite to redo).", flush=True)
    # Append (O_APPEND) whenever resuming OR sharding: with multiple shard workers on the
    # same file, append forces every write to EOF so they can't clobber each other's offsets.
    # Truncate ("w") only for a fresh single-worker run.
    file_mode = "a" if (args.num_shards > 1 or (existing_by_key and not args.overwrite)) else "w"

    if not (0 <= args.shard_index < args.num_shards):
        raise SystemExit(f"--shard-index must be in [0, {args.num_shards})")

    runs = build_runs(args)
    all_keys = [(rl, dn, ex.id)
                for rl, _, _, _ in runs
                for dn, exs in datasets.items() for ex in exs]
    # This worker owns a disjoint slice: global positions where k % num_shards == shard_index.
    shard_keys = {all_keys[i] for i in range(len(all_keys))
                  if i % args.num_shards == args.shard_index}
    total = len(shard_keys)                       # units this worker is responsible for
    n_to_run = sum(1 for k in shard_keys if k not in existing_by_key)
    shard_note = (f" [shard {args.shard_index}/{args.num_shards}]"
                  if args.num_shards > 1 else "")
    print(f"\nRunning{shard_note} {len(runs)} run(s) over {total} units "
          f"({total - n_to_run} already done, {n_to_run} to run)\n", flush=True)

    all_rows = list(existing_by_key.values())   # carry finished rows into the summary
    done = 0
    ran = 0
    t_start = time.perf_counter()
    with open(rows_path, file_mode) as rows_file:
        for run_label, strat, fn, interval in runs:
            cfg = base_cfg if interval is None else replace(base_cfg, repair_interval=interval)
            print(f"--- run '{run_label}' ({sum(len(e) for e in datasets.values())} examples) ---",
                  flush=True)
            run_correct = run_n = 0
            for dname, examples in datasets.items():
                for ex in examples:
                    key = (run_label, dname, ex.id)
                    if key not in shard_keys:                  # belongs to another worker
                        continue
                    done += 1
                    if key in existing_by_key:                 # already computed -> skip
                        run_n += 1
                        run_correct += int(bool(existing_by_key[key]["correct"]))
                        print(f"[{done}/{total} {100*done/total:4.0f}%] {run_label} {dname} "
                              f"{ex.id}: SKIP (already done) | run_acc={run_correct}/{run_n}",
                              flush=True)
                        continue

                    t0 = time.perf_counter()
                    result = fn(ex, small, large, cfg)
                    wall = time.perf_counter() - t0
                    correct = grade(ex.kind, ex.gold, result.final_text)

                    row = {
                        "run": run_label, "strategy": strat, "dataset": dname,
                        "repair_interval": interval,
                        "repair_thinking": args.repair_thinking,
                        "example_id": ex.id, "kind": ex.kind,
                        "correct": bool(correct), "gold": ex.gold,
                        "n_repairs": result.n_repairs,
                        "answer_from": result.answer_from,
                        "wall_time_s": round(wall, 3),   # end-to-end incl. Python glue
                        **result.small_usage.as_dict("small"),
                        **result.large_usage.as_dict("large"),
                    }
                    # method latency = sum of each model call's measured inference time
                    # (KV-caching already reflected in per-call time); excludes Python glue.
                    row["latency_s"] = round(row["small_seconds"] + row["large_seconds"], 3)
                    row.update(cost_for(row, args))
                    if args.save_traces:
                        row["final_text"] = result.final_text
                        row["interventions"] = result.interventions
                    # per-token 8B logprobs -> separate file (keeps rows.jsonl lean)
                    if result.logprobs is not None:
                        lp_dir = out_dir / "logprobs"
                        lp_dir.mkdir(exist_ok=True)
                        payload = {"example_id": ex.id, "run": run_label,
                                   "interventions": result.interventions, **result.logprobs}
                        with open(lp_dir / f"{ex.id}.json", "w") as lf:
                            json.dump(payload, lf)
                    # lock the shared file so parallel shard workers can't interleave
                    # large (trace-carrying) lines and corrupt rows.jsonl.
                    fcntl.flock(rows_file.fileno(), fcntl.LOCK_EX)
                    try:
                        rows_file.write(json.dumps(row) + "\n")
                        rows_file.flush()
                    finally:
                        fcntl.flock(rows_file.fileno(), fcntl.LOCK_UN)
                    all_rows.append(row)

                    ran += 1
                    run_n += 1
                    run_correct += int(bool(correct))
                    elapsed = time.perf_counter() - t_start
                    eta = elapsed / max(ran, 1) * (n_to_run - ran)   # ETA over units still to run
                    print(f"[{done}/{total} {100*done/total:4.0f}%] {run_label} {dname} "
                          f"{ex.id}: correct={int(bool(correct))} repairs={result.n_repairs} "
                          f"s_out={row['small_gen_out']} l_out={row['large_gen_out']} "
                          f"lat={row['latency_s']}s | run_acc={run_correct}/{run_n} "
                          f"| elapsed={elapsed/60:.1f}m eta={eta/60:.1f}m", flush=True)
                    # incrementally refresh summary.csv so results are current mid-run;
                    # never let a summary hiccup interrupt inference. Skipped when sharded
                    # (each worker holds only its own shard -> a shared summary would race).
                    if args.num_shards == 1:
                        try:
                            write_summary(all_rows, out_dir, quiet=True)
                        except Exception as e:
                            print(f"    (summary refresh skipped: {e})", flush=True)
            print(f"    -> run '{run_label}' accuracy: {run_correct}/{run_n} "
                  f"({100*run_correct/max(run_n,1):.1f}%)\n", flush=True)

    if args.num_shards == 1:
        write_summary(all_rows, out_dir)
        print(f"\nDone in {(time.perf_counter()-t_start)/60:.1f}m. "
              f"Rows -> {rows_path}\nSummary -> {out_dir/'summary.csv'}", flush=True)
    else:
        print(f"\nDone in {(time.perf_counter()-t_start)/60:.1f}m "
              f"[shard {args.shard_index}/{args.num_shards}]. Rows -> {rows_path}\n"
              f"After ALL shards finish, regenerate the combined summary by re-running the "
              f"same command WITHOUT --num-shards/--shard-index (it skips all done and writes "
              f"summary.csv).", flush=True)


def write_summary(rows: list[dict], out_dir: Path, quiet: bool = False) -> None:
    if not rows:
        if not quiet:
            print("No rows produced.")
        return
    df = pd.DataFrame(rows)
    agg = df.groupby(["run", "dataset"]).agg(
        n=("correct", "size"),
        accuracy=("correct", "mean"),
        small_gen_out=("small_gen_out", "mean"),
        large_gen_out=("large_gen_out", "mean"),
        small_new_prefix=("small_new_prefix", "mean"),   # KV-cache misses (billed input)
        large_new_prefix=("large_new_prefix", "mean"),
        n_repairs=("n_repairs", "mean"),
        latency_s=("latency_s", "mean"),                 # sum of model call latencies
        cost_total=("cost_total", "mean"),
    ).reset_index()
    agg["accuracy"] = (agg["accuracy"] * 100).round(1)
    for c in ["small_gen_out", "large_gen_out", "small_new_prefix", "large_new_prefix",
              "n_repairs", "latency_s"]:
        agg[c] = agg[c].round(1)
    agg["cost_total"] = agg["cost_total"].round(6)
    agg.to_csv(out_dir / "summary.csv", index=False)
    if not quiet:
        print("\n=== summary ===")
        print(agg.to_string(index=False))


if __name__ == "__main__":
    main()

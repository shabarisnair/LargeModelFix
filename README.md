# LargeModelFix — small-model thinking, periodically repaired by a large model

POC to test whether a small thinking LLM (Qwen3-8B) whose chain-of-thought is
periodically *repaired* by a large thinking LLM (Qwen3-32B) can approach the
large model's accuracy at lower cost/latency.

## Strategies compared (`--strategies`)
| name | what runs |
|------|-----------|
| `small` | Qwen3-8B thinking, single shot (baseline) |
| `large` | Qwen3-32B thinking, single shot (baseline) |
| `periodic` | the 8B thinks; a **trigger** pauses it and an **intervener** consults the 32B to repair (see below) |
| `repair_once` | 8B writes the trace; 32B **reviews it in a fresh turn** (per `--repair-thinking`) and answers |
| `or` | Offloaded Reasoning (Jindal et al.): 8B's reasoning injected inside the 32B's `<think>`, `</think>` **closed** → 32B answers directly, no refinement |
| `orr` | Offloaded Reasoning w/ Refinement: same, but `</think>` left **open** with a skeptical prefill → 32B briefly refines, then answers |

`repair_once`, `or`, `orr` all consume the 8B's completed trace. Differences: `repair_once`
puts the trace in a *user turn* with review instructions; `or`/`orr` prefill it *inside the
32B's own think block* (the faithful paper mechanism — `or`≈no refinement, `orr`≈bounded refinement).

### `periodic` = WHEN (trigger) × HOW (intervener) — two independent, pluggable parts
These are decoupled so either can be edited/extended alone:

- **WHEN** — [triggers.py](scripts/triggers.py), `--repair-trigger` (default `interval`):
  `interval` pauses the 8B every `X` generated tokens. `X` is `--repair-intervals`
  (ablatable, e.g. `128 256 512 1024`). Add a policy = new `Trigger` subclass.
- **HOW** — [interventions.py](scripts/interventions.py), `--repair-intervener` (default `mentor`):
  `mentor` sends the 8B's partial trace to the 32B, which must return either
  `<NO_EDIT>` (leave it alone → 8B keeps thinking) or a concise
  `<MENTOR_REPAIR>…</MENTOR_REPAIR>` note that is appended into the 8B's thinking so
  it self-corrects. The exact prompt is `MENTOR_PROMPT` in that file — edit it there.
  `--repair-thinking` toggles whether the 32B reasons before answering (default off,
  which keeps its output to a one-line `NO_EDIT`/repair and is far cheaper).
  Add a mechanism = new `Intervener` subclass.

`--max-repairs` caps 32B consultations per example. With `--save-traces`, each row's
`interventions` field logs every consultation (`at_tokens`, `action`, `text`).

## Metrics (per example in `rows.jsonl`, aggregated in `summary.csv`)
For **each** model separately:
- `*_gen_out` — generated (decode) tokens.
- `*_new_prefix` — input tokens that actually had to be **prefilled** (KV-cache
  **misses**), computed deterministically as the tokens beyond the longest common
  prefix with that model's previous **prompt + generation** (mirrors vLLM prefix
  reuse; the small model's own decoded tokens are cache hits on the next chunk).
- `*_cached_prefix` — input tokens served from the KV cache.
- `*_raw_in` — Σ prompt_tokens (no-cache pessimistic upper bound), kept for reference.
- `*_seconds` — summed measured inference latency for that model's calls.

Plus `accuracy`, `n_repairs`, and:
- **`latency_s`** — the method's latency = **sum of every model call's measured
  inference time** (small chunks + large consultations, in call order). This reflects
  KV caching (each call's server time already does) and **excludes** Python glue.
  `wall_time_s` (end-to-end incl. Python) is also logged for reference.
- **`cost_total`** — `$` from editable prices, computed on the **KV-aware** input
  (`new_prefix`) + `gen_out`. Prices: `--price-{small,large}-{in,out}` ($/1M tokens).
  vLLM must run with `--enable-prefix-caching` (serve_models.sh does) for the KV
  split to reflect reality; the API itself does not expose cached-token counts, so we
  compute the split ourselves. Accounting is per-example (cross-example cache reuse,
  e.g. the shared mentor template, is not credited).

## Environment
- Conda env: `/home/ssn899/envs/largemodelfix` (Python 3.11).
- **Pinned for this box's driver (570 / CUDA 12.8):** `vllm==0.11.0`,
  `torch==2.8.0+cu128`, `transformers==4.57.1`, and **flashinfer removed**
  (it needs a JIT `ninja` build). Newer vllm pulls a CUDA-13 torch that this
  driver rejects — don't upgrade blindly.
- Model weights cached on `/hdd1/ssn899/hf_cache` (`HF_HOME`); the env lives on
  `/home` (home quota is 100 GB, too small for the 32B weights).

## Run it

**1. Start the two vLLM servers** (8B → GPU 0 :8000, 32B → GPU 3 :8001):
```bash
bash scripts/serve_models.sh          # first run downloads ~80 GB to /hdd1
# override e.g.: SMALL_GPU=1 LARGE_GPU=2 SMALL_MODEL=... bash scripts/serve_models.sh
```
Logs: `results/serve_small.log`, `results/serve_large.log`. Stop: `bash scripts/stop_models.sh`.

**2. Run experiments** (from the `scripts/` dir so sibling imports resolve):
```bash
cd scripts
PY=/home/ssn899/envs/largemodelfix/bin/python
HF_HOME=/hdd1/ssn899/hf_cache $PY run_eval.py \
    --datasets math500 aime2024 gpqa \
    --strategies small large periodic repair_once \
    --repair-trigger interval --repair-intervener mentor \
    --repair-intervals 128 256 512 1024 \
    --limit 50 --out-dir ../results --tag full_run
```
Outputs: `results/<tag>/rows.jsonl` (per example), `results/<tag>/summary.csv`,
`results/<tag>/args.json`. Add `--save-traces` to store full generations.

Every parameter is a flag — see `python run_eval.py -h`. Key ones:
`--limit` (examples/dataset), `--max-tokens`, `--repair-max-tokens`,
`--max-repairs`, `--repair-thinking` (let the 32B think before repairing; default
off), `--temperature/--top-p/--top-k`, `--system-math/--system-mcq`,
`--small-model/--large-model/--small-url/--large-url`.

## Reusing an existing 8B trace (`--small-traces`)
`repair_once`, `or`, `orr` all need the 8B's completed trace. To avoid re-running the
8B, point at a prior run's rows (that used `--save-traces`):
```bash
$PY run_eval.py --strategies or orr repair_once --datasets math500 aime2024 \
    --limit 50 --small-traces /path/to/prior_run/rows.jsonl \
    --repair-max-tokens 4096 --out-dir ../results --tag offloaded --save-traces
```
It matches by `example_id`, so use the **same `--datasets/--limit/--seed`** as the source
run. The reused 8B tokens/latency are still counted toward each method's totals (fair
comparison). Any example missing from the file falls back to running the 8B. A path to the
run's directory also works (it looks for `rows.jsonl`).

## Resuming a run / skipping finished work
If `results/<tag>/rows.jsonl` already exists, a re-run **resumes by default**: it skips every
`(run, dataset, example_id)` already present and only computes the missing ones (appending to
the same file; skipped units still count in the summary). This makes it safe to grow a run —
e.g. add `gsm8k` to a tag that already has `math500`/`aime2024`, or raise `--limit` — without
recomputing. Pass `--overwrite` to ignore existing rows and start fresh. Resume assumes the
same config; if you changed params (e.g. `--max-tokens`), use `--overwrite` or a new `--tag`.

## Datasets
`math500` (open), `aime2024` (open), `gsm8k` (open, `openai/gsm8k` test = 1319),
`gpqa` (**gated** — `huggingface-cli login`
or export `HF_TOKEN` with access to `Idavidrein/gpqa`, else it's auto-skipped).

## Adding models later (e.g. DeepSeek-R1-Distill-Qwen)
Add one entry to `MODEL_REGISTRY` in `scripts/common.py` (match substring,
system-prompt support, chat-template kwargs, think tags). No other changes; the
DeepSeek-distill family is already registered.

## Files
```
scripts/common.py       model registry, tokenizer templating, vLLM client, token/time accounting
scripts/data_loaders.py MATH-500 / AIME-2024 / GPQA -> uniform Example
scripts/grading.py      boxed extraction + math-verify (math) / letter (mcq) grading
scripts/strategies.py   the 5 strategies + editable repair prompts
scripts/run_eval.py     CLI orchestration, metrics, cost, results
scripts/serve_models.sh launch the two vLLM servers   (stop_models.sh to stop)
```

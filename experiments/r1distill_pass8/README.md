# R1-Distill pass@1 x 8 seeds on GSM8K / WebInstruct / LiveCodeBench

## Results

pass@1 averaged over 8 seeds, +/- the standard deviation across those seeds.
100 queries per dataset, `max_tokens=45000`.

| model | GSM8K | WebInstruct | LiveCodeBench |
|---|---|---|---|
| R1-Distill-Qwen-32B  | **96.0% +/- 1.6** | **51.9% +/- 2.3** | **48.8% +/- 2.8** |
| R1-Distill-Qwen-1.5B | **82.5% +/- 2.3** | **28.1% +/- 2.8** | **16.4% +/- 1.8** |

Truncation at the 45k cap (a truncated sample never closes `</think>`, so it has no
answer section and scores 0):

| run | truncated | accuracy on completed samples | ceiling |
|---|---|---|---|
| 32B gsm8k | 0/800 | 96.0% | 100.0% |
| 32B webinstruct | 14/800 | 52.8% | 98.2% |
| 32B livecodebench | 38/800 | 51.2% | 95.2% |
| 1.5B gsm8k | 1/800 | 82.6% | 99.9% |
| 1.5B webinstruct | 20/800 | 28.8% | 97.5% |
| 1.5B livecodebench | **94/800** | 18.6% | 88.2% |

The 1.5B on LiveCodeBench is the one run where the cap materially bites: 11.8% of its
samples run out of budget mid-reasoning, capping its achievable score at 88.2%. Even so
16.4% is in line with the published ~16.9% for that model. Mean completion length was
16.6k tokens for the 1.5B on LCB vs 12.1k for the 32B -- the small model reasons longer
and scores less.

Raw traces, per-row verdicts and `results.json` are under
`/hdd1/ssn899/LargeModelFix/results/r1distill_pass8/`.


Measures pass@1 for **DeepSeek-R1-Distill-Qwen-32B** and **-1.5B** on 100 queries from each
of three datasets, sampling **8 responses per query** (8 fixed seeds) to average out
sampling stochasticity.

Sampling is DeepSeek's recommended setting: `temperature=0.6, top_p=0.95, top_k=20`,
`max_tokens=45000`. No system message (per DeepSeek guidance for the distill family) --
every instruction is folded into the user turn. The chat template already opens `<think>`,
so a response is `reasoning ... </think> final answer`; **only the text after `</think>`
is graded.**

The 45k generation budget requires `max_model_len=49152` on the server (45000 + the
longest prompt, 1436 tokens, + margin); the model's own limit is 131072.

Seeds are `[1000..1007]`, identical across every model x dataset combination.

## Trace reuse (never recompute an existing trace)

`generate.py` scans `/hdd1/ssn899/LargeModelFix/results` for any trace matching
`(model, dataset, query id, seed)` and reuses it instead of regenerating. A trace found
in a *different* file is copied into the current run's output, so the output is complete
either way. `--no-reuse` forces regeneration; `--results-root` changes the tree scanned.

Reuse requires the model and all sampling parameters to match exactly. `max_tokens` is
handled specially, because a cap only matters if it actually binds:

| existing trace | under a new `max_tokens` | reused? |
|---|---|---|
| same `max_tokens` | -- | yes |
| smaller cap, `finish_reason="stop"` | fits the new cap | yes -- the cap never bound, so it is the same sample |
| smaller cap, `finish_reason="length"` | was truncated | **no** -- regenerated |
| larger cap, trace longer than the new cap | would not have fit | **no** |

This is why raising 38k -> 45k reused 338 of the ~350 traces already on disk: they had
all stopped on their own well before 38k. Rows written before `config` was recorded are
treated as the original 38k run. `test_reuse.py` covers these cases.

Note that seeds give provenance, not bitwise replay: vLLM's numerics depend on batch
composition, so the same seed can yield a different trace under different concurrency.
Each trace is still a valid sample from the configured distribution.

## Layout

| path | what |
|---|---|
| `datasets_prep.py` | builds the three `*_first_100` subsets |
| `prompts.py` | per-dataset user prompt (step-separation + answer-format instructions) |
| `generate.py` | samples 8 responses/query from a vLLM endpoint; resumable |
| `grade.py` | numeric / MCQ / LiveCodeBench-executor grading -> per-seed accuracy |
| `summarize.py` | aggregates every summary into one table + `results.json` |
| `serve.sh` | launches a vLLM server |
| `run_model.sh` | generate+grade all three datasets for one model, in parallel |
| `test_grade.py`, `test_lcb_eval.py`, `test_reuse.py` | offline checks (no GPU) |
| `probe_webinstruct.py`, `probe_tiers.py` | one-off dataset censuses |

Outputs live in `/hdd1/ssn899/LargeModelFix/results/r1distill_pass8/`:
`generations/` (raw, one row per query x seed), `graded/` (per-row verdicts + summaries),
`logs/`, `serve/`, and the aggregated `results.json`.

Every generation row records the seed, the full `response`, the split-out `thinking` and
`final_answer`, `finish_reason`, `closed_think` and token counts -- so a run is
reproducible from its seed and re-gradeable without re-generating.

## The subsets

**`gsm8k_first_100`** -- first 100 rows of the test split. Gold is the value after `####`.

**`livecodebench_first_100`** -- the 100 **newest** problems in `release_v6` by
`contest_date`, spanning **2025-02-15 .. 2025-04-06**. release_v6 is cumulative and ordered
oldest-first, so a literal "first 100" would have returned 2023 problems that predate the
models' training cutoff. Composition: 61 atcoder (stdin) / 39 leetcode (functional),
46 hard / 31 medium / 23 easy.

**`webinstruct_first_100`** -- first 100 rows that are **deterministically checkable**,
which is much stricter than "the answer is a number". A census of all 1000 test rows
(`probe_tiers.py`):

| tier | n | description | kept |
|---|---|---|---|
| A | 26 | MCQ with lettered options in the question + single-letter gold | yes |
| B | 57 | bare integer gold (`'0'`, `'$95,344'`) | yes |
| C | 85 | bare decimal gold (`'29.65'`, `'-.30'`) | yes |
| D | 183 | number + trailing unit (`'65 m'`, `'21 x 10^-6 T'`) | **no** |
| E | 145 | prose / multi-part / no options (`'reinforcers'`) | **no** |

Tier D is excluded deliberately: the prompt asks for a bare number, so a correct answer
given in a different unit (6500 cm vs a gold of `65 m`) would score wrong for a unit
choice rather than a reasoning error. A+B+C = 168 available, of which the first 100 are
used -- 32 Integer, 53 Float, 15 MCQ. **No LLM judge is needed.**

## Grading

- **numeric** -- last `\boxed{}` in the answer section, parsed through LaTeX/unit stripping
  (`\times 10^{-5}`, `\frac{1}{2}`, `$`, commas). Integer golds must match exactly; decimal
  golds use a **1% relative tolerance**, because golds are rounded to 2-3 significant figures.
- **mcq** -- the option letter inside `\boxed{}`.
- **codegen** -- the official LiveCodeBench executor
  (`lcb_runner.evaluation.codegen_metrics`) against public+private test cases, with the
  official `extract_code` taking the last fenced block. The repo's own
  `load_code_generation_dataset` is unusable here (it needs `trust_remote_code`, removed in
  `datasets` 5.0.0), so problems are rebuilt from the local jsonl into
  `CodeGenerationProblem`.

A response that never closes `</think>` (i.e. it hit the 38k cap mid-reasoning) has an
empty answer section and scores 0. This is counted and reported as
`truncated_at_max_tokens` / `unclosed_think` rather than hidden.

**pass@1** is measured directly: each of the 8 samples is graded independently, each seed's
accuracy over the 100 queries is computed, and those 8 accuracies are averaged (`pass@1_mean`,
with `pass@1_std` across seeds).

## Verification done before the production run

- `test_grade.py` -- 25 assertions on boxed extraction, number parsing (units, LaTeX
  scientific notation, fractions), tolerance behaviour, and truncated-response handling.
- `test_lcb_eval.py` -- the LCB executor returns `[True, False]` for a known-correct and
  known-wrong solution, on both stdin and functional problem styles.
- A 3-problem easy-LiveCodeBench run scored 6/6 against the real executor, confirming the
  True path works on real data (both platforms).

## Reproducing

```bash
python datasets_prep.py
bash serve.sh 2,3 8002 deepseek-ai/DeepSeek-R1-Distill-Qwen-32B 49152 0.90
bash run_model.sh deepseek-ai/DeepSeek-R1-Distill-Qwen-32B http://127.0.0.1:8002 ds32b
bash run_model.sh deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B  http://127.0.0.1:8004 ds15b
python summarize.py
```

`serve.sh` takes a comma-separated GPU list; tensor-parallel size is inferred from it.
The last argument is `gpu_memory_utilization` as a fraction of **total** device memory --
these GPUs are shared with other users, so check `nvidia-smi` for free memory before
raising it. The 32B needs ~62 GB of weights, which does not leave workable KV-cache room
on a single GPU when another job is resident; it was run tensor-parallel across GPUs 2+3.

`generate.py` is resumable -- rows already in the output file are skipped, so an
interrupted run is restarted by re-issuing the same command.

# Reasoning DAGs (TRM method)

Dependency DAGs over the **thinking-block** steps of the v1 traces sampled in
`trace_samples/`, built with the reference implementation in
`experiments/post_trace_dag/TRM/dag_construction`.

## Method

For each step the judge LLM classifies how it attaches to earlier steps:

- **continue** — follows on from the current main path
- **backtrack** — restarts/revisits an earlier step ("Alternatively…", "Let me check again…")
- **merge** — stitches together two branches

`n=3` samples per step, majority-voted and validated (a vote naming an illegal
parent is discarded); linear `continue` chains are then collapsed into
super-nodes for the merged view.

**Judge model:** `Qwen/Qwen3-32B` served locally with vLLM, thinking disabled.
The upstream default is `deepseek-v3.2` via a hosted API; a local judge keeps
the traces on-machine and costs nothing per call. Qwen3's chat template enables
thinking by default, which would consume the 512-token budget before the
`<|action|>` line, so `build_reasoning_dags.py` supplies a custom `ChatClient`
(the extension point the upstream README documents) passing
`chat_template_kwargs={"enable_thinking": false}`.

## Aggregate structure

| dataset | model | traces | median steps | backtrack rate | median depth | median leaves | median super-nodes |
|---|---|---|---|---|---|---|---|
| gsm8k | 1.5B | 3 | 3 | 0% | 2 | 1 | 1 |
| gsm8k | 32B | 3 | 5 | 0% | 4 | 1 | 1 |
| livecodebench | 1.5B | 3 | 96 | 4% | 78 | 5 | 17 |
| livecodebench | 32B | 3 | 82 | 5% | 65 | 4 | 10 |
| webinstruct | 1.5B | 2 | 28 | 6% | 14 | 2 | 10 |
| webinstruct | 32B | 2 | 42 | 7% | 22 | 4 | 13 |

**backtrack rate** = share of non-root steps classified `backtrack`.
**leaves** = dangling branches never folded back in — abandoned lines of
reasoning. A perfectly linear trace has 1 leaf and depth = steps-1.

## Per query

| dataset | query | model | steps | cont | back | merge | depth | leaves | super-nodes | linearity |
|---|---|---|---|---|---|---|---|---|---|---|
| gsm8k | `gsm8k-2` | 1.5B | 3 | 2 | 0 | 0 | 2 | 1 | 1 | 1.00 |
| gsm8k | `gsm8k-2` | 32B | 3 | 2 | 0 | 0 | 2 | 1 | 1 | 1.00 |
| gsm8k | `gsm8k-54` | 1.5B | 126 | 65 | 45 | 15 | 13 | 28 | 80 | 0.10 |
| gsm8k | `gsm8k-54` | 32B | 5 | 4 | 0 | 0 | 4 | 1 | 1 | 1.00 |
| gsm8k | `gsm8k-87` | 1.5B | 3 | 2 | 0 | 0 | 2 | 1 | 1 | 1.00 |
| gsm8k | `gsm8k-87` | 32B | 8 | 7 | 0 | 0 | 7 | 1 | 1 | 1.00 |
| livecodebench | `lcb-abc394_a` | 1.5B | 61 | 49 | 11 | 0 | 42 | 12 | 17 | 0.70 |
| livecodebench | `lcb-abc394_a` | 32B | 43 | 40 | 1 | 1 | 30 | 1 | 4 | 0.71 |
| livecodebench | `lcb-abc396_b` | 1.5B | 202 | 189 | 8 | 4 | 152 | 5 | 21 | 0.76 |
| livecodebench | `lcb-abc396_b` | 32B | 82 | 76 | 4 | 1 | 65 | 4 | 10 | 0.80 |
| livecodebench | `lcb-abc398_c` | 1.5B | 96 | 91 | 3 | 1 | 78 | 4 | 8 | 0.82 |
| livecodebench | `lcb-abc398_c` | 32B | 168 | 155 | 9 | 3 | 89 | 6 | 20 | 0.53 |
| webinstruct | `webinstruct-1589899` | 1.5B | 7 | 6 | 0 | 0 | 6 | 1 | 1 | 1.00 |
| webinstruct | `webinstruct-1589899` | 32B | 5 | 4 | 0 | 0 | 4 | 1 | 1 | 1.00 |
| webinstruct | `webinstruct-73279` | 1.5B | 49 | 38 | 6 | 4 | 22 | 4 | 18 | 0.46 |
| webinstruct | `webinstruct-73279` | 32B | 80 | 63 | 11 | 5 | 39 | 6 | 25 | 0.49 |

**linearity** = max_depth / (steps-1); 1.00 is a straight chain, lower
means more branching and abandoned work.

Judge calls: 960. Steps where no valid vote survived (fell back
to `continue`): 0.


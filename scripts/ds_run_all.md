# DeepSeek baseline re-run @ 32768 max generation tokens

Why 32768: DeepSeek's official eval uses 32,768 max generation. At our previous 16,384
budget, 17-53% of AIME traces were truncated, and **every truncated trace scores 0%**
(no `</think>`, no `\boxed{}`). GPQA was largely unaffected (1-7%) and already reproduced
published numbers (32B GPQA 62.6% vs 62.1% published), but AIME was badly depressed
(32B AIME-24 66.7% vs 72.6% published).

## Servers (one model per GPU)
| model | GPU | port | ctx |
|---|---|---|---|
| DeepSeek-R1-Distill-Qwen-7B   | 0 | 8000 | 40960 |
| DeepSeek-R1-Distill-Qwen-32B  | 1 | 8001 | 73728 |
| DeepSeek-R1-Distill-Qwen-1.5B | 2 | 8002 | 40960 |

The 32B needs 73728 because the reuse strategies send the whole small trace as prompt
(up to ~33k tokens) *plus* up to 32768 generated tokens.

## Fairness constraint
At any moment, **each model serves exactly one run**. Three workers:

- `ds_w_small7b.sh`  -> 7B small baseline           (7B only)
- `ds_w_small15b.sh` -> 1.5B small baseline         (1.5B only)
- `ds_w_large.sh`    -> 32B large baseline, then the six reuse runs **sequentially**
                        (32B only; small traces reused, so it never touches :8000/:8002)

Phase 1 runs all three workers concurrently (three different models).
Phase 2 is the large worker alone, serializing the six reuse runs.

## Launch
```bash
cd /home/ssn899/Desktop/LargeModelFix
setsid nohup bash scripts/ds_w_small7b.sh  > results/w_small7b.log  2>&1 < /dev/null &
setsid nohup bash scripts/ds_w_small15b.sh > results/w_small15b.log 2>&1 < /dev/null &
setsid nohup bash scripts/ds_w_large.sh    > results/w_large.log    2>&1 < /dev/null &
```

## Output tags (all re-run at 32768; `_32k` suffix marks the budget)
| pair | tags |
|---|---|
| 7B/32B   | `ds7b_small_base_32k`, `ds7b_or_32k`, `ds7b_orr_32k`, `ds7b_repair_once_32k` |
| 1.5B/32B | `ds15b_small_base_32k`, `ds15b_or_32k`, `ds15b_orr_32k`, `ds15b_repair_once_32k` |
| shared   | `ds_large_base_32k` (32B baseline, same for both pairs) |

The old 16384-budget results are retained under their original names
(`ds_*`, `*_extended`) for comparison.

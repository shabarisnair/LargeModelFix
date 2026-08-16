# Prompt v2 test run

12 queries (the ones sampled in `trace_samples/`), both models, 8 seeds each
= 192 traces. Generated with `PROMPT_VERSION = v2`, which requires the section
after `</think>` to be *only* the final answer.

## Compliance: is the answer section exactly the final answer?

| dataset | model | prompt | traces | compliant | median extra chars |
|---|---|---|---|---|---|
| gsm8k | 32B | **v1** | 32 | 0/32 (0%) | 482 |
| gsm8k | 32B | **v2** | 32 | 16/32 (50%) | 38 |
| gsm8k | 1.5B | **v1** | 32 | 0/32 (0%) | 600 |
| gsm8k | 1.5B | **v2** | 32 | 0/32 (0%) | 611 |
| webinstruct | 32B | **v1** | 32 | 0/32 (0%) | 540 |
| webinstruct | 32B | **v2** | 32 | 5/32 (16%) | 361 |
| webinstruct | 1.5B | **v1** | 32 | 0/32 (0%) | 1058 |
| webinstruct | 1.5B | **v2** | 32 | 0/32 (0%) | 1060 |
| livecodebench | 32B | **v1** | 32 | 0/32 (0%) | 1534 |
| livecodebench | 32B | **v2** | 32 | 0/32 (0%) | 1465 |
| livecodebench | 1.5B | **v1** | 32 | 0/32 (0%) | 1590 |
| livecodebench | 1.5B | **v2** | 32 | 0/32 (0%) | 1575 |

## Accuracy on the same (query, seed) pairs

| dataset | model | v1 | v2 | n |
|---|---|---|---|---|
| gsm8k | 32B | 78% | 81% | 32 |
| gsm8k | 1.5B | 41% | 53% | 32 |
| webinstruct | 32B | 91% | 91% | 32 |
| webinstruct | 1.5B | 56% | 38% | 32 |
| livecodebench | 32B | 100% | 100% | 32 |
| livecodebench | 1.5B | 41% | 31% | 32 |

Per-query traces are in the dataset subfolders; each file shows the v2
reasoning steps and answer section, with the v1 answer section collapsed
underneath for contrast.

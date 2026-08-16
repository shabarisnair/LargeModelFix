"""Build TRM reasoning DAGs over the sampled v1 traces.

Uses the reference implementation in
experiments/post_trace_dag/TRM/dag_construction (`trm_dag`), which turns an ordered list
of reasoning steps into a DAG by asking a judge LLM, for each step, whether it
`continue`s the current main path, `backtrack`s to an earlier step, or `merge`s two
branches -- then majority-votes over n samples and collapses linear `continue` chains.

Input is `trace_samples/steps.jsonl`: steps come from the **thinking block only**
(everything before `</think>`), already split on the blank line the generation prompt
asked for.

    python build_reasoning_dags.py --base-url http://127.0.0.1:8010 --model Qwen/Qwen3-32B
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

from trm_dag import DagParams, OpenAIConfig, build_dag_batch
from trm_dag.client import Usage

HERE = Path(__file__).resolve().parent


@dataclass
class VLLMChatClient:
    """ChatClient for a local vLLM endpoint.

    Two judge modes:

    * `enable_thinking=False` -- for hybrid models (Qwen3). Their template turns thinking
      on by default, so a short-budget judge would reason instead of emitting the
      `<|action|>` line. vLLM takes `chat_template_kwargs` to switch it off, which the
      stock OpenAIChatClient cannot pass.
    * `enable_thinking=True` -- for reasoning judges (DeepSeek-R1-Distill). Their template
      opens `<think>` unconditionally and accepts no such kwarg, so nothing extra is sent.
      The reasoning is stripped before parsing by `trm_dag.components.strip_reasoning`.
    """

    max_retries: int = 3
    initial_delay: float = 1.0
    backoff: float = 2.0
    enable_thinking: bool = False

    def complete(self, prompt: str, config: OpenAIConfig, *, n: int) -> tuple[list[str], Usage]:
        from openai import OpenAI

        client = OpenAI(api_key=config.api_key, base_url=config.base_url,
                        timeout=config.timeout)
        delay = self.initial_delay
        last_exc: Exception | None = None
        for attempt in range(max(1, self.max_retries)):
            try:
                extra = ({} if self.enable_thinking else
                         {"extra_body": {"chat_template_kwargs":
                                         {"enable_thinking": False}}})
                resp = client.chat.completions.create(
                    model=config.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=config.temperature,
                    top_p=config.top_p,
                    max_tokens=config.max_tokens,
                    n=max(1, int(n)),
                    **extra,
                )
                outputs = [str(c.message.content) for c in resp.choices
                           if getattr(getattr(c, "message", None), "content", None)]
                u = resp.usage
                usage = {"prompt_tokens": int(getattr(u, "prompt_tokens", 0) or 0),
                         "completion_tokens": int(getattr(u, "completion_tokens", 0) or 0),
                         "total_tokens": int(getattr(u, "total_tokens", 0) or 0)}
                return outputs, usage
            except Exception as exc:
                last_exc = exc
                if attempt + 1 >= self.max_retries:
                    break
                time.sleep(delay)
                delay *= self.backoff
        raise RuntimeError(f"vLLM completion failed: {last_exc}") from last_exc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default=str(HERE / "trace_samples" / "steps.jsonl"))
    ap.add_argument("--outdir", default=str(HERE / "reasoning_dags"))
    ap.add_argument("--base-url", default="http://127.0.0.1:8010/v1")
    ap.add_argument("--model", default="Qwen/Qwen3-32B")
    ap.add_argument("--n", type=int, default=3, help="samples per step for majority vote")
    ap.add_argument("--temperature", type=float, default=0.3)
    ap.add_argument("--max-tokens", type=int, default=512)
    ap.add_argument("--judge-thinking", action="store_true",
                    help="judge is a reasoning model; let it think before answering")
    ap.add_argument("--num-threads", type=int, default=24, help="traces in parallel")
    ap.add_argument("--max-steps", type=int, default=None,
                    help="skip traces longer than this (cost control)")
    ap.add_argument("--only", default=None, help="comma-separated query ids")
    ap.add_argument("--no-resume", action="store_true")
    ap.add_argument("--timeout", type=float, default=300.0,
                    help="per-request client timeout; a wedged connection must fail fast "
                         "so the client retries instead of blocking a worker forever")
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.steps)]
    if args.only:
        want = set(args.only.split(","))
        rows = [r for r in rows if r["id"] in want]
    if args.max_steps:
        rows = [r for r in rows if r["n_steps"] <= args.max_steps]
    # Shortest first. The writer emits rows in *input* order, so a long trace at index 0
    # buffers every finished result behind it until it completes. When the pool has a
    # thread per trace they all start together regardless of order, so ordering by
    # ascending length costs nothing and lets finished DAGs land incrementally.
    rows.sort(key=lambda r: r["n_steps"])

    items = [{"prompt": "", "steps": r["steps"], "dataset": r["dataset"], "id": r["id"],
              "model": r["model"], "seed": r["seed"], "correct": r["correct"],
              "n_steps": r["n_steps"]} for r in rows]

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    out_path = outdir / "dags.jsonl"

    cfg = OpenAIConfig(api_key="EMPTY", base_url=args.base_url, model=args.model,
                       temperature=args.temperature, top_p=0.9,
                       max_tokens=args.max_tokens, n=args.n, timeout=args.timeout)
    params = DagParams(random_seed=0)      # deterministic tie-breaking

    print(f"{len(items)} traces, {sum(i['n_steps'] for i in items)} steps total "
          f"(longest {items[0]['n_steps']}), judge={args.model} n={args.n} "
          f"max_tokens={args.max_tokens} thinking={args.judge_thinking}", flush=True)
    t0 = time.time()
    out = build_dag_batch(items, openai_config=cfg, dag_params=params,
                          client=VLLMChatClient(enable_thinking=args.judge_thinking),
                          num_threads=args.num_threads,
                          output_path=str(out_path), resume=not args.no_resume)
    print(f"done in {(time.time()-t0)/60:.1f} min -> {out_path} ({len(out)} rows)")


if __name__ == "__main__":
    main()

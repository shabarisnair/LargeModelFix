"""AdaptiveStep building blocks (Stage 1).

Reusable, independently-testable pieces for the speculative-reasoning-repair method:
  * token_confidences  -> per-token confidence c_i = p(sampled token) via re-scoring
  * calibrate_tau      -> AdaptiveStep threshold tau = the p-th percentile of confidence
                          (default p=2%, i.e. the lowest-confidence ~2% of tokens break)

Confidence follows AdaptiveStep Eq.1: the probability the model assigned to the token
it actually produced. We recover it for an existing trace by a prompt_logprobs pass
(the actual token's logprob is always returned by vLLM, even outside the top-k).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Iterator, Optional

import requests

from common import ModelClient, has_think_close


# --------------------------------------------------------------------------------------
# Streaming generation with per-token confidence (AdaptiveStep Eq.1)
# --------------------------------------------------------------------------------------
def stream_tokens(client: ModelClient, prompt: str, max_tokens: int,
                  logprobs: int = 1, temperature: Optional[float] = None,
                  top_p: Optional[float] = None, top_k: Optional[int] = None,
                  seed: Optional[int] = None) -> Iterator[dict]:
    """Yield {token, logprob, conf, finish_reason} per generated token, as it arrives.

    conf = exp(logprob of the SAMPLED token) = AdaptiveStep model confidence.
    The caller may stop consuming at any time (closing the stream aborts generation),
    which is how the orchestrator truncates/overwrites the small model's output.
    """
    fam = client.family
    payload = {
        "model": client.model_id, "prompt": prompt, "max_tokens": max_tokens,
        "temperature": fam.temperature if temperature is None else temperature,
        "top_p": fam.top_p if top_p is None else top_p,
        "add_special_tokens": False, "stream": True, "logprobs": logprobs,
    }
    tk = fam.top_k if top_k is None else top_k
    if tk and tk > 0:
        payload["top_k"] = tk
    if seed is not None:
        payload["seed"] = seed

    with requests.post(f"{client.base_url}/v1/completions", json=payload,
                       stream=True, timeout=client.timeout) as r:
        r.raise_for_status()
        for raw in r.iter_lines():
            if not raw:
                continue
            line = raw.decode() if isinstance(raw, bytes) else raw
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                return
            ch = json.loads(data)["choices"][0]
            lp = ch.get("logprobs") or {}
            toks, tlps = lp.get("tokens") or [], lp.get("token_logprobs") or []
            tops = lp.get("top_logprobs") or []
            fr = ch.get("finish_reason")
            delta = ch.get("text", "")
            for i, t in enumerate(toks):
                l = tlps[i] if i < len(tlps) else None
                tk_ = tops[i] if i < len(tops) else None
                # `text` is vLLM's incrementally-decoded delta: it reconstructs multi-byte
                # UTF-8 correctly, whereas raw token pieces can be partial (mojibake).
                # Use it as the token's text whenever the chunk carries exactly one token.
                txt = delta if len(toks) == 1 else t
                yield {"token": t, "text": txt, "logprob": l,
                       "conf": math.exp(l) if l is not None else None,
                       "topk": tk_,
                       "entropy": entropy_from_topk(tk_) if tk_ else None,
                       "finish_reason": fr if i == len(toks) - 1 else None}


def entropy_from_topk(topk: Optional[dict]) -> float:
    """Entropy (nats) over the returned top-k logprobs, renormalized. Approximates the
    full-vocab entropy (bounded by ln(k)); the server caps k at --max-logprobs."""
    if not topk:
        return 0.0
    ps = [math.exp(l) for l in topk.values()]
    z = sum(ps) or 1.0
    return -sum((p / z) * math.log(p / z) for p in ps if p > 0)


# --------------------------------------------------------------------------------------
# Step-boundary detection (reused for: small-step detection, finding Y, stopping large gen)
# --------------------------------------------------------------------------------------
STEP_KEYWORDS = ("therefore", "so", "now", "case", "thus", "hence", "then",
                 "wait", "alternatively", "next", "finally", "however")


class StepBoundaryDetector:
    """Marks step ENDS: a low-confidence token (c < tau) snapped RIGHT to the next natural
    boundary (never mid-word/expression). Natural boundary = newline, sentence punctuation
    (. ; ? !), an '=' completion, or a step keyword -- each at a word boundary.

    Operates on (tokens, confidences); tokens are the raw tokenizer pieces (may carry a
    leading space). Returns a sorted list of token indices where reasoning steps end.
    """

    def __init__(self, tau: float, keywords=STEP_KEYWORDS):
        self.tau = tau
        self.keywords = tuple(keywords)

    def _natural_end(self, tokens: list[str], j: int) -> bool:
        t = tokens[j]
        if "\n" in t:
            return True
        s = t.rstrip()
        if s and s[-1] in ".;?!=":
            nxt = tokens[j + 1] if j + 1 < len(tokens) else ""
            # word complete: end of text, or next piece starts with space/newline/non-alnum
            return nxt == "" or (not nxt[:1].isalnum())
        # step keyword starting a new clause -> this token ends the previous step
        w = t.strip().lower()
        if w in self.keywords and (t[:1] == " " or j == 0):
            return True
        return False

    def snap_forward(self, tokens: list[str], start: int, max_span: int = 40) -> Optional[int]:
        """First natural-boundary token index at/after `start` (within max_span). None if none."""
        for j in range(start, min(len(tokens), start + max_span)):
            if self._natural_end(tokens, j):
                return j
        return None

    def boundaries(self, tokens: list[str], confs: list[float]) -> list[int]:
        """Step-end token indices: each low-confidence trigger snapped to the next boundary."""
        ends: list[int] = []
        for i, c in enumerate(confs):
            if c < self.tau:
                j = self.snap_forward(tokens, i)
                if j is not None and (not ends or ends[-1] != j):
                    ends.append(j)
        return sorted(set(ends))

    def last_boundary_before(self, tokens: list[str], confs: list[float],
                             x: int) -> Optional[int]:
        """Y: the nearest step-end strictly to the left of token index x (or None)."""
        b = [e for e in self.boundaries(tokens, confs) if e < x]
        return b[-1] if b else None


# --------------------------------------------------------------------------------------
# Critic: the LARGE model inspects the small model's trace.
#   1) prefill-score the trace  -> per-token entropy + NLL (the large model's view)
#   2) earliest token with entropy>theta_H OR nll>theta_NLL  -> X  (first "dislike")
#   3) nearest step boundary strictly left of X               -> Y
#   4) prefill up to Y, generate one replacement step (capped) -> the repair
# Returns None (no intervention) if no X or no Y is found.
# --------------------------------------------------------------------------------------
def _entropy_nll_from_prompt_logprobs(entry: dict, actual_id: int) -> tuple[float, float]:
    """(top-k entropy in nats, NLL of the actual token) at one prefill position."""
    lps = [v["logprob"] for v in entry.values()]
    ps = [math.exp(l) for l in lps]
    z = sum(ps) or 1.0
    ent = -sum((p / z) * math.log(p / z) for p in ps if p > 0)
    a = entry.get(str(actual_id))
    nll = -a["logprob"] if a else float("inf")
    return ent, nll


@dataclass
class CriticResult:
    intervened: bool
    x_tok: Optional[int] = None          # first disliked token (index into trace tokens)
    y_tok: Optional[int] = None          # step boundary chosen as the rewrite point
    y_fallback: bool = False             # True if no Y found -> rewound to the first token
    replacement: str = ""                # text the large model generated from Y
    reason: str = ""                     # why we did/didn't intervene
    large_gen_tokens: int = 0
    score_seconds: float = 0.0
    gen_seconds: float = 0.0
    scored_tokens: int = 0
    # entropy gate (all as seen BY THE LARGE MODEL)
    repair_entropy: Optional[float] = None    # mean entropy of the large model's repair
    small_entropy: Optional[float] = None     # mean entropy over the small model's tokens > Y
    gate_passed: Optional[bool] = None


class Critic:
    """Large-model critic. `detector` supplies the SAME boundary rule used by the small model.

    gate_rule decides whether a generated repair is actually applied, comparing (both
    measured by the LARGE model) the mean entropy of its own repair tokens vs the mean
    entropy over the small model's tokens after Y:
      'large_lower'  -> apply when repair_entropy <  small_entropy  (default: the large
                        model is MORE confident in its own rewrite than in the small
                        model's text)
      'large_higher' -> the inverse (kept for ablation)
      'off'          -> always apply
    """

    def __init__(self, large: ModelClient, detector: StepBoundaryDetector,
                 theta_entropy: float = 1.53, theta_nll: float = 3.81,
                 max_gen_tokens: int = 100, topk: int = 20,
                 max_score_tokens: int = 4000, x_min_index: int = 0,
                 gate_rule: str = "large_lower"):
        self.large = large
        self.detector = detector
        self.theta_entropy = theta_entropy
        self.theta_nll = theta_nll
        self.max_gen_tokens = max_gen_tokens
        self.topk = topk
        self.max_score_tokens = max_score_tokens
        self.x_min_index = x_min_index
        self.gate_rule = gate_rule

    # -- step 1+2: score the trace, find the first token the large model dislikes -------
    def find_x(self, base_prompt: str, trace: str, min_index: int = 0
               ) -> tuple[Optional[int], list[dict], float]:
        """min_index: only consider X at/after this trace-token index. Used to skip the
        region before the first step boundary, where no rewind point Y could exist."""
        import time
        ids_trace = self.large.tokenizer.encode(trace, add_special_tokens=False)
        ids_trace = ids_trace[: self.max_score_tokens]
        trace = self.large.tokenizer.decode(ids_trace)
        full = base_prompt + trace
        ids_full = self.large.tokenizer.encode(full, add_special_tokens=False)
        base_len = len(self.large.tokenizer.encode(base_prompt, add_special_tokens=False))

        t0 = time.perf_counter()
        res = self.large.complete(full, max_tokens=1, temperature=0,
                                  prompt_logprobs=self.topk)
        dt = time.perf_counter() - t0
        pl = res.prompt_logprobs or []

        per_token, x = [], None
        for i in range(base_len, min(len(pl), len(ids_full))):
            entry = pl[i]
            if not entry:
                continue
            ent, nll = _entropy_nll_from_prompt_logprobs(entry, ids_full[i])
            j = i - base_len                      # index within the trace tokens
            per_token.append({"i": j, "entropy": ent, "nll": nll})
            if x is None and j >= min_index and \
                    (ent > self.theta_entropy or nll > self.theta_nll):
                x = j
        return x, per_token, dt

    # -- step 3+4: pick Y, regenerate one step from there -------------------------------
    def run(self, base_prompt: str, trace_tokens: list[str], trace_confs: list[float],
            min_y: int = 0) -> CriticResult:
        """min_y: earliest token index we may rewind to (end of the previous repair)."""
        import time
        trace = "".join(trace_tokens)

        # min_y is the earliest token we're allowed to rewind to. It starts at 0 and, after
        # a repair is applied, becomes the END of that repair -- so a later intervention can
        # never rewind into (and thus rewrite) a previous repair.
        min_y = max(min_y, self.x_min_index)

        # (1)+(2) score the trace and find X (only in territory we may rewind into).
        # No X -> no intervention.
        x, per_token, score_dt = self.find_x(base_prompt, trace, min_index=min_y)
        if x is None:
            return CriticResult(False, reason="no disliked token (X) found",
                                score_seconds=score_dt, scored_tokens=len(per_token))

        # (3) Y = nearest boundary left of X but at/after min_y. If none, rewind from the
        # earliest allowed point (the first generated token, or the end of the last repair).
        cands = [b for b in self.detector.boundaries(trace_tokens, trace_confs)
                 if min_y <= b < x]
        y_fallback = not cands
        y = cands[-1] if cands else min_y

        # (4) regenerate one step from Y, stopping at the large model's OWN step boundary.
        prefix = "".join(trace_tokens[: y + 1])
        toks, confs, ents = [], [], []
        t0 = time.perf_counter()
        for t in stream_tokens(self.large, base_prompt + prefix,
                               max_tokens=self.max_gen_tokens, logprobs=self.topk):
            toks.append(t["text"])
            confs.append(t["conf"] if t["conf"] is not None else 1.0)
            ents.append(t["entropy"] if t["entropy"] is not None else 0.0)
            # boundary rule: a low-confidence trigger has fired AND we're at a natural end
            if any(c < self.detector.tau for c in confs) and \
                    self.detector._natural_end(toks, len(toks) - 1):
                break
        gen_dt = time.perf_counter() - t0
        replacement = "".join(toks)

        # (5) entropy gate: large model's own repair vs the small model's tokens after Y,
        #     both measured by the large model.
        rep_ent = (sum(ents) / len(ents)) if ents else None
        after = [p["entropy"] for p in per_token if p["i"] > y]
        small_ent = (sum(after) / len(after)) if after else None
        if self.gate_rule == "off" or rep_ent is None or small_ent is None:
            passed = True
        elif self.gate_rule == "large_lower":
            passed = rep_ent < small_ent
        else:                                        # 'large_higher' (as specified)
            passed = rep_ent > small_ent

        base = dict(x_tok=x, y_tok=y, y_fallback=y_fallback, replacement=replacement,
                    large_gen_tokens=len(toks), score_seconds=score_dt, gen_seconds=gen_dt,
                    scored_tokens=len(per_token), repair_entropy=rep_ent,
                    small_entropy=small_ent, gate_passed=passed)
        if not passed:
            return CriticResult(False, reason=f"entropy gate rejected "
                                f"(repair {rep_ent:.3f} vs small {small_ent:.3f}, "
                                f"rule={self.gate_rule})", **base)
        return CriticResult(True, reason="ok", **base)


# --------------------------------------------------------------------------------------
# Orchestrator (Stage 1: synchronous -- produces the SAME final trace as the parallel
# design, since an intervention always truncates to Y and appends the repair regardless
# of how far the small model ran past the boundary).
# --------------------------------------------------------------------------------------
@dataclass
class AdaptiveConfig:
    tau: float = 0.27691               # AdaptiveStep step threshold (2nd pct, 8B/AIME)
    theta_entropy: float = 1.53        # dissatisfaction: entropy (P99, nats)
    theta_nll: float = 3.81            # dissatisfaction: NLL (P99, nats)
    max_gen_tokens: int = 100          # cap on one large-model repair step
    max_tokens: int = 16384            # small-model total budget
    chunk_tokens: int = 400            # how far the small model runs between critic calls
    max_interventions: int = 8         # safety cap per example
    topk: int = 20                     # logprobs breadth (server --max-logprobs)
    max_score_tokens: int = 4000       # cap on the critic's prefill scoring
    gate_rule: str = "large_lower"     # entropy gate direction
    seed: Optional[int] = None


def run_adaptive(example_prompt: str, small: ModelClient, large: ModelClient,
                 cfg: AdaptiveConfig) -> dict:
    """Small model generates; at each step boundary the large model may rewind to Y and
    rewrite one step. Returns the final text plus a rich event log."""
    import time
    det = StepBoundaryDetector(cfg.tau)
    critic = Critic(large, det, theta_entropy=cfg.theta_entropy, theta_nll=cfg.theta_nll,
                    max_gen_tokens=cfg.max_gen_tokens, topk=cfg.topk,
                    max_score_tokens=cfg.max_score_tokens, gate_rule=cfg.gate_rule)

    toks: list[str] = []       # the evolving trace (small tokens + applied repairs)
    confs: list[float] = []
    ents: list[float] = []
    min_y = 0                  # never rewind before the end of the last applied repair
    events: list[dict] = []
    small_s = large_s = 0.0
    small_gen = large_gen = 0
    t_start = time.perf_counter()
    finished = False

    while len(toks) < cfg.max_tokens and not finished:
        # -- small model runs forward one chunk -------------------------------------
        t0 = time.perf_counter()
        n0 = len(toks)
        for t in stream_tokens(small, example_prompt + "".join(toks),
                               max_tokens=min(cfg.chunk_tokens, cfg.max_tokens - len(toks)),
                               logprobs=cfg.topk, seed=cfg.seed):
            toks.append(t["text"])
            confs.append(t["conf"] if t["conf"] is not None else 1.0)
            ents.append(t["entropy"] if t["entropy"] is not None else 0.0)
            if t["finish_reason"] == "stop":
                finished = True
        small_s += time.perf_counter() - t0
        small_gen += len(toks) - n0
        if finished or has_think_close("".join(toks)) or len(toks) >= cfg.max_tokens:
            break                      # never repair the answer phase
        if len([e for e in events if e.get("applied")]) >= cfg.max_interventions:
            continue

        # -- large model critiques the trace so far ---------------------------------
        r = critic.run(example_prompt, toks, confs, min_y=min_y)
        large_s += r.score_seconds + r.gen_seconds
        large_gen += r.large_gen_tokens
        ev = {"at_tokens": len(toks), "x": r.x_tok, "y": r.y_tok,
              "y_fallback": r.y_fallback, "applied": r.intervened, "reason": r.reason,
              "repair": r.replacement, "repair_entropy": r.repair_entropy,
              "small_entropy": r.small_entropy, "gate_passed": r.gate_passed,
              "large_gen_tokens": r.large_gen_tokens,
              "score_s": round(r.score_seconds, 3), "gen_s": round(r.gen_seconds, 3)}
        events.append(ev)

        if r.intervened:
            # overwrite everything after Y with the large model's step, then continue.
            rep_toks = [t["text"] for t in
                        _retokenize_stream(large, r.replacement)] or [r.replacement]
            toks = toks[: r.y_tok + 1] + rep_toks
            confs = confs[: r.y_tok + 1] + [1.0] * len(rep_toks)
            ents = ents[: r.y_tok + 1] + [0.0] * len(rep_toks)
            min_y = len(toks) - 1          # next Y must be at/after the end of this repair
            ev["new_min_y"] = min_y
        elif r.x_tok is not None:
            # We looked at this spot and decided against repairing it (gate rejected, or a
            # repair we won't apply). Don't re-litigate the same X/Y on every later call --
            # advance past X so the next critique looks at fresh territory.
            min_y = max(min_y, r.x_tok + 1)     # +1: move PAST X, else we refind the same X
            ev["new_min_y"] = min_y

    text = "".join(toks)
    return {
        "final_text": text, "events": events,
        "small_gen_tokens": small_gen, "large_gen_tokens": large_gen,
        "small_seconds": round(small_s, 3), "large_seconds": round(large_s, 3),
        "latency_s": round(small_s + large_s, 3),
        "wall_s": round(time.perf_counter() - t_start, 3),
        "n_interventions": sum(1 for e in events if e["applied"]),
        "n_critic_calls": len(events),
        "token_conf": confs, "token_entropy": ents,
    }


def _retokenize_stream(client: ModelClient, text: str) -> list[dict]:
    """Split `text` into the client's tokens (as {'text': piece}) for trace bookkeeping."""
    ids = client.tokenizer.encode(text, add_special_tokens=False)
    return [{"text": client.tokenizer.decode([i])} for i in ids]


def token_confidences(client: ModelClient, base_prompt: str, response: str,
                      logprobs_k: int = 1, max_response_tokens: int = 1000) -> list[float]:
    """Confidence c_i = p(response token i) for each token of `response`, given base_prompt.

    Re-scores base_prompt+response with prompt_logprobs and reads the actual token's
    probability at each response position. Only the first `max_response_tokens` response
    tokens are scored (prompt_logprobs materializes full-vocab logits per position, which
    OOMs on long prompts under high gpu-mem-util).
    """
    resp_ids = client.tokenizer.encode(response, add_special_tokens=False)[:max_response_tokens]
    response = client.tokenizer.decode(resp_ids)
    full = base_prompt + response
    ids = client.tokenizer.encode(full, add_special_tokens=False)
    base_len = len(client.tokenizer.encode(base_prompt, add_special_tokens=False))
    res = client.complete(full, max_tokens=1, temperature=0, prompt_logprobs=logprobs_k)
    pl = res.prompt_logprobs or []
    confs = []
    for i in range(base_len, min(len(pl), len(ids))):
        entry = pl[i]
        if not entry:
            continue
        e = entry.get(str(ids[i]))            # actual token's logprob (vLLM always includes it)
        if e is not None:
            confs.append(math.exp(e["logprob"]))
    return confs


def calibrate_tau_streaming(client: ModelClient, prompts: list[str], max_tokens: int = 1500,
                            percentile: float = 2.0, seed: Optional[int] = None,
                            think_close: str = "</think>") -> tuple[float, list[float]]:
    """AdaptiveStep-faithful calibration: pool confidences collected DURING sampling.

    This is what the paper does ("generate N responses with temperature-based random
    sampling ... use the probability of the sampled token"). It avoids the re-tokenization
    artifacts of scoring a joined string, which inject spurious near-zero probabilities.
    """
    import numpy as np
    pooled: list[float] = []
    for p in prompts:
        text = ""
        for t in stream_tokens(client, p, max_tokens=max_tokens, logprobs=1, seed=seed):
            if t["conf"] is None:
                continue
            pooled.append(t["conf"])
            text += t["token"]
            if think_close in text:        # stay inside the reasoning block
                break
    tau = float(np.percentile(pooled, percentile))
    return tau, pooled


def calibrate_tau(client: ModelClient, base_prompts: list[str], responses: list[str],
                  percentile: float = 2.0, think_only: bool = True,
                  think_close: str = "</think>") -> tuple[float, list[float]]:
    """Pool per-token confidences and return (tau, all_confidences).

    tau is the `percentile`-th percentile: ~`percentile`% of tokens fall below it and
    become step-breaking points. If think_only, only score tokens inside the <think> block.
    """
    import numpy as np
    pooled: list[float] = []
    for bp, resp in zip(base_prompts, responses):
        if think_only and think_close in resp:
            resp = resp.split(think_close)[0]      # reasoning only
        pooled.extend(token_confidences(client, bp, resp))
    tau = float(np.percentile(pooled, percentile))
    return tau, pooled


if __name__ == "__main__":
    # Calibrate tau for the 8B over AIME traces in small_base_extended.
    import argparse, json, os
    os.environ.setdefault("HF_HOME", "/hdd1/ssn899/hf_cache")
    from data_loaders import load_examples, SYSTEM_PROMPTS

    ap = argparse.ArgumentParser()
    ap.add_argument("--small-model", default="Qwen/Qwen3-8B")
    ap.add_argument("--small-url", default="http://localhost:8000")
    ap.add_argument("--traces", default="/home/ssn899/Desktop/LargeModelFix/results/small_base_extended")
    ap.add_argument("--dataset", default="aime2024")
    ap.add_argument("--n", type=int, default=8, help="how many problems to calibrate on")
    ap.add_argument("--percentile", type=float, default=2.0)
    ap.add_argument("--mode", default="stream", choices=["stream", "rescore"],
                    help="stream = AdaptiveStep-faithful (confidences during sampling)")
    ap.add_argument("--max-tokens", type=int, default=1500)
    args = ap.parse_args()

    client = ModelClient(args.small_model, args.small_url)
    examples = load_examples(args.dataset, limit=100000)[:args.n]
    prompts = [client.build_prompt(e.user_prompt, system=SYSTEM_PROMPTS[e.kind])
               for e in examples]

    if args.mode == "stream":
        tau, pooled = calibrate_tau_streaming(client, prompts, max_tokens=args.max_tokens,
                                              percentile=args.percentile)
    else:
        rows = {r["example_id"]: r for r in
                (json.loads(l) for l in open(f"{args.traces}/rows.jsonl"))
                if r["dataset"] == args.dataset}
        resps = [rows[e.id]["final_text"] for e in examples]
        tau, pooled = calibrate_tau(client, prompts, resps, percentile=args.percentile)
    import numpy as np
    p = np.percentile(pooled, [0.5, 1, 2, 5, 10])
    print(f"calibrated on {len(prompts)} {args.dataset} problems ({args.mode}), {len(pooled)} thinking tokens")
    print(f"confidence percentiles: 0.5%={p[0]:.4f} 1%={p[1]:.4f} 2%={p[2]:.4f} "
          f"5%={p[3]:.4f} 10%={p[4]:.4f}")
    print(f"\n==> tau (@{args.percentile}%) = {tau:.5f}   "
          f"({sum(c < tau for c in pooled)}/{len(pooled)} tokens below = "
          f"{sum(c < tau for c in pooled)/len(pooled)*100:.1f}%)")

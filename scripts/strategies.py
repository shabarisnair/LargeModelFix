"""The generation strategies being compared.

Every strategy has the same signature:

    fn(example, small, large, cfg) -> GenResult

The interesting one is `periodic`, which pauses the small model (WHEN = a Trigger,
triggers.py) and consults the large model (HOW = an Intervener, interventions.py).
Those two concerns are fully decoupled: swapping the trigger or the intervener is a
one-line change and needs no edit here.

Token/latency accounting lives in the Usage objects; grading happens later in
run_eval on GenResult.final_text.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from common import (ModelClient, Usage, has_think_close, split_think,
                    usage_from_dict, gen_logprobs_to_list)
from data_loaders import Example, SYSTEM_PROMPTS
from triggers import make_trigger
from interventions import make_intervener


# --------------------------------------------------------------------------------------
# Config + result
# --------------------------------------------------------------------------------------
@dataclass
class GenConfig:
    # small-model reasoning+answer budget
    max_tokens: int = 8192

    # WHEN to intervene (periodic strategy)
    trigger_name: str = "interval"
    repair_interval: int = 512          # X: small-model tokens between interventions
    max_repairs: int = 16               # cap on target-model consultations per example

    # HOW to intervene (periodic strategy)
    intervener_name: str = "mentor"
    repair_thinking: bool = False       # does the target model think before answering?
    repair_max_tokens: int = 4096       # generation budget per target-model call

    # sampling overrides (None -> family default from common.py)
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    seed: int | None = None

    # optional {example_id: saved_row} to reuse the small model's trace (repair_once/or/orr)
    small_traces: dict | None = None

    # >0 => capture top-k logprobs of the small model's tokens (periodic only), k<=20
    small_logprobs: int = 0

    # answering system prompts by kind (override defaults from data_loaders.py)
    system_prompts: dict = field(default_factory=lambda: dict(SYSTEM_PROMPTS))

    def system_for(self, kind: str) -> str:
        return self.system_prompts.get(kind, SYSTEM_PROMPTS[kind])


@dataclass
class GenResult:
    final_text: str                     # graded text (thinking + answer)
    small_usage: Usage = field(default_factory=Usage)
    large_usage: Usage = field(default_factory=Usage)
    n_repairs: int = 0                  # interventions that actually edited the trace
    answer_from: str = "small"          # which model produced the graded answer
    interventions: list = field(default_factory=list)   # per-consultation {action,text,raw}
    logprobs: dict | None = None        # small-model token logprobs (periodic + --small-logprobs)


def _sample_kwargs(cfg: GenConfig) -> dict:
    return {"temperature": cfg.temperature, "top_p": cfg.top_p,
            "top_k": cfg.top_k, "seed": cfg.seed}


def _append_note(thought: str, note: str) -> str:
    """Append a mentor note to the trace with a clean sentence boundary."""
    note = note.strip()
    if note and note[-1] not in ".!?":
        note += "."
    sep = "" if (not thought or thought[-1].isspace()) else " "
    return f"{thought}{sep}{note} "


# --------------------------------------------------------------------------------------
# Baselines
# --------------------------------------------------------------------------------------
def _single(model: ModelClient, example: Example, cfg: GenConfig, who: str) -> GenResult:
    prompt = model.build_prompt(example.user_prompt, system=cfg.system_for(example.kind))
    res = model.complete(prompt, max_tokens=cfg.max_tokens, **_sample_kwargs(cfg))
    result = GenResult(final_text=res.text, answer_from=who)
    usage = result.small_usage if who == "small" else result.large_usage
    usage.add(res.prompt_tokens, res.completion_tokens, res.seconds, res.prompt_ids, res.gen_ids)
    return result


def small_only(example, small, large, cfg) -> GenResult:
    return _single(small, example, cfg, who="small")


def large_only(example, small, large, cfg) -> GenResult:
    return _single(large, example, cfg, who="large")


# --------------------------------------------------------------------------------------
# Periodic intervention (trigger + intervener)
# --------------------------------------------------------------------------------------
def periodic(example, small, large, cfg) -> GenResult:
    result = GenResult(final_text="", answer_from="small")
    trigger = make_trigger(cfg.trigger_name, cfg)
    intervener = make_intervener(cfg.intervener_name)

    system = cfg.system_for(example.kind)
    base_prompt = small.build_prompt(example.user_prompt, system=system)

    thought = ""            # accumulated small-model generation (reasoning, then answer)
    gen_tokens = 0          # small-model tokens generated so far
    consultations = 0       # target-model calls (edit or not) -> cost driver
    lp_kw = {"logprobs": cfg.small_logprobs} if cfg.small_logprobs else {}
    gen_lp = []             # per generated-token top-k logprobs (in order), if capturing

    while gen_tokens < cfg.max_tokens:
        step = trigger.step_max_tokens(cfg.max_tokens - gen_tokens)
        res = small.complete(base_prompt + thought, max_tokens=step,
                             stop=trigger.stop(), **_sample_kwargs(cfg), **lp_kw)
        result.small_usage.add(res.prompt_tokens, res.completion_tokens, res.seconds, res.prompt_ids, res.gen_ids)
        thought += res.text
        gen_tokens += res.completion_tokens
        if lp_kw:
            gen_lp.extend(gen_logprobs_to_list(res.gen_logprobs))

        if res.finished:                          # small emitted EOS -> answer done
            break
        if has_think_close(thought):
            # Reasoning phase is over (</think> emitted): NEVER repair the final answer.
            # Finish it in one un-chunked call and stop -- no more consultations.
            remaining = cfg.max_tokens - gen_tokens
            if remaining > 0:
                res = small.complete(base_prompt + thought, max_tokens=remaining,
                                     **_sample_kwargs(cfg), **lp_kw)
                result.small_usage.add(res.prompt_tokens, res.completion_tokens,
                                       res.seconds, res.prompt_ids, res.gen_ids)
                thought += res.text
                if lp_kw:
                    gen_lp.extend(gen_logprobs_to_list(res.gen_logprobs))
            break
        if consultations >= cfg.max_repairs:      # stop consulting, keep generating
            continue
        if not trigger.should_intervene(res.text, thought, res.finished):
            continue

        consultations += 1
        interv = intervener.intervene(example, thought, large, cfg, result.large_usage)
        result.interventions.append({"at_tokens": gen_tokens,
                                     "action": interv.action, "text": interv.text,
                                     "raw": interv.raw})
        if interv.action == "append":
            thought = _append_note(thought, interv.text)
            result.n_repairs += 1
        elif interv.action == "replace":
            thought = interv.text
            result.n_repairs += 1
        # action == "none": leave the trace unchanged, let the small model continue

    if cfg.small_logprobs:
        # One extra prefill-only pass over the FULL final trace to score every token
        # (question + injected repairs + generated) as prompt_logprobs. Diagnostic:
        # NOT added to small_usage so it doesn't inflate token/latency/cost metrics.
        full = base_prompt + thought
        pl = small.complete(full, max_tokens=1, temperature=0,
                            prompt_logprobs=cfg.small_logprobs)
        result.logprobs = {
            "base_prompt_tokens": len(small.tokenizer.encode(base_prompt,
                                                             add_special_tokens=False)),
            "generated": gen_lp,               # online top-k logprobs of generated tokens
            "prefill": pl.prompt_logprobs,     # raw vLLM prompt_logprobs over the full trace
        }

    result.final_text = thought
    return result


# --------------------------------------------------------------------------------------
# Trace-consuming strategies: small writes the full trace once, large uses it.
# All three (repair_once / or / orr) share the small trace via _small_trace, which
# reuses a saved trace (cfg.small_traces) when available instead of re-running the 8B.
# --------------------------------------------------------------------------------------
def _small_trace(example, small, cfg) -> tuple[str, Usage]:
    """Return (small full trace, small Usage), reusing a saved trace if provided."""
    store = cfg.small_traces
    if store and example.id in store and "final_text" in store[example.id]:
        row = store[example.id]
        return row["final_text"], usage_from_dict(row, "small")
    prompt = small.build_prompt(example.user_prompt, system=cfg.system_for(example.kind))
    res = small.complete(prompt, max_tokens=cfg.max_tokens, **_sample_kwargs(cfg))
    usage = Usage()
    usage.add(res.prompt_tokens, res.completion_tokens, res.seconds,
              res.prompt_ids, res.gen_ids)
    return res.text, usage


# -- repair_once: large REVIEWS the trace in a fresh turn, then answers -----------------
REPAIR_ONCE_SYSTEM = (
    "You are an expert problem solver reviewing another model's full solution."
)
REPAIR_ONCE_TASK = (
    "Review the reasoning and answer above. Fix any mistakes and give the correct, "
    "final solution. Put the final answer within \\boxed{}."
)


def repair_once(example, small, large, cfg) -> GenResult:
    result = GenResult(final_text="", answer_from="large")
    small_trace, result.small_usage = _small_trace(example, small, cfg)

    user = (f"Problem:\n{example.user_prompt}\n\n"
            f"Another model produced the following reasoning and answer:\n{small_trace}\n\n"
            f"{REPAIR_ONCE_TASK}")
    large_prompt = large.build_prompt(user, system=REPAIR_ONCE_SYSTEM,
                                      enable_thinking=cfg.repair_thinking)
    res2 = large.complete(large_prompt, max_tokens=cfg.repair_max_tokens,
                          **_sample_kwargs(cfg))
    result.large_usage.add(res2.prompt_tokens, res2.completion_tokens, res2.seconds,
                           res2.prompt_ids, res2.gen_ids)
    result.n_repairs = 1
    result.final_text = res2.text           # graded from the large model's output
    return result


# -- OR / ORR (Jindal et al.): inject the small reasoning INSIDE the large model's -------
# -- own <think> block. OR closes </think> (no refinement, direct answer); ORR leaves ---
# -- it open with a skeptical prefill so the large model briefly refines, then answers. --
ORR_PREFILL = (
    "nahh.. I got some speculations. let me check that <SPECULATIONS> {reason} "
    "</SPECULATIONS> ohh.. no.. But wait.. These speculations could be incorrect. "
)


def _offloaded(example, small, large, cfg, refine: bool) -> GenResult:
    result = GenResult(final_text="", answer_from="large")
    small_trace, result.small_usage = _small_trace(example, small, cfg)
    reasoning = split_think(small_trace)[0].strip()   # the 8B's thinking (drop its answer)

    # large model's assistant turn, opened at <think>, then we prefill it ourselves.
    base = large.build_prompt(example.user_prompt, system=cfg.system_for(example.kind),
                              enable_thinking=True)
    if refine:                                        # ORR: keep <think> open
        prompt = base + ORR_PREFILL.replace("{reason}", reasoning)
    else:                                             # OR: inject reason and close <think>
        prompt = base + f"{reasoning}\n{large.family.think_close}\n\n"

    res = large.complete(prompt, max_tokens=cfg.repair_max_tokens, **_sample_kwargs(cfg))
    result.large_usage.add(res.prompt_tokens, res.completion_tokens, res.seconds,
                           res.prompt_ids, res.gen_ids)
    result.n_repairs = 1
    result.final_text = res.text
    return result


def offloaded_reasoning(example, small, large, cfg) -> GenResult:      # OR
    return _offloaded(example, small, large, cfg, refine=False)


def offloaded_refine(example, small, large, cfg) -> GenResult:         # ORR
    return _offloaded(example, small, large, cfg, refine=True)


# name -> strategy function
STRATEGIES = {
    "small":       small_only,
    "large":       large_only,
    "periodic":    periodic,
    "repair_once": repair_once,
    "or":          offloaded_reasoning,
    "orr":         offloaded_refine,
}

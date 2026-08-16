"""
Shared plumbing for the thought-repair experiments.

Responsibilities:
  * Model registry  -> family-specific chat-template / sampling / think-tag config.
  * ModelClient     -> talks to a vLLM OpenAI-compatible server via the /v1/completions
                       endpoint, so we can *resume an assistant turn from a partial
                       thought* (needed for interleaved repair). Renders prompts with the
                       model's own tokenizer chat template.
  * Usage           -> per-call token + wall-time accounting.

Everything downstream (strategies, run_eval) only touches ModelClient + Usage, so adding
a new model family = adding one MODEL_REGISTRY entry, no logic changes.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Optional

import requests
from transformers import AutoTokenizer


# --------------------------------------------------------------------------------------
# Model registry: per-family behaviour. Matched against the HF model id by substring.
# --------------------------------------------------------------------------------------
@dataclass
class FamilyConfig:
    match: str                      # case-insensitive substring of the model id
    supports_system: bool           # can we send a system message?
    chat_template_kwargs: dict      # extra kwargs for apply_chat_template
    force_think_open: bool          # ensure the rendered prompt ends inside <think>
    think_open: str = "<think>"
    think_close: str = "</think>"
    # Recommended sampling for *thinking* generation.
    temperature: float = 0.6
    top_p: float = 0.95
    top_k: int = 20


# Order matters: first substring match wins.
MODEL_REGISTRY: list[FamilyConfig] = [
    FamilyConfig(
        match="qwen3",
        supports_system=True,
        chat_template_kwargs={"enable_thinking": True},
        force_think_open=True,          # Qwen3 template already opens <think>; harmless to assert
    ),
    FamilyConfig(
        match="deepseek-r1-distill",
        supports_system=False,          # distill models: fold instructions into the user turn
        chat_template_kwargs={},
        force_think_open=True,          # must prefill <think>\n to guarantee reasoning
    ),
    FamilyConfig(
        match="r1-distill",             # looser fallback for the same family
        supports_system=False,
        chat_template_kwargs={},
        force_think_open=True,
    ),
]

# Generic fallback for anything unrecognised (assume a thinking model with system support).
_DEFAULT_FAMILY = FamilyConfig(
    match="",
    supports_system=True,
    chat_template_kwargs={"enable_thinking": True},
    force_think_open=False,
)


def family_for(model_id: str) -> FamilyConfig:
    low = model_id.lower()
    for fam in MODEL_REGISTRY:
        if fam.match and fam.match in low:
            return fam
    return _DEFAULT_FAMILY


# --------------------------------------------------------------------------------------
# Usage accounting
# --------------------------------------------------------------------------------------
def _common_prefix_len(a: list[int], b: list[int]) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


@dataclass
class Usage:
    """Accumulates token + latency cost for a single model across many calls.

    raw_in / raw_out : what the server reported per call, summed. With prefix caching
                       the growing thought is re-sent each round, so raw_in over-counts
                       vs. a KV-persistent session -- kept as a pessimistic upper bound.
    gen_out          : generated (completion) tokens only == raw_out (renamed in reports).
    prompt_first     : prompt tokens of the very first call.
    new_prefix       : prompt tokens that actually had to be prefilled (KV-cache MISSES),
                       computed deterministically as the tokens beyond the longest common
                       prefix with this model's previous prompt (mirrors vLLM prefix reuse).
    cached_prefix    : prompt tokens served from the KV cache (raw_in - new_prefix view).
                       new_prefix + cached_prefix == our local total prompt tokens.
    n_calls          : number of server round-trips for this model.
    seconds          : summed measured inference latency across this model's calls (the
                       time waited on each /v1/completions request; excludes Python glue).
    """

    raw_in: int = 0
    raw_out: int = 0
    prompt_first: Optional[int] = None
    new_prefix: int = 0
    cached_prefix: int = 0
    n_calls: int = 0
    seconds: float = 0.0
    # token ids of the previous call's FULL sequence (prompt + generated). We compare
    # against prompt+gen -- not just the prompt -- because decoded tokens stay in the KV
    # cache, so the small model's own generation is a cache hit on the next chunk. This is
    # also correct for the large model, whose next prompt diverges after the shared prefix.
    _last_full_ids: list = field(default_factory=list, repr=False)

    def add(self, prompt_tokens: int, completion_tokens: int, seconds: float,
            prompt_ids: Optional[list[int]] = None,
            gen_ids: Optional[list[int]] = None) -> None:
        if self.prompt_first is None:
            self.prompt_first = prompt_tokens
        self.raw_in += prompt_tokens
        self.raw_out += completion_tokens
        self.n_calls += 1
        self.seconds += seconds
        if prompt_ids is not None:
            hit = _common_prefix_len(prompt_ids, self._last_full_ids)
            self.cached_prefix += hit
            self.new_prefix += len(prompt_ids) - hit
            self._last_full_ids = prompt_ids + (gen_ids or [])

    def as_dict(self, prefix: str) -> dict:
        return {
            f"{prefix}_raw_in": self.raw_in,
            f"{prefix}_gen_out": self.raw_out,
            f"{prefix}_prompt_first": self.prompt_first or 0,
            f"{prefix}_new_prefix": self.new_prefix,
            f"{prefix}_cached_prefix": self.cached_prefix,
            f"{prefix}_calls": self.n_calls,
            f"{prefix}_seconds": round(self.seconds, 3),
        }


def gen_logprobs_to_list(lp: Optional[dict]) -> list:
    """Flatten OpenAI-style generated logprobs into [{token, logprob, topk}, ...]."""
    if not lp:
        return []
    toks = lp.get("tokens") or []
    tlp = lp.get("token_logprobs") or []
    top = lp.get("top_logprobs") or []
    return [{"token": t,
             "logprob": tlp[i] if i < len(tlp) else None,
             "topk": top[i] if i < len(top) else None}
            for i, t in enumerate(toks)]


def usage_from_dict(row: dict, prefix: str) -> Usage:
    """Rebuild a Usage from a saved results row (for reusing precomputed traces).

    Restores the token/latency metrics so a reused trace still contributes its
    (already-incurred) cost/latency to the method's totals.
    """
    u = Usage()
    u.raw_in = row.get(f"{prefix}_raw_in", 0)
    u.raw_out = row.get(f"{prefix}_gen_out", 0)
    u.prompt_first = row.get(f"{prefix}_prompt_first", 0)
    u.new_prefix = row.get(f"{prefix}_new_prefix", 0)
    u.cached_prefix = row.get(f"{prefix}_cached_prefix", 0)
    u.n_calls = row.get(f"{prefix}_calls", 0)
    u.seconds = row.get(f"{prefix}_seconds", 0.0)
    return u


@dataclass
class CompletionResult:
    text: str
    finished: bool          # True if the model stopped on its own (EOS/stop), not length cap
    prompt_tokens: int
    completion_tokens: int
    seconds: float
    prompt_ids: list = field(default_factory=list)   # local token ids of the prompt (for KV split)
    gen_ids: list = field(default_factory=list)       # local token ids of the generation
    gen_logprobs: dict = None       # raw OpenAI-style logprobs of generated tokens (if requested)
    prompt_logprobs: list = None    # raw vLLM prompt_logprobs of the prefill (if requested)


# --------------------------------------------------------------------------------------
# Model client (vLLM OpenAI-compatible server, /v1/completions)
# --------------------------------------------------------------------------------------
class ModelClient:
    def __init__(self, model_id: str, base_url: str, timeout: float = 3600.0,
                 tokenizer_path: Optional[str] = None):
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.family = family_for(model_id)
        # Tokenizer is only used for prompt templating (CPU, no GPU).
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path or model_id,
                                                        trust_remote_code=True)

    # -- prompt construction --------------------------------------------------------
    def build_prompt(self, user_content: str, system: Optional[str] = None,
                     enable_thinking: bool = True) -> str:
        """Render the chat prompt up to (and including) the assistant turn.

        enable_thinking=False produces a non-thinking prompt (used for cheap repair
        calls). For families that expose the flag (Qwen3) it is threaded into the
        chat template; for the rest we simply skip the forced <think> prefill.
        """
        messages = []
        if system and self.family.supports_system:
            messages.append({"role": "system", "content": system})
        elif system:  # family without system support: prepend to the user turn
            user_content = f"{system}\n\n{user_content}"
        messages.append({"role": "user", "content": user_content})

        kwargs = dict(self.family.chat_template_kwargs)
        if "enable_thinking" in kwargs:
            kwargs["enable_thinking"] = enable_thinking

        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            **kwargs,
        )
        if enable_thinking and self.family.force_think_open \
                and self.family.think_open not in prompt:
            prompt = prompt + self.family.think_open + "\n"
        return prompt

    # -- generation -----------------------------------------------------------------
    def complete(self, prompt: str, max_tokens: int,
                 temperature: Optional[float] = None,
                 top_p: Optional[float] = None,
                 top_k: Optional[int] = None,
                 stop: Optional[list[str]] = None,
                 seed: Optional[int] = None,
                 logprobs: Optional[int] = None,
                 prompt_logprobs: Optional[int] = None) -> CompletionResult:
        """Raw completion on top of `prompt`. finish_reason=='length' -> hit the cap.

        logprobs>0 requests top-k logprobs for generated tokens; prompt_logprobs>0
        requests top-k logprobs for the prefill (prompt) tokens. Both capped by the
        server's --max-logprobs (default 20).
        """
        fam = self.family
        payload = {
            "model": self.model_id,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": fam.temperature if temperature is None else temperature,
            "top_p": fam.top_p if top_p is None else top_p,
            "add_special_tokens": False,   # prompt already carries chat-template specials
        }
        tk = fam.top_k if top_k is None else top_k
        if tk and tk > 0:
            payload["top_k"] = tk
        if stop:
            payload["stop"] = stop
        if seed is not None:
            payload["seed"] = seed
        if logprobs:
            payload["logprobs"] = logprobs
        if prompt_logprobs:
            payload["prompt_logprobs"] = prompt_logprobs

        # Local token ids of the exact prompt, for the deterministic KV-cache split.
        # Same tokenizer + add_special_tokens=False as the server sees, so the
        # longest-common-prefix delta mirrors vLLM's prefix reuse.
        prompt_ids = self.tokenizer.encode(prompt, add_special_tokens=False)

        t0 = time.perf_counter()
        resp = requests.post(f"{self.base_url}/v1/completions", json=payload,
                             timeout=self.timeout)
        dt = time.perf_counter() - t0
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})
        return CompletionResult(
            text=choice["text"],
            finished=(choice.get("finish_reason") != "length"),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            seconds=dt,
            prompt_ids=prompt_ids,
            gen_ids=self.tokenizer.encode(choice["text"], add_special_tokens=False),
            gen_logprobs=choice.get("logprobs"),
            prompt_logprobs=choice.get("prompt_logprobs"),
        )


# --------------------------------------------------------------------------------------
# Small text helpers shared by strategies + grading
# --------------------------------------------------------------------------------------
def has_think_close(text: str, close: str = "</think>") -> bool:
    return close in text


def split_think(text: str, close: str = "</think>") -> tuple[str, str]:
    """Return (reasoning, answer_section). answer_section is everything after </think>."""
    idx = text.rfind(close)
    if idx == -1:
        return text, ""
    return text[:idx], text[idx + len(close):]


def wait_for_server(base_url: str, timeout: float = 1800.0, interval: float = 5.0) -> bool:
    """Poll /v1/models until the vLLM server is ready."""
    url = f"{base_url.rstrip('/')}/v1/models"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if requests.get(url, timeout=5).status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(interval)
    return False

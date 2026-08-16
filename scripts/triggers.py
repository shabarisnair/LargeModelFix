"""WHEN to intervene.

A Trigger decides (a) how many tokens the small model generates before we pause,
and (b) whether an intervention should fire at that pause. This is deliberately
separate from HOW we intervene (see interventions.py) so the two can be edited or
extended independently. Add a new policy = new Trigger subclass + a line in
make_trigger; nothing else changes.
"""

from __future__ import annotations


class Trigger:
    def step_max_tokens(self, remaining: int) -> int:
        """Token budget for the next small-model generation chunk."""
        raise NotImplementedError

    def stop(self) -> list[str] | None:
        """Optional stop strings for the chunk (None = only natural EOS/length)."""
        return None

    def should_intervene(self, chunk_text: str, thought: str, finished: bool) -> bool:
        """After a chunk, decide whether to consult the target model."""
        raise NotImplementedError


class IntervalTrigger(Trigger):
    """Intervene every `interval` generated tokens, until the small model finishes."""

    def __init__(self, interval: int):
        self.interval = interval

    def step_max_tokens(self, remaining: int) -> int:
        return min(self.interval, remaining)

    def should_intervene(self, chunk_text: str, thought: str, finished: bool) -> bool:
        # We only reach here while the model is still going, so always consult.
        return not finished


TRIGGERS = ["interval"]


def make_trigger(name: str, cfg) -> Trigger:
    if name == "interval":
        return IntervalTrigger(cfg.repair_interval)
    raise ValueError(f"unknown trigger '{name}'. options: {TRIGGERS}")

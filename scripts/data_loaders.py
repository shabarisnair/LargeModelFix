"""Dataset loaders -> a single uniform Example type.

Every dataset is reduced to:
    Example(id, user_prompt, gold, kind)
where `kind` selects the grader ('math' or 'mcq') and the default system prompt.
For multiple-choice (GPQA) the options are baked into user_prompt and `gold` is
the correct letter; option order is shuffled deterministically from `seed`.

Add a dataset by appending to DATASETS -- nothing else changes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Optional

from datasets import load_dataset


@dataclass
class Example:
    id: str
    user_prompt: str        # the full question shown to the model (incl. options for MCQ)
    gold: str               # gold answer string; for MCQ this is a letter "A".."D"
    kind: str               # "math" | "mcq"


# Default system prompts (override on the CLI with --system-math / --system-mcq).
# Two deliberate requirements:
#   1. each reasoning step separated by a blank line ("\n\n") -- gives clean, detectable
#      step boundaries (used by the AdaptiveStep-based method).
#   2. after the thinking block, emit ONLY \boxed{answer} -- no post-hoc explanation,
#      so generated tokens measure reasoning rather than presentation.
SYSTEM_PROMPTS = {
    "math": (
        "Think and reason step by step, separating each reasoning step with a blank "
        "line (\\n\\n).\n"
        "When you have finished thinking, output ONLY the final answer inside "
        "\\boxed{} and nothing else. Do not explain, summarise, or restate your "
        "reasoning after the thinking block -- the boxed answer must be the entire "
        "content of your reply after thinking."
    ),
    "mcq": (
        "You are answering a multiple-choice question. Think and reason step by step, "
        "separating each reasoning step with a blank line (\\n\\n).\n"
        "When you have finished thinking, output ONLY the letter of the correct option "
        "inside \\boxed{} and nothing else (e.g. \\boxed{C}). Do not explain, "
        "summarise, or restate your reasoning after the thinking block -- the boxed "
        "letter must be the entire content of your reply after thinking."
    ),
}

_LETTERS = ["A", "B", "C", "D"]


@dataclass
class DatasetSpec:
    hf_path: str
    split: str
    loader: Callable          # (row, idx, rng) -> Example
    config: Optional[str] = None


def _math500(row, idx, rng) -> Example:
    return Example(id=f"math500-{idx}", user_prompt=row["problem"],
                   gold=str(row["answer"]), kind="math")


def _aime2024(row, idx, rng) -> Example:
    return Example(id=f"aime2024-{idx}", user_prompt=row["Problem"],
                   gold=str(row["Answer"]).strip(), kind="math")


def _aime2025(row, idx, rng) -> Example:
    return Example(id=f"aime2025-{idx}", user_prompt=row["problem"],
                   gold=str(row["answer"]).strip(), kind="math")


def _gpqa_diamond(row, idx, rng) -> Example:
    correct = row["Correct Answer"].strip()
    options = [correct,
               row["Incorrect Answer 1"].strip(),
               row["Incorrect Answer 2"].strip(),
               row["Incorrect Answer 3"].strip()]
    rng.shuffle(options)
    gold_letter = _LETTERS[options.index(correct)]
    lettered = "\n".join(f"({L}) {opt}" for L, opt in zip(_LETTERS, options))
    prompt = f"{row['Question'].strip()}\n\n{lettered}"
    return Example(id=f"gpqa-{idx}", user_prompt=prompt, gold=gold_letter, kind="mcq")


def _aime2025(row, idx, rng) -> Example:
    return Example(id=f"aime2025-{idx}", user_prompt=row["problem"],
                   gold=str(row["answer"]).strip(), kind="math")


def _gsm8k(row, idx, rng) -> Example:
    # gold is the number after the "#### " marker; strip thousands separators.
    gold = row["answer"].split("####")[-1].strip().replace(",", "")
    return Example(id=f"gsm8k-{idx}", user_prompt=row["question"], gold=gold, kind="math")


DATASETS: dict[str, DatasetSpec] = {
    "math500": DatasetSpec("HuggingFaceH4/MATH-500", "test", _math500),
    "aime2024": DatasetSpec("Maxwell-Jia/AIME_2024", "train", _aime2024),
    "aime2025": DatasetSpec("yentinglin/aime_2025", "train", _aime2025),
    "aime2025": DatasetSpec("math-ai/aime25", "test", _aime2025),
    "gsm8k": DatasetSpec("openai/gsm8k", "test", _gsm8k, config="main"),
    "gpqa": DatasetSpec("Idavidrein/gpqa", "train", _gpqa_diamond, config="gpqa_diamond"),
}


def load_examples(name: str, limit: Optional[int] = None, seed: int = 0) -> list[Example]:
    if name not in DATASETS:
        raise ValueError(f"unknown dataset '{name}'. options: {list(DATASETS)}")
    spec = DATASETS[name]
    ds = (load_dataset(spec.hf_path, spec.config, split=spec.split)
          if spec.config else load_dataset(spec.hf_path, split=spec.split))
    rng = random.Random(seed)
    examples = [spec.loader(row, i, rng) for i, row in enumerate(ds)]
    if limit is not None:
        examples = examples[:limit]
    return examples

"""Answer extraction + grading.

Grading always runs on the text *after* the last </think> (the model's final
answer section), never on the reasoning. Two graders:
  * math  -> symbolic equivalence via the `math-verify` library
  * mcq   -> compare the boxed option letter

Both are wrapped so a parse failure scores 0 rather than crashing a run.
"""

from __future__ import annotations

import re

from math_verify import parse, verify

from common import split_think


def extract_boxed(text: str) -> str | None:
    """Return the content of the last \\boxed{...}, handling nested braces."""
    key = r"\boxed{"
    start = text.rfind(key)
    if start == -1:
        return None
    i = start + len(key)
    depth = 1
    out = []
    while i < len(text) and depth > 0:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
        out.append(c)
        i += 1
    return "".join(out).strip()


def _answer_section(full_text: str) -> str:
    """Text after the last </think>; fall back to the whole text if none."""
    _, answer = split_think(full_text)
    return answer if answer.strip() else full_text


def grade_math(gold: str, full_text: str) -> bool:
    answer = _answer_section(full_text)
    try:
        # Wrap gold in $...$ so latex extraction fires (needed for tuples like
        # "\left(3,\frac{\pi}{2}\right)"); pass the *full* answer text so math_verify
        # extracts the \boxed{} expression itself.
        gold_str = gold if "$" in gold else f"${gold}$"
        gold_parsed = parse(gold_str)
        pred_parsed = parse(answer)
        if verify(gold_parsed, pred_parsed):   # verify(gold, target)
            return True
    except Exception:
        pass
    # last-ditch: exact boxed-string match.
    pred = extract_boxed(answer)
    return pred is not None and pred.strip() == gold.strip()


_LETTER_RE = re.compile(r"[ABCD]")


def grade_mcq(gold_letter: str, full_text: str) -> bool:
    answer = _answer_section(full_text)
    boxed = extract_boxed(answer)
    pred_letter = None
    if boxed:
        m = _LETTER_RE.search(boxed.upper())
        if m:
            pred_letter = m.group(0)
    if pred_letter is None:
        # fall back to "answer is (B)" / "answer: B" patterns in the answer section.
        m = re.search(r"answer\s*(?:is|:)?\s*\(?([ABCD])\)?", answer, re.IGNORECASE)
        if m:
            pred_letter = m.group(1).upper()
    return pred_letter is not None and pred_letter == gold_letter.strip().upper()


def grade(kind: str, gold: str, full_text: str) -> bool:
    if kind == "math":
        return grade_math(gold, full_text)
    if kind == "mcq":
        return grade_mcq(gold, full_text)
    raise ValueError(f"unknown grading kind: {kind}")

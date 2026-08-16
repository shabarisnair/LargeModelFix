"""Resolve math_prompt_template.txt into the final user prompt.

The template has three placeholders:
    {Gold-standard demonstration examples}   <- 4 well-formed DAGs from problems_merged
    {Bad demonstration examples}             <- bad_examples.txt, verbatim
    {Test problem statement}                 <- the AIME problem

Demonstrations are rendered in exactly the shape the model must emit: a single JSON
object with a "steps" array, so the format shown and the format demanded agree.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "math_prompt_template.txt"
BAD = HERE / "bad_examples.txt"
DEMOS = HERE / "datasets" / "demos.json"

PROMPT_VERSION = "dagjson-v1"


def render_demo(rec: dict, n: int) -> str:
    body = json.dumps({"steps": rec["steps"]}, indent=2, ensure_ascii=False)
    return (f"Example {n}\n"
            f"Problem: {rec['problem_text'].strip()}\n"
            f"Solution:\n{body}")


def demo_block(demos: list[dict] | None = None) -> str:
    if demos is None:
        demos = json.loads(DEMOS.read_text())
    return "\n\n".join(render_demo(d, i + 1) for i, d in enumerate(demos))


def bad_block() -> str:
    return BAD.read_text(encoding="utf-8-sig").strip()


def build_prompt(question: str, demos: list[dict] | None = None) -> str:
    t = TEMPLATE.read_text(encoding="utf-8-sig")
    t = t.replace("{Gold-standard demonstration examples}", demo_block(demos))
    t = t.replace("{Bad demonstration examples}", bad_block())
    t = t.replace("{Test problem statement}", question.strip())
    return t.rstrip() + "\n"


if __name__ == "__main__":
    import sys
    ds = sys.argv[1] if len(sys.argv) > 1 else "aime2025"
    rows = [json.loads(l) for l in open(HERE / "datasets" / f"{ds}.jsonl")]
    out = HERE / f"resolved_prompt_{ds}_example.txt"
    out.write_text(build_prompt(rows[0]["question"]))
    print(f"wrote {out} ({out.stat().st_size:,} bytes) for {rows[0]['id']}")

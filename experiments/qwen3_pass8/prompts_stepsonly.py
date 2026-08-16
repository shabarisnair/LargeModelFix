"""Resolve the steps-only prompt: reasoning steps as JSON, no DAG annotation.

Same skeleton as prompts.py, with the dependency machinery removed:
  * a step is just a string, so step_id / edge / direct_dependent_steps are gone
  * the topological-order and closure rules are gone with them
  * the demonstrations are the same four problems, reduced to their `node` sentences
  * there is no Bad Examples section: both originals concern the `edge` field (missing
    "Step N" tags, plural grouping), which no longer exists in this format

Kept from the original: atomic one-assertion steps, LaTeX in dollar signs, and JSON-only
output. The closing step is now pinned to "The final answer is $\boxed{N}$." with N
required to be a fully evaluated number -- measured on the 1,920 responses from the
previous run, 9% of extraction failures were the model writing a placeholder such as
\boxed{m + n} instead of computing the integer.
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "math_prompt_template_stepsonly.txt"
DEMOS = HERE / "datasets" / "demos.json"

PROMPT_VERSION = "stepsonly-v1"


def render_demo(rec: dict, n: int) -> str:
    steps = [s["node"] for s in rec["steps"]]
    body = json.dumps({"steps": steps}, indent=2, ensure_ascii=False)
    return (f"Example {n}\n"
            f"Problem: {rec['problem_text'].strip()}\n"
            f"Solution:\n{body}")


def demo_block(demos: list[dict] | None = None) -> str:
    if demos is None:
        demos = json.loads(DEMOS.read_text())
    return "\n\n".join(render_demo(d, i + 1) for i, d in enumerate(demos))


def build_prompt(question: str, demos: list[dict] | None = None) -> str:
    t = TEMPLATE.read_text(encoding="utf-8-sig")
    t = t.replace("{Gold-standard demonstration examples}", demo_block(demos))
    t = t.replace("{Test problem statement}", question.strip())
    return t.rstrip() + "\n"


if __name__ == "__main__":
    import sys
    ds = sys.argv[1] if len(sys.argv) > 1 else "aime2024"
    rows = [json.loads(l) for l in open(HERE / "datasets" / f"{ds}.jsonl")]
    out = HERE / f"resolved_prompt_stepsonly_{ds}_example.txt"
    out.write_text(build_prompt(rows[0]["question"]))
    print(f"wrote {out.name} ({out.stat().st_size:,} bytes) for {rows[0]['id']}")

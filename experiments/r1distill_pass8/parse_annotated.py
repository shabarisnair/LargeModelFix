"""Parse self-annotated reasoning steps (prompt v3 / v4) into a dependency DAG.

v3   {2} -> [0,1] step text
v4   {2} step text <- [0,1]

Returns one record per trace with the steps, their declared parents, and a list of
defects, so a malformed trace is reported rather than silently mis-parsed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# The index marker is anchored at the very start of a step. Measured against 1,571,709 v1
# steps: zero begin with "{N}", so this cannot collide with real reasoning text.
IDX_RE = re.compile(r"^\s*\{(\d+)\}\s*")
# v3: arrow + list immediately after the index.
V3_DEPS_RE = re.compile(r"^->\s*\[([\d,\s]*)\]\s*")
# v4: bare list at the very end. The models would not emit a "<-" arrow (see prompts.py),
# so the collision with real content has to be filtered instead: 4,103 of 1,571,709 v1
# steps end with a bare "[N,...]", nearly all LiveCodeBench code like "return [0,1]".
# `only_backward` below rejects any trailing list that is not a valid dependency set.
V4_DEPS_RE = re.compile(r"\s\[([\d,\s]*)\]\s*$")


@dataclass
class Step:
    index: int          # index the model declared
    pos: int            # position in the trace, 0-based
    deps: list[int]
    text: str


@dataclass
class ParsedTrace:
    steps: list[Step] = field(default_factory=list)
    defects: list[str] = field(default_factory=list)
    n_raw_blocks: int = 0

    @property
    def ok(self) -> bool:
        return not self.defects


def _deps(raw: str) -> list[int]:
    return [int(x) for x in re.findall(r"\d+", raw)]


def parse_trace(thinking: str, version: str) -> ParsedTrace:
    if version not in ("v3", "v4"):
        raise ValueError("version must be v3 or v4")
    out = ParsedTrace()
    blocks = [b.strip() for b in thinking.split("\n\n") if b.strip()]
    out.n_raw_blocks = len(blocks)

    for pos, block in enumerate(blocks):
        m = IDX_RE.match(block)
        if not m:
            out.defects.append(f"block {pos}: no {{index}} marker")
            continue
        idx = int(m.group(1))
        rest = block[m.end():]
        deps: list[int] = []
        if version == "v3":
            dm = V3_DEPS_RE.match(rest)
            if dm:
                deps = _deps(dm.group(1))
                rest = rest[dm.end():]
        else:
            dm = V4_DEPS_RE.search(rest)
            if dm:
                cand = _deps(dm.group(1))
                # A real dependency set only ever points backwards. A code step ending in
                # "return [0,1]" at step 0 or 1 fails this and keeps its text intact.
                if cand and all(d < idx for d in cand):
                    deps = cand
                    rest = rest[:dm.start()]
                else:
                    out.defects.append(
                        f"step {idx}: trailing {dm.group(0).strip()} is not a valid "
                        f"dependency set, treated as text")
        out.steps.append(Step(index=idx, pos=pos, deps=deps, text=rest.strip()))

    # numbering must be 0-based and strictly +1
    for i, s in enumerate(out.steps):
        if s.index != i:
            out.defects.append(f"step at position {i} declared index {s.index}")
            break
    # dependencies must point strictly backwards and exist
    n = len(out.steps)
    for s in out.steps:
        for d in s.deps:
            if d >= s.index:
                out.defects.append(f"step {s.index} depends on {d} (not strictly earlier)")
            elif d >= n:
                out.defects.append(f"step {s.index} depends on {d} which does not exist")
    return out


def to_dag(parsed: ParsedTrace) -> dict:
    """Index-aligned arrays, matching the shape the DAG viewer already consumes."""
    n = len(parsed.steps)
    return {
        "n": n,
        "parents": [sorted(s.deps) for s in parsed.steps],
        "text": [s.text for s in parsed.steps],
        "roots": [s.index for s in parsed.steps if not s.deps],
    }

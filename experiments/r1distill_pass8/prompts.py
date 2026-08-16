"""User-prompt construction, versioned.

DeepSeek-R1-Distill models are used without a system message (per DeepSeek's own
guidance) -- every instruction is folded into the user turn.

Two instructions are appended to every question:
  1. the reasoning-step separator ("\n\n" between steps), for downstream analysis;
  2. a final-answer format, so the text after </think> can be parsed mechanically.

Both prompt versions are kept here so either run is reproducible. `PROMPT_VERSION` is
recorded on every generated row and gates trace reuse (see generate.py:is_reusable), so
traces from different versions are never silently pooled.

  v1  the original run (all 4,800 production traces). Its "and nothing else after it"
      only forbade text *following* the \boxed{}, so models legitimately restated their
      working before it.
  v2  requires the whole answer section to be the final answer alone. Measured
      compliance on a 192-trace test: 32B/gsm8k 50%, 32B/webinstruct 16%, everything
      else ~0% -- the R1-distill family is post-trained to restate its solution after
      </think> and largely ignores the instruction. See trace_samples_v2/README.md.
"""

from __future__ import annotations

PROMPT_VERSION = "v2"          # version used for new generations

STEP_SEP = (
    "While you reason, separate each distinct reasoning step with a blank line "
    "(i.e. end each step with a double newline \"\\n\\n\")."
)

# --- v1 -----------------------------------------------------------------------------
V1_NUMERIC_FMT = (
    "After you finish thinking, state your final answer as a single number inside "
    "\\boxed{}, with no units, no symbols and no words -- for example \\boxed{42} or "
    "\\boxed{3.14}. Give the \\boxed{} answer and nothing else after it."
)

V1_MCQ_FMT = (
    "After you finish thinking, state your final answer as the single letter of the "
    "correct option inside \\boxed{} -- for example \\boxed{C}. Give the \\boxed{} "
    "answer and nothing else after it."
)

V1_LCB_ONLY_CODE = ""          # v1 added no such instruction for LiveCodeBench

# --- v2 -----------------------------------------------------------------------------
V2_NUMERIC_FMT = (
    "When you have finished thinking, close the thinking block and then output ONLY your "
    "final answer, as a single number inside \\boxed{} -- for example \\boxed{42} or "
    "\\boxed{3.14}, with no units, no symbols and no words.\n"
    "Everything after the thinking block must be exactly that one \\boxed{...} "
    "expression and nothing else: no explanation, no summary of your reasoning, no "
    "restatement of the question, no working, and no text before or after the "
    "\\boxed{...}."
)

V2_MCQ_FMT = (
    "When you have finished thinking, close the thinking block and then output ONLY your "
    "final answer, as the single letter of the correct option inside \\boxed{} -- for "
    "example \\boxed{C}.\n"
    "Everything after the thinking block must be exactly that one \\boxed{...} "
    "expression and nothing else: no explanation, no summary of your reasoning, no "
    "restatement of the options, and no text before or after the \\boxed{...}."
)

V2_LCB_ONLY_CODE = (
    "When you have finished thinking, close the thinking block and then output ONLY the "
    "final Python program in a single ```python code block. Everything after the "
    "thinking block must be exactly that one code block and nothing else: no "
    "explanation, no summary of your approach, and no text before or after the code "
    "block."
)

# --- v3 / v4: the model annotates its own step dependencies ---------------------------
# Same post-</think> behaviour as v1; only the in-thinking step format changes, so v3/v4
# results stay comparable with the v1 production run.
#
# Marker choice is measured, not guessed. Across the 1,571,709 reasoning steps in the v1
# traces:
#   * 0 steps begin with "{N}"          -> the leading index marker is collision-free
#   * 4,103 steps END with "[N,...]"    -> a bare trailing list would be misparsed as
#     dependencies ~1 step in 400, almost entirely LiveCodeBench code ("return [0,1]",
#     "print(dp[0])").
# A "<- [0,1]" terminator was tried first to disambiguate v4, but the models would not
# produce it: asked for the arrow they emitted a bare "[0]" anyway, and when the
# instruction was strengthened they stopped emitting dependencies altogether. v4 therefore
# uses the bare trailing list, and parse_annotated.py filters the collisions (a trailing
# list only counts when every index is strictly smaller than the step's own index).
#
# Neither version works from the instruction alone: R1-Distill models ignore formatting
# rules aimed at the thinking block. PREFILL seeds the assistant turn with "{0} " so the
# very first token is already in the required format, which the models then sustain.

_DEP_RULES = """- Every step starts with its index in curly braces at the very beginning: {0}, {1}, {2}, ...
- Indices are 0-based and increase by exactly 1 each step. Never skip, repeat or reorder them.
- Every index listed as a dependency must be strictly smaller than the step's own index.
- Inside the square brackets write only digits separated by commas, like [0,3,4] -- no
  spaces, no ranges, no words, no other punctuation.
- Step {0} never lists dependencies, because nothing comes before it.
- A step that starts a fresh line of thought and does not build on anything earlier simply
  has no dependency marker at all.
- These markers belong only inside your thinking. Once you finish thinking, never write
  {index} markers or dependency lists again."""

V3_STEP_FMT = (
    "Lay out your reasoning as a numbered sequence of steps. Put each step in its own "
    "paragraph, separated from the next by a blank line (a double newline \"\\n\\n\").\n\n"
    "Begin each step with its index in curly braces. If the step follows from, uses, or "
    "builds on earlier steps, put an arrow and the indices of those steps in square "
    "brackets straight after the index, before the step's text:\n\n"
    "{0} the first step, which nothing precedes\n\n"
    "{1} a step that starts a separate idea and uses nothing earlier\n\n"
    "{2} -> [0,1] a step that follows from steps 0 and 1\n\n"
    "{3} -> [1] a step that follows only from step 1\n\n"
    "Follow these rules exactly so the markers can be parsed:\n" + _DEP_RULES
)

V4_STEP_FMT = (
    "Lay out your reasoning as a numbered sequence of steps. Put each step in its own "
    "paragraph, separated from the next by a blank line (a double newline \"\\n\\n\").\n\n"
    "Begin each step with its index in curly braces. If the step follows from, uses, or "
    "builds on earlier steps, finish the step with the indices of those "
    "steps in square brackets, after all of the step's text:\n\n"
    "{0} the first step, which nothing precedes\n\n"
    "{1} a step that starts a separate idea and uses nothing earlier\n\n"
    "{2} a step that follows from steps 0 and 1 [0,1]\n\n"
    "{3} a step that follows only from step 1 [1]\n\n"
    "Follow these rules exactly so the markers can be parsed:\n"
    "- The bracket list is the very last thing in the step, with nothing after it.\n"
    + _DEP_RULES
)

VERSIONS = {
    "v1": {"step": STEP_SEP, "numeric": V1_NUMERIC_FMT, "mcq": V1_MCQ_FMT,
           "lcb": V1_LCB_ONLY_CODE},
    "v2": {"step": STEP_SEP, "numeric": V2_NUMERIC_FMT, "mcq": V2_MCQ_FMT,
           "lcb": V2_LCB_ONLY_CODE},
    "v3": {"step": V3_STEP_FMT, "numeric": V1_NUMERIC_FMT, "mcq": V1_MCQ_FMT,
           "lcb": V1_LCB_ONLY_CODE},
    "v4": {"step": V4_STEP_FMT, "numeric": V1_NUMERIC_FMT, "mcq": V1_MCQ_FMT,
           "lcb": V1_LCB_ONLY_CODE},
}

# Mirrors lcb_runner/prompts/code_generation.py so the official extractor works.
LCB_WITH_STARTER = (
    "You will use the following starter code to write the solution to the problem and "
    "enclose your code within delimiters."
)
LCB_WITHOUT_STARTER = (
    "Read the inputs from stdin solve the problem and write the answer to stdout (do not "
    "directly test on the sample inputs). Enclose your code within delimiters as follows. "
    "Ensure that when the python program runs, it reads the inputs, runs the algorithm and "
    "writes output to STDOUT."
)


def build_prompt(rec: dict, version: str = PROMPT_VERSION) -> str:
    fmts = VERSIONS[version]
    step = fmts["step"]
    grader = rec["meta"]["grader"]
    if grader == "codegen":
        starter = rec["meta"].get("starter_code") or ""
        body = f"### Question:\n{rec['question']}\n\n"
        if starter.strip():
            body += f"### Format: {LCB_WITH_STARTER}\n```python\n{starter}\n```\n\n"
        else:
            body += f"### Format: {LCB_WITHOUT_STARTER}\n```python\n# YOUR CODE HERE\n```\n\n"
        body += (
            "You are an expert Python programmer. Write a correct Python program that "
            f"matches the specification and passes all tests.\n\n{step}\n\n"
        )
        if fmts["lcb"]:
            body += f"{fmts['lcb']}\n\n"
        body += "### Answer: (use the provided format with backticks)\n"
        return body

    fmt = fmts["mcq"] if grader == "mcq" else fmts["numeric"]
    return f"{rec['question'].strip()}\n\n{step}\n\n{fmt}"


# The thinking block is where these models are least steerable: with the instruction alone
# they ignored the format completely (0 of 2,206 steps carried a marker across a 48-trace
# sample). Seeding the assistant turn with the first index marker fixes that -- the models
# continue the pattern once it is established. generate.py prepends this to the recorded
# response so the stored trace is complete.
PREFILL = {"v3": "{0} ", "v4": "{0} "}

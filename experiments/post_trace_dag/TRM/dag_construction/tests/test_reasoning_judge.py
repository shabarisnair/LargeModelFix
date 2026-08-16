"""Parsing when the judge is a reasoning model that emits a <think> block.

The failure this guards against: a reasoning judge weighs options aloud, writing markers
it later rejects. Since ACTION_RE takes the first match in the string, parsing the raw
output would return a discarded hypothesis rather than the model's conclusion.
"""

from trm_dag.components import parse_action_previous, strip_reasoning


def test_strip_reasoning_keeps_only_post_think_text():
    assert strip_reasoning("reasoning here</think>\nanswer") == "\nanswer"


def test_text_without_think_is_untouched():
    """Non-reasoning judges (e.g. Qwen3 with thinking disabled) must be unaffected."""
    assert strip_reasoning("plain answer") == "plain answer"


def test_last_think_close_wins():
    assert strip_reasoning("a</think>b</think>final") == "final"


def test_discarded_marker_inside_reasoning_is_ignored():
    out = (
        "Hmm, at first glance this looks like <|action|>merge because it mentions two\n"
        "branches. But actually it only refers to the main path, so merge is wrong.\n"
        "</think>\n"
        "s7 revisits the earlier setup to re-check the arithmetic.\n"
        "<|action|>backtrack\n"
        "<|previous|>3\n"
    )
    block, errors = parse_action_previous(out)
    assert errors == []
    assert block is not None
    # without strip_reasoning this would have been "merge"
    assert block.action == "backtrack"
    assert block.prev_list == [3]
    assert "revisits the earlier setup" in block.explanation


def test_explanation_not_taken_from_reasoning():
    out = (
        "Let me think about what s2 is doing in relation to s1.\n"
        "</think>\n"
        "s2 continues the calculation started in s1.\n"
        "<|action|>continue\n"
    )
    block, _ = parse_action_previous(out)
    assert block is not None
    assert block.action == "continue"
    assert block.explanation.startswith("s2 continues")


def test_truncated_reasoning_yields_no_action():
    """A judge that ran out of budget mid-thought has no answer to parse."""
    block, errors = parse_action_previous("still deliberating about whether this is a")
    assert block is None
    assert errors

"""Tests for the extraction and execution harness.

No model calls and no network: every case uses a hand-written "model output" so the
behaviour under test is the harness itself, not the model. That matters because the
whole point of this repo is that the harness, not the model, moves the score.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from core import (
    STRATEGIES,
    Problem,
    extract_fenced,
    extract_fenced_all,
    extract_prompt_plus_body,
    extract_raw,
    extract_smart,
    run_tests,
)

PROMPT = "def add(a, b):\n"
TEST = "def check(candidate):\n    assert candidate(2, 3) == 5\n    assert candidate(-1, 1) == 0\n"
PROBLEM = Problem("test/0", PROMPT, TEST, "add")

FENCED = "Here you go:\n```python\ndef add(a, b):\n    return a + b\n```\nHope that helps!"
BARE = "def add(a, b):\n    return a + b\n"
CONTINUATION = "    return a + b\n"


# --- extraction ------------------------------------------------------------------------


def test_raw_returns_output_untouched():
    assert extract_raw(PROMPT, FENCED) == FENCED


def test_first_fence_pulls_the_block():
    assert extract_fenced(PROMPT, FENCED).strip() == "def add(a, b):\n    return a + b"


def test_fence_falls_back_to_raw_when_absent():
    assert extract_fenced(PROMPT, BARE) == BARE


def test_all_fences_joins_multiple_blocks():
    two = "```python\nimport math\n```\nand\n```python\ndef add(a, b):\n    return a + b\n```"
    joined = extract_fenced_all(PROMPT, two)
    assert "import math" in joined
    assert "def add" in joined


def test_prompt_plus_body_reassembles_a_continuation():
    assert "def add" in extract_prompt_plus_body(PROMPT, CONTINUATION)


def test_smart_handles_a_continuation_without_a_def():
    """A bare body has no `def`, so smart must prepend the prompt to make it valid."""
    assert "def add" in extract_smart(PROMPT, CONTINUATION)


def test_smart_prefers_the_fence_when_there_is_one():
    assert extract_smart(PROMPT, FENCED).count("def add") == 1


# --- execution --------------------------------------------------------------------------


def test_correct_code_passes():
    ok, why = run_tests(BARE, PROBLEM)
    assert ok, why


def test_wrong_code_fails():
    ok, _ = run_tests("def add(a, b):\n    return a * b\n", PROBLEM)
    assert not ok


def test_entry_point_is_passed_as_a_function_not_a_string():
    """Regression test for a real bug in this harness.

    The runner template interpolated `repr(entry_point)`, so `check` received the
    string "add" instead of the function. Every test failed with "'str' object is not
    callable" no matter how correct the code was - the harness reported 0% for working
    models. Exactly the failure mode this repo exists to measure.
    """
    ok, why = run_tests(BARE, PROBLEM)
    assert ok, f"entry point regression: {why}"
    assert "not callable" not in why


def test_fenced_output_is_a_syntax_error_when_taken_raw():
    """Why `raw` scores zero: backticks are not Python."""
    ok, why = run_tests(FENCED, PROBLEM)
    assert not ok
    assert "SyntaxError" in why


def test_timeout_is_enforced():
    ok, why = run_tests("import time\ndef add(a, b):\n    time.sleep(30)\n", PROBLEM, timeout=3)
    assert not ok
    assert why == "timeout"


def test_exception_in_candidate_is_caught_not_raised():
    ok, _ = run_tests("def add(a, b):\n    raise RuntimeError('boom')\n", PROBLEM)
    assert not ok


# --- the claim the repo makes ------------------------------------------------------------


@pytest.mark.parametrize("name", list(STRATEGIES))
def test_every_strategy_is_callable_and_returns_text(name):
    assert isinstance(STRATEGIES[name](PROMPT, FENCED), str)


def test_strategies_disagree_on_identical_output():
    """The headline, in miniature: same generation, different verdicts."""
    verdicts = {name: run_tests(fn(PROMPT, FENCED), PROBLEM)[0] for name, fn in STRATEGIES.items()}
    assert any(verdicts.values()), "no strategy passed - fixture is wrong"
    assert not all(verdicts.values()), "all strategies passed - no spread to measure"

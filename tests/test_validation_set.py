"""Regression test: the judge's verdicts must match the hand-labeled answer key.

This is the test that actually protects the 14/14 result — without it, CI
only checks that the graph wires together, not that the judge's scoring
logic still agrees with ground truth after a change.
"""

import json
from pathlib import Path

import pytest

from src.nodes.judge import judge_claim

_ROOT = Path(__file__).resolve().parent.parent
_VALIDATION_SET = _ROOT / "validation_set.json"
_ANSWER_KEY = _ROOT / "validation_set_answer_key.json"


def _load_checkable_claims():
    """Flatten both files into a list of (source_lines, claim, expected) tuples.

    Only checkable claims are included — non-checkable claims have no
    verdict to compare against.
    """
    with open(_VALIDATION_SET) as f:
        validation_set = json.load(f)
    with open(_ANSWER_KEY) as f:
        answer_key = json.load(f)

    cases = []
    for record, labeled_record in zip(validation_set, answer_key):
        source_lines = record["source_lines"]
        for claim, labeled_claim in zip(record["claims"], labeled_record["claims"]):
            if not claim["checkable"]:
                continue
            cases.append(
                pytest.param(
                    source_lines,
                    claim["claim"],
                    labeled_claim["verdict"],
                    id=claim["claim"][:60],
                )
            )
    return cases


@pytest.mark.parametrize(
    "source_lines, claim_text, expected_verdict", _load_checkable_claims()
)
def test_judge_matches_hand_labeled_verdict(source_lines, claim_text, expected_verdict):
    """Each checkable claim's judged verdict must match the hand-labeled answer key.

    This is a live API test — it calls the real judge, not a mock. Slower
    and costs tokens, but it's the only way to actually catch a scoring
    regression rather than a wiring regression.
    """
    result = judge_claim(claim_text, source_lines)
    assert result["verdict"] == expected_verdict, (
        f"claim: {claim_text!r}\n"
        f"expected: {expected_verdict}, got: {result['verdict']}\n"
        f"judge's explanation: {result.get('explanation')}"
    )

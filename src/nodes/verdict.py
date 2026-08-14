"""verdict — tally the per-claim judgements into a single score.

Reads `state["claims"]` and `state["verdicts"]` (parallel lists — see
judge.py) and aggregates them into a hallucination rate plus per-claim
receipts, so any number reported can be traced back to the claim and the
quoted line behind it.
"""

from src.state import EvalState


def verdict(state: EvalState) -> dict:
    """Tally claims/verdicts into a final report.

    hallucination_rate = unsupported / checkable (None if no checkable claims).
    """
    claims = state["claims"]
    verdicts = state["verdicts"]

    checkable_count = sum(1 for c in claims if c["checkable"])
    not_checkable_count = len(claims) - checkable_count
    supported_count = sum(1 for v in verdicts if v and v["verdict"] == "supported")
    unsupported_count = sum(1 for v in verdicts if v and v["verdict"] == "unsupported")

    hallucination_rate = (
        unsupported_count / checkable_count if checkable_count else None
    )

    findings = [
        {
            "claim": claim["claim"],
            "checkable": claim["checkable"],
            "verdict": v["verdict"] if v else None,
            "quote": v["quote"] if v else None,
            "explanation": v["explanation"] if v else None,
        }
        for claim, v in zip(claims, verdicts)
    ]

    return {
        "hallucination_rate": hallucination_rate,
        "total_claims": len(claims),
        "checkable_claims": checkable_count,
        "not_checkable_claims": not_checkable_count,
        "supported_claims": supported_count,
        "unsupported_claims": unsupported_count,
        "findings": findings,
    }

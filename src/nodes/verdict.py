"""verdict — tally the per-claim judgements into a single score.

STUB. The scoring logic is deliberately unwritten; see TODO(human) below.

Intended contract
-----------------
Read `state["verdicts"]`, aggregate supported vs unsupported into a
`hallucination_rate`, and keep the per-claim receipts reachable so any number
reported can be traced back to the claim and the quoted line behind it.
"""

from src.state import EvalState


def verdict(state: EvalState) -> dict:
    """Aggregate verdicts into a hallucination rate.

    Returns the shape only, so the graph runs end-to-end while unimplemented.
    """
    # TODO(human): decide the scoring/aggregation.
    #   - What exactly is the denominator when there are zero claims?
    #   - Are all claims weighted equally?
    #   - What else, if anything, does this node surface alongside the rate?
    return {"hallucination_rate": None}

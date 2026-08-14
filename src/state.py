"""Shared state passed between the graph's nodes.

LangGraph threads a single dict through every node; each node returns a partial
update that gets merged in. Keeping the whole contract in one TypedDict means
the pipeline's data flow is readable in one place.
"""

from typing import TypedDict


class EvalState(TypedDict):
    """State for one evaluation run: one source record judged against one answer.

    Fields are populated progressively as the graph runs:
      ingest  -> source_record, answer
      judge   -> claims, verdicts
      verdict -> hallucination_rate, total_claims, checkable_claims,
                 not_checkable_claims, supported_claims, unsupported_claims,
                 findings
    """

    # Ground truth the answer is checked against. Plain text so the judge can
    # cite a supporting *line* rather than a JSON path.
    source_record: str

    # The model-generated output under evaluation.
    answer: str

    # Atomic claims extracted from `answer`: {"claim": str, "checkable": bool}.
    claims: list

    # One verdict per claim, same order as `claims`; None where the claim
    # wasn't checkable. Each verdict: {"verdict", "quote", "explanation"}.
    verdicts: list

    # None until the verdict node has run, so "not scored yet" is
    # distinguishable from "scored 0.0".
    hallucination_rate: float | None

    # Tallies from the verdict node, alongside hallucination_rate.
    total_claims: int
    checkable_claims: int
    not_checkable_claims: int
    supported_claims: int
    unsupported_claims: int

    # Per-claim receipts: {"claim", "checkable", "verdict", "quote", "explanation"}.
    findings: list

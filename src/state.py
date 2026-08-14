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
      verdict -> hallucination_rate
    """

    # Ground truth the answer is checked against. Plain text so the judge can
    # cite a supporting *line* rather than a JSON path.
    source_record: str

    # The model-generated output under evaluation.
    answer: str

    # Atomic claims extracted from `answer`. Shape is the judge's call.
    claims: list

    # One judgement per claim (supported / unsupported + its receipt).
    verdicts: list

    # None until the verdict node has run, so "not scored yet" is
    # distinguishable from "scored 0.0".
    hallucination_rate: float | None

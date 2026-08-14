"""Skeleton test: the graph runs end-to-end and returns a verdict-shaped state.

These assert *shape*, not correctness — the judge is still a stub, so there is
no scoring behaviour to pin down yet. The point is that wiring regressions fail
loudly here before any eval logic gets written on top.
"""

import json

import pytest

from src.graph import build_graph, run
from src.nodes.ingest import ingest

SOURCE = "Patient reports a persistent cough.\nNo fever recorded."
ANSWER = "The patient has a cough and a fever."

FHIR_BUNDLE = {
    "resourceType": "Bundle",
    "entry": [
        {
            "resource": {
                "resourceType": "Patient",
                "name": [{"given": ["Jane"], "family": "Doe"}],
                "gender": "female",
                "birthDate": "1974-03-12",
            }
        },
        {
            "resource": {
                "resourceType": "Condition",
                "code": {"text": "Type 2 Diabetes Mellitus"},
                "onsetDateTime": "2015-04-12T08:00:00-05:00",
                "clinicalStatus": {"coding": [{"code": "active"}]},
            }
        },
        {
            # Administrative resource type: should be dropped, not rendered.
            "resource": {
                "resourceType": "Claim",
                "id": "irrelevant-billing-record",
            }
        },
    ],
}


def test_graph_returns_verdict_shape():
    """A run populates every field of EvalState."""
    state = run(source_record=SOURCE, answer=ANSWER)

    for key in ("source_record", "answer", "claims", "verdicts", "hallucination_rate"):
        assert key in state, f"final state is missing `{key}`"

    assert isinstance(state["claims"], list)
    assert isinstance(state["verdicts"], list)
    assert state["hallucination_rate"] is None or isinstance(
        state["hallucination_rate"], float
    )


def test_ingest_passes_inputs_through():
    """Text handed in is the text the judge sees."""
    state = run(source_record=SOURCE, answer=ANSWER)

    assert state["source_record"] == SOURCE
    assert state["answer"] == ANSWER


def test_ingest_reads_a_record_from_disk(tmp_path):
    """A path argument is resolved to file contents, so runs can be driven from data/."""
    record = tmp_path / "record.txt"
    record.write_text(SOURCE, encoding="utf-8")

    state = run(source_record=str(record), answer=ANSWER)

    assert state["source_record"] == SOURCE


@pytest.mark.parametrize("missing", ["source_record", "answer"])
def test_missing_input_is_rejected(missing):
    """Ingest fails fast rather than handing the judge an empty document."""
    inputs = {"source_record": SOURCE, "answer": ANSWER}
    inputs[missing] = ""

    with pytest.raises(ValueError):
        build_graph().invoke(inputs)


def test_ingest_flattens_a_fhir_bundle_into_citable_lines():
    """A FHIR Bundle is rendered into flat "Resource.field: value" lines."""
    result = ingest({"source_record": json.dumps(FHIR_BUNDLE, indent=2), "answer": ANSWER})
    lines = result["source_record"].splitlines()

    assert "Patient.birthDate: 1974-03-12" in lines
    assert "Condition.code: Type 2 Diabetes Mellitus" in lines
    # Administrative resource types (Claim, ExplanationOfBenefit, ...) are noise
    # relative to a clinical summary, so they're dropped rather than rendered.
    assert not any("irrelevant-billing-record" in line for line in lines)


def test_ingest_leaves_non_fhir_text_untouched():
    """Plain-text records (and non-Bundle JSON) pass through unchanged."""
    result = ingest({"source_record": SOURCE, "answer": ANSWER})
    assert result["source_record"] == SOURCE

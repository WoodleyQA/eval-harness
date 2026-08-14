"""Run the eval graph end-to-end on one sample Synthea record.

Usage:
    .venv/bin/python scripts/run_example.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.graph import run  # noqa: E402

# A model-generated summary of the patient. Deliberately mixes claims that
# should be supported, one that's a plausible-sounding fabrication (this
# patient's conditions don't include diabetes), and one unverifiable opinion,
# so the report below shows all three verdict outcomes.
ANSWER = (
    "The patient is male with a history of essential hypertension, first "
    "diagnosed in 1997. He is also managing type 2 diabetes with metformin. "
    "Overall he appears to be in reasonably good health for his age."
)

REPORT_FIELDS = [
    "hallucination_rate",
    "total_claims",
    "checkable_claims",
    "not_checkable_claims",
    "supported_claims",
    "unsupported_claims",
    "findings",
]


def _first_patient_record() -> Path:
    """The first Synthea patient bundle in data/fhir/, alphabetically.

    Excludes the hospital/practitioner reference files Synthea also emits —
    those aren't patient records the judge can be run against.
    """
    candidates = sorted(
        p
        for p in (ROOT / "data" / "fhir").glob("*.json")
        if "Information" not in p.stem
    )
    if not candidates:
        raise FileNotFoundError(
            "No patient records in data/fhir/ — see README for how to generate them."
        )
    return candidates[0]


def main() -> None:
    record_path = _first_patient_record()
    print(f"Source record: {record_path.name}")
    print(f"Answer under evaluation: {ANSWER}\n")

    state = run(source_record=str(record_path), answer=ANSWER)

    report = {field: state[field] for field in REPORT_FIELDS}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

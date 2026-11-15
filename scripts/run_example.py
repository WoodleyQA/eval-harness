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


def _first_patient_record() -> Path | None:
    """The first Synthea patient bundle in data/fhir/, alphabetically, if any.

    Excludes the hospital/practitioner reference files Synthea also emits —
    those aren't patient records the judge can be run against.
    """
    candidates = sorted(
        p
        for p in (ROOT / "data" / "fhir").glob("*.json")
        if "Information" not in p.stem
    )
    return candidates[0] if candidates else None


def _bundled_record() -> tuple[str, str]:
    """The first record of the committed validation set, as (label, source text).

    data/ is gitignored (generated Synthea output is ~47MB), so a fresh clone
    has no records. The validation set already carries four flattened synthetic
    records, which is enough to run the example with no extra setup.
    """
    with open(ROOT / "validation_set.json", encoding="utf-8") as f:
        record = json.load(f)[0]
    return "validation_set.json[0] (bundled)", record["source_lines"]


def main() -> None:
    record_path = _first_patient_record()
    if record_path is not None:
        label, source = record_path.name, str(record_path)
    else:
        label, source = _bundled_record()
    print(f"Source record: {label}")
    print(f"Answer under evaluation: {ANSWER}\n")

    state = run(source_record=source, answer=ANSWER)

    report = {field: state[field] for field in REPORT_FIELDS}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

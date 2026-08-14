"""Build a hand-labeling validation set for the judge.

For each of a few sample records, run a made-up model "answer" (mixing
correct, subtly wrong, and fabricated claims) through extract_claims() and
judge_claim(). Writes two files:

  validation_set.json            — checkable claims + their source records,
                                    no verdicts. For a human to hand-label.
  validation_set_answer_key.json — the same claims, with the judge's
                                    verdicts, to compare against those labels.

This is the input to the credibility check described in the README: hand-
label validation_set.json, then diff the labels against the answer key to
report agreement.

Usage:
    .venv/bin/python scripts/build_validation_set.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.nodes.ingest import ingest  # noqa: E402
from src.nodes.judge import extract_claims, judge_claim  # noqa: E402

# Each answer mixes three kinds of claims against real facts in the record:
# correct, subtly wrong (a swapped date or value), and clearly fabricated.
RECORDS = [
    {
        "path": "data/fhir/Andrés117_Olivo261_5c9f20d5-8361-b331-9267-5303ca5b136a.json",
        "answer": (
            "The patient is male. He was diagnosed with essential "
            "hypertension in 1999. He also has a history of atrial "
            "fibrillation."
        ),
    },
    {
        "path": "data/fhir/Ashely524_Maybelle917_Weimann465_d545798e-09a4-ef89-abc5-9f62dc5a5095.json",
        "answer": (
            "The patient is female. She was diagnosed with childhood asthma "
            "in 2001. She has type 1 diabetes."
        ),
    },
    {
        "path": "data/fhir/Iva908_Katerine813_Harvey63_c597378a-02fb-d690-115b-196121219178.json",
        "answer": (
            "The patient has essential hypertension, diagnosed in 1978. "
            "She has a pacemaker implanted for her heart condition."
        ),
    },
    {
        "path": "data/fhir/Miguel815_Bashirian201_5393ea7f-1fea-4064-9df4-460a2f662d07.json",
        "answer": (
            "The patient is male and has a BMI in the healthy range. He "
            "underwent hip replacement surgery in 2018."
        ),
    },
]


def build() -> tuple[list[dict], list[dict]]:
    """Run every record through the judge, returning (validation_set, answer_key)."""
    validation_set = []
    answer_key = []

    for record in RECORDS:
        state = ingest({"source_record": record["path"], "answer": record["answer"]})
        source_lines = state["source_record"]

        claims = extract_claims(record["answer"])
        checkable = [c for c in claims if c["checkable"]]

        judged = [
            {"claim": c["claim"], "checkable": True, **judge_claim(c["claim"], source_lines)}
            for c in checkable
        ]

        validation_set.append(
            {
                "source_record": record["path"],
                "source_lines": source_lines,
                "claims": [{"claim": c["claim"], "checkable": True} for c in checkable],
            }
        )
        answer_key.append(
            {
                "source_record": record["path"],
                "source_lines": source_lines,
                "claims": judged,
            }
        )

    return validation_set, answer_key


def main() -> None:
    validation_set, answer_key = build()

    total_checkable = sum(len(entry["claims"]) for entry in validation_set)
    print(f"{total_checkable} checkable claims across {len(RECORDS)} records.")

    (ROOT / "validation_set.json").write_text(
        json.dumps(validation_set, indent=2), encoding="utf-8"
    )
    (ROOT / "validation_set_answer_key.json").write_text(
        json.dumps(answer_key, indent=2), encoding="utf-8"
    )
    print("Wrote validation_set.json and validation_set_answer_key.json")


if __name__ == "__main__":
    main()

"""ingest — load a source record and a model answer into state.

Pure plumbing: no model calls, no judgement. Its only job is to hand the judge
two blocks of text, so that everything downstream can assume `source_record`
and `answer` are already-resolved strings.
"""

import json
from pathlib import Path

from src.state import EvalState


def _resolve(value: str) -> str:
    """Return `value` as text, reading it from disk if it names a real file.

    Accepting either a path or a literal lets the graph be driven from files in
    `data/` and from inline strings in tests without a second entry point.
    """
    if not isinstance(value, str):
        raise TypeError(f"expected str, got {type(value).__name__}")

    candidate = Path(value)
    # A literal record is multi-line and far longer than any real path, so the
    # length guard keeps us from stat-ing an entire document.
    if len(value) < 4096 and "\n" not in value and candidate.is_file():
        return candidate.read_text(encoding="utf-8")

    return value


def _date(iso_datetime: str | None) -> str | None:
    """The date portion of a FHIR dateTime/date string."""
    return iso_datetime[:10] if iso_datetime else None


def _codeable_text(concept: dict | None) -> str | None:
    """Human-readable text for a FHIR CodeableConcept.

    Prefers the concept's own `.text`; falls back to the first coding's
    `.display`, since `.text` is optional but Synthea always populates one or
    the other.
    """
    if not concept:
        return None
    if concept.get("text"):
        return concept["text"]
    for coding in concept.get("coding", []):
        if coding.get("display"):
            return coding["display"]
    return None


def _quantity_text(quantity: dict | None) -> str | None:
    if not quantity or quantity.get("value") is None:
        return None
    unit = quantity.get("unit", "")
    return f"{quantity['value']} {unit}".strip()


def _observation_value(resource: dict) -> str | None:
    """An Observation's value, wherever FHIR's value[x] polymorphism put it.

    Panel observations (e.g. blood pressure) carry no top-level value at all —
    their readings live in `component` instead — so that case is handled
    separately.
    """
    if "valueQuantity" in resource:
        return _quantity_text(resource["valueQuantity"])
    if "valueCodeableConcept" in resource:
        return _codeable_text(resource["valueCodeableConcept"])
    if "valueString" in resource:
        return resource["valueString"]
    if "valueBoolean" in resource:
        return str(resource["valueBoolean"])

    components = []
    for component in resource.get("component", []):
        label = _codeable_text(component.get("code"))
        value = _quantity_text(component.get("valueQuantity")) or _codeable_text(
            component.get("valueCodeableConcept")
        )
        if label and value:
            components.append(f"{label} {value}")
    return "; ".join(components) if components else None


def _patient_lines(resource: dict) -> list[str]:
    lines = []

    names = resource.get("name", [])
    if names:
        full_name = " ".join([*names[0].get("given", []), names[0].get("family", "")]).strip()
        if full_name:
            lines.append(f"Patient.name: {full_name}")

    if resource.get("gender"):
        lines.append(f"Patient.gender: {resource['gender']}")

    if resource.get("birthDate"):
        lines.append(f"Patient.birthDate: {resource['birthDate']}")

    marital_status = _codeable_text(resource.get("maritalStatus"))
    if marital_status:
        lines.append(f"Patient.maritalStatus: {marital_status}")

    addresses = resource.get("address", [])
    if addresses:
        address = addresses[0]
        parts = [
            ", ".join(address.get("line", [])),
            ", ".join(p for p in [address.get("city"), address.get("state")] if p),
            address.get("postalCode"),
        ]
        address_text = ", ".join(p for p in parts if p)
        if address_text:
            lines.append(f"Patient.address: {address_text}")

    deceased_date = _date(resource.get("deceasedDateTime"))
    if deceased_date:
        lines.append(f"Patient.deceasedDate: {deceased_date}")

    return lines


def _condition_lines(resource: dict) -> list[str]:
    lines = []

    code = _codeable_text(resource.get("code"))
    if code:
        lines.append(f"Condition.code: {code}")

    onset_date = _date(resource.get("onsetDateTime"))
    if onset_date:
        lines.append(f"Condition.onsetDate: {onset_date}")

    clinical_status = next(
        iter(resource.get("clinicalStatus", {}).get("coding", [])), {}
    ).get("code")
    if clinical_status:
        lines.append(f"Condition.clinicalStatus: {clinical_status}")

    return lines


def _observation_lines(resource: dict) -> list[str]:
    code = _codeable_text(resource.get("code"))
    value = _observation_value(resource)
    if not code or not value:
        return []

    line = f"Observation.{code}: {value}"
    date = _date(resource.get("effectiveDateTime"))
    if date:
        line += f" ({date})"
    return [line]


def _procedure_lines(resource: dict) -> list[str]:
    lines = []

    code = _codeable_text(resource.get("code"))
    if code:
        lines.append(f"Procedure.code: {code}")

    date = _date(resource.get("performedPeriod", {}).get("start")) or _date(
        resource.get("performedDateTime")
    )
    if date:
        lines.append(f"Procedure.date: {date}")

    return lines


def _medication_request_lines(resource: dict) -> list[str]:
    lines = []

    medication = _codeable_text(resource.get("medicationCodeableConcept"))
    if medication:
        lines.append(f"MedicationRequest.medication: {medication}")

    authored_date = _date(resource.get("authoredOn"))
    if authored_date:
        lines.append(f"MedicationRequest.authoredOn: {authored_date}")

    if resource.get("status"):
        lines.append(f"MedicationRequest.status: {resource['status']}")

    return lines


def _immunization_lines(resource: dict) -> list[str]:
    lines = []

    vaccine = _codeable_text(resource.get("vaccineCode"))
    if vaccine:
        lines.append(f"Immunization.vaccine: {vaccine}")

    date = _date(resource.get("occurrenceDateTime"))
    if date:
        lines.append(f"Immunization.date: {date}")

    return lines


def _allergy_intolerance_lines(resource: dict) -> list[str]:
    lines = []

    code = _codeable_text(resource.get("code"))
    if code:
        lines.append(f"AllergyIntolerance.code: {code}")

    onset_date = _date(resource.get("onsetDateTime") or resource.get("recordedDate"))
    if onset_date:
        lines.append(f"AllergyIntolerance.onsetDate: {onset_date}")

    return lines


# Resource types rendered into lines. Limited to ones that carry a fact a
# clinical summary might actually assert about the patient — administrative
# and billing resources (Claim, ExplanationOfBenefit, Encounter,
# DocumentReference, Provenance, ...) describe the paperwork around a visit,
# not the patient, so they're dropped rather than rendered as noise.
_RESOURCE_RENDERERS = {
    "Patient": _patient_lines,
    "Condition": _condition_lines,
    "Observation": _observation_lines,
    "Procedure": _procedure_lines,
    "MedicationRequest": _medication_request_lines,
    "Immunization": _immunization_lines,
    "AllergyIntolerance": _allergy_intolerance_lines,
}


def _flatten_fhir_bundle(bundle: dict) -> str:
    """Render a FHIR Bundle into flat "Resource.field: value" lines.

    Each line is a self-contained fact, so the judge can quote one verbatim as
    a supporting line rather than pointing at a JSON path.
    """
    lines: list[str] = []
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        renderer = _RESOURCE_RENDERERS.get(resource.get("resourceType"))
        if renderer:
            lines.extend(renderer(resource))
    return "\n".join(lines)


def _render_source(text: str) -> str:
    """Render `text` into citable lines if it's a FHIR Bundle; else pass it through.

    Non-FHIR sources (plain-text records, test fixtures) are already the kind
    of line-oriented text the judge can cite, so they're left untouched.
    """
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return text

    if isinstance(parsed, dict) and parsed.get("resourceType") == "Bundle":
        return _flatten_fhir_bundle(parsed)

    return text


def ingest(state: EvalState) -> dict:
    """Normalise the run's inputs to text.

    Expects `source_record` and `answer` in the initial state, each a path to a
    file or the text itself.
    """
    source_record = state.get("source_record")
    answer = state.get("answer")

    if not source_record:
        raise ValueError("ingest requires a non-empty `source_record`")
    if not answer:
        raise ValueError("ingest requires a non-empty `answer`")

    return {
        "source_record": _render_source(_resolve(source_record)),
        "answer": _resolve(answer),
    }

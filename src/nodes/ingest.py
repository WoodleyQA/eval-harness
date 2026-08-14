"""ingest — load a source record and a model answer into state.

Pure plumbing: no model calls, no judgement. Its only job is to hand the judge
two blocks of text, so that everything downstream can assume `source_record`
and `answer` are already-resolved strings.
"""

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

    # TODO(human): Synthea emits FHIR JSON / CSV, but the judge's contract is to
    # cite a supporting *line* of the source. Deciding how a record is rendered
    # into citable lines is a judge-design decision, so it is left here rather
    # than guessed — right now the file is passed through verbatim.
    return {
        "source_record": _resolve(source_record),
        "answer": _resolve(answer),
    }

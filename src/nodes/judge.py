"""judge — extract atomic claims from the answer and check each against the source.

Two steps, both inside this node:

1. **Extract** (`extract_claims`). Break the answer into atomic claims, each
   marked `checkable` or not.
2. **Check** (`judge_claim`). For every *checkable* claim, ask the model to
   verify it against the source record. A `supported` verdict must carry a
   quoted supporting line; `unsupported` must explain why not. That quote is
   the receipt — it's what makes a verdict auditable rather than a vibe.

Claims marked `checkable: false` are extracted (so they aren't silently
dropped) but never sent to `judge_claim` — there's nothing in the source that
could confirm an opinion or a hedge, so their slot in `verdicts` is `None`,
parallel to `claims`.
"""

import json

import anthropic
from dotenv import load_dotenv

from src.state import EvalState

load_dotenv()

_MODEL = "claude-sonnet-5"

_client = anthropic.Anthropic()

_EXTRACT_CLAIMS_PROMPT = """You are extracting atomic factual claims from a piece of text.

Break the following answer into a list of atomic claims. An atomic claim is
a single, independently checkable fact — if a sentence contains two facts,
split it into two claims.

Rules:
- Each claim must be a complete, standalone statement. Resolve pronouns and
  references back to earlier parts of the answer (e.g. "he was diagnosed in
  2019" becomes "the patient was diagnosed in 2019").
- Mark each claim as checkable: true or checkable: false.
  - checkable: true — a specific, verifiable fact (a date, a diagnosis, a
    value, an event).
  - checkable: false — an opinion, hedge, or vague statement that can't be
    checked against a source record (e.g. "the patient seems healthy
    overall"). Still extract it, just mark it false — do not drop it.
- Output ONLY a JSON array of objects, no other text. Each object:
  {{"claim": "<the claim text>", "checkable": true|false}}

Answer to extract claims from:
{answer}
"""

_JUDGE_CLAIM_PROMPT = """You are checking whether a single factual claim is supported by a source record.

Source record (flat key-value facts):
{source_lines}

Claim to check:
{claim}

Task:
- Determine if this claim is fully supported by the source record.
- A claim is "supported" only if you can point to a specific line in the
  source that confirms it exactly. Partial matches, close-but-not-exact
  values, or claims the record simply doesn't mention all count as
  "unsupported."
- If supported, quote the exact source line that supports it.
- If unsupported, explain specifically why — e.g. "not mentioned in the
  record," or "the record states a different value: <the actual line>."
  This explanation matters even more than the verdict itself, so be precise.

Output ONLY a JSON object, no other text:
{{"verdict": "supported"|"unsupported", "quote": "<exact source line, or null if unsupported>", "explanation": "<your reasoning>"}}
"""


def _response_text(response: anthropic.types.Message) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


def _parse_json_values(text: str) -> list:
    """Decode every JSON value in `text`, in order.

    The prompt asks for one JSON array; for short answers the model
    sometimes emits newline-separated objects instead (JSONL, no wrapping
    `[...]`). Decoding every value rather than just the first means a
    two-claim extraction like that isn't silently truncated to one claim.
    """
    decoder = json.JSONDecoder()
    values = []
    index = 0
    length = len(text)
    while index < length:
        while index < length and text[index].isspace():
            index += 1
        if index >= length:
            break
        try:
            value, end = decoder.raw_decode(text, index)
        except json.JSONDecodeError:
            # Trailing prose after at least one good value (e.g. a stray
            # comment) is ignorable; no valid value at all is a real error.
            if values:
                break
            raise
        values.append(value)
        index = end
    return values


def _parse_json_response(text: str):
    # The prompt says "output ONLY JSON", but models occasionally wrap it in a
    # markdown fence anyway — strip one off if present before decoding.
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.partition("\n")[2] if "\n" in text else text

    values = _parse_json_values(text.strip())
    # A single JSON array or object decodes to one value — return it as-is.
    # Multiple space/newline-separated values (JSONL) collapse into a list.
    return values[0] if len(values) == 1 else values


def extract_claims(answer: str) -> list[dict]:
    """Extract atomic claims from `answer`.

    Returns a list of `{"claim": str, "checkable": bool}` objects in the
    order the model produced them.
    """
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        response = _client.messages.create(
            model=_MODEL,
            max_tokens=8192,
            thinking={"type": "adaptive"},
            messages=[
                {
                    "role": "user",
                    "content": _EXTRACT_CLAIMS_PROMPT.format(answer=answer),
                }
            ],
        )
        result = _parse_json_response(_response_text(response))
        # The prompt asks for a JSON array; occasionally the model instead
        # returns a single bare object (as if there were only one claim).
        # That's a malformed response, not a one-claim answer, so retry
        # rather than silently dropping every claim after the first.
        if isinstance(result, list):
            return result
        if attempt < max_attempts:
            continue
        raise ValueError(
            f"extract_claims: expected a JSON array after {max_attempts} attempts, "
            f"got {type(result).__name__}: {result!r}"
        )


def judge_claim(claim: str, source_lines: str) -> dict:
    """Check one checkable `claim` against `source_lines`.

    Returns `{"verdict": "supported" | "unsupported", "quote": str | None,
    "explanation": str}`.
    """
    response = _client.messages.create(
        model=_MODEL,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        messages=[
            {
                "role": "user",
                "content": _JUDGE_CLAIM_PROMPT.format(
                    source_lines=source_lines, claim=claim
                ),
            }
        ],
    )
    return _parse_json_response(_response_text(response))


def judge(state: EvalState) -> dict:
    """Judge the answer's claims against the source record.

    Runs `extract_claims` once, then `judge_claim` for each checkable claim.
    `verdicts` is parallel to `claims`; an unchecked (non-checkable) claim's
    slot is `None`.
    """
    claims = extract_claims(state["answer"])
    verdicts = [
        judge_claim(claim["claim"], state["source_record"]) if claim["checkable"] else None
        for claim in claims
    ]
    return {"claims": claims, "verdicts": verdicts}

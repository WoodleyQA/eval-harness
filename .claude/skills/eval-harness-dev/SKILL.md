---
name: eval-harness-dev
description: Working context for extending the eval-harness project (LangGraph-based LLM hallucination judge, grounds model output against a source-of-truth record). Use whenever modifying src/nodes/*.py, adding new judge/verdict logic, extending to new claim types, or reasoning about the ingest→judge→verdict pipeline in ~/eval-harness.
---

# eval-harness — dev context

## What this is
A judge, not a generator. Given a source-of-truth record and a model-produced
answer about it, extracts the answer into atomic claims and checks each claim
against the record. Reports a hallucination rate with per-claim citations.
No Playwright, no browser tests — this project doesn't touch test execution,
it touches claim verification.

v1 shipped and validated (Aug 2026): github.com/WoodleyQA/eval-harness.
100% agreement (14/14) between hand-labeled claims and judge verdicts across
4 Synthea patient records.

## Architecture
Three LangGraph nodes, wired in `src/graph.py`, state carried in
`src/state.py` (`EvalState` TypedDict: source_record, answer, claims,
verdicts, hallucination_rate).

1. **`src/nodes/ingest.py`** — loads source record + answer into state. Plumbing only.
2. **`src/nodes/judge.py`** — two-phase:
   - Extract answer into atomic, standalone-checkable claims (pronouns resolved).
     Unjudgeable statements (opinions/hedges) tagged `checkable: false`, not dropped.
   - Judge each checkable claim: binary `supported`/`unsupported` against the
     source record. Unsupported requires an explanation. Supported requires a
     quoted source line.
3. **`src/nodes/verdict.py`** — tallies checkable claims into a hallucination
   rate (unsupported / checkable), preserving per-claim receipts and the
   not-checkable count separately.

## Locked design decisions (with rationale — don't relitigate without reason)
- **Extraction and judging are separate LLM calls**, not bundled. Chose
  debuggability and interview-explainability over minimizing API calls.
- **checkable:false is tagged, not dropped.** Hiding a skip would understate
  what the hallucination-rate metric actually covers.
- **Verdict is binary (supported/unsupported), no partial_supported bucket.**
  A third bucket makes the judge's own grading criteria fuzzier and harder to
  validate against hand-labeled examples. Nuance on near-misses (right
  diagnosis, wrong date) goes in the required explanation text, not a category.
- **FHIR records are flattened to key-value lines** (e.g. `Patient.birthDate:
  1974-03-12`), not rendered as clinical narrative. Keeps every citation
  traceable to one exact field; avoids a second hallucination-prone rendering
  layer. Narrative rendering is a possible v2, not done.

## Validated worked example (calibration anchor)
See README.md → "Worked Example" section for the full trace: a Synthea
record with a deliberately fabricated claim (type 2 diabetes + metformin,
not in the record) was correctly flagged unsupported, citing the real HbA1c
(5.2%, normal) and real medication list as counter-evidence — not just
"not mentioned." Use this as the reference case when validating any change
to judge.py's prompting or scoring logic: rerun it and confirm the verdict
and citations still hold.

## Deferred (do not build unless explicitly asked)
- Meta-evaluation layer aggregating verdicts across many runs to surface
  systemic hallucination patterns by field/claim-type (extension of
  verdict.py, not a new agent).
- Multi-agent structure (worker/co-worker/boss roles) — noted as a future
  model, not scoped for current build.
- DeepEval wiring — installed, pinned, not integrated.
- Test-vs-requirement application (second use of the same engine, judging
  test coverage against acceptance criteria instead of claims against a
  health record). Same pipeline, different source-of-truth type.

## Conventions
- Functions small and readable; must be explainable line-by-line in an interview.
- Comment why, not what.
- No secrets in code — `.env`, not hardcoded.
- Before changing judge.py or verdict.py scoring logic, rerun the worked
  example above and the 14-claim validation set (`validation_set.json` /
  `validation_set_answer_key.json`) to catch regressions.

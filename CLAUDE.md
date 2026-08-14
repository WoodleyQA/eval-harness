# CLAUDE.md — Project Spec & Guardrails

## What this project is
An **LLM eval harness**, built on **LangGraph**, that grounds a model's output
against a source of truth and reports where the output is unsupported
(hallucinated). Demonstrated on synthetic health records, but described in
domain-neutral terms: *"an eval harness for grounding LLM output against a
source of truth."*

This is a portfolio project. The **design judgment is the asset** — so the
decisions below are locked, and the reasoning-heavy code is intentionally left
for the human to write. Do not make those calls yourself.

## Locked decisions — do not change these
- This is a **judge**, not a test generator. No Playwright, no browser tests.
- **LangGraph is the skeleton; the eval logic runs inside the nodes.** One
  project, not two.
- Core pipeline (three nodes):
  1. **ingest** — load a source record + a model-generated answer into state
  2. **judge** — extract the answer into *atomic claims*, then check each claim
     against the source (must cite a supporting line, or it's `unsupported`)
  3. **verdict** — tally supported vs unsupported into a hallucination rate,
     with per-claim receipts
- First slice = **self-contained hallucination eval**: Synthea record → model
  summary → judge claims against the record. (The test-vs-requirement use case
  comes later as a second application of the same engine — not now.)
- Eval framework to adopt: **DeepEval** (for its faithfulness / hallucination
  metrics, to benchmark our judge against).
- Credibility move (human does this, later): validate the judge against ~10
  hand-labeled claims and report agreement.

## Stack
- Python 3.12 (Homebrew, Intel Mac), venv, `.env` for the Anthropic key
- `langgraph`, `langchain-anthropic`, `anthropic`, `deepeval`
- Synthea for synthetic patient records (Java tool — clone/run to generate
  sample FHIR/CSV output into `data/`)

## ── SCOPE FOR THE OVERNIGHT / HEADLESS RUN ──
You are ONLY allowed to build the **scaffolding**. Do the following:
1. Create the repo structure:
   ```
   ./
     data/            # Synthea output lands here
     src/
       state.py       # EvalState TypedDict
       nodes/
         ingest.py    # implemented: load record + answer into state
         judge.py     # STUB ONLY — see below
         verdict.py   # STUB ONLY — see below
       graph.py       # wire the three nodes into a LangGraph, runnable end-to-end with stubs
     tests/
       test_harness.py  # skeleton: runs the graph on one example, asserts it returns a verdict shape
     README.md          # shell with headings only (see below)
     requirements.txt
     .env.example
   ```
2. Write `state.py`: an `EvalState` TypedDict carrying `source_record`,
   `answer`, `claims: list`, `verdicts: list`, `hallucination_rate: float | None`.
3. Implement **ingest.py** fully (it's plumbing: read a record + answer, populate state).
4. Implement **graph.py** fully: build the LangGraph, wire ingest → judge → verdict,
   make it runnable end-to-end so the graph executes even with stub nodes.
5. Install deps into the venv, freeze `requirements.txt`, write `.env.example`.
6. Set up Synthea: clone it, generate a small batch of sample records into `data/`,
   and note in the README how you ran it.
7. Write the README **shell** — headings and one-line placeholders only:
   Overview, Problem (why false-greens/hallucinations matter), Architecture,
   How the judge works, Validating the judge, Running it. Leave the prose to the human.

## ── DO NOT DO (leave for the human, awake) ──
- **judge.py**: leave as a stub with a clear `# TODO` and a docstring describing
  the intended contract (extract atomic claims; per claim, prompt the model to
  return supported/unsupported + a quoted supporting line). Do NOT write the
  prompt or the claim-extraction/judging logic.
- **verdict.py**: stub with `# TODO`. Do NOT decide the scoring/aggregation logic
  beyond returning the shape.
- Do NOT wire in DeepEval yet.
- Do NOT write the judge/extraction prompts.
- Do NOT fabricate results, sample outputs, or fake metrics in the README.

If any instruction here is ambiguous, stop and leave a `# TODO(human):` note
rather than guessing. Prefer under-building over improvising scope.

## Conventions
- Keep functions small and readable; the human will read every line and must be
  able to explain it in an interview.
- Comment *why*, not *what*.
- No secrets in code; everything sensitive via `.env`.

# eval-harness

An eval harness for grounding LLM output against a source of truth.

## Overview

_TODO(human): what this is, in a few lines._

## Problem

_TODO(human): why unsupported output / false greens matter, and what goes wrong
when nobody checks an answer against its source._

## Architecture

Three LangGraph nodes, run in order:

| Node | File | Does |
| --- | --- | --- |
| `ingest` | `src/nodes/ingest.py` | Loads a source record + a model answer into state |
| `judge` | `src/nodes/judge.py` | **Stub.** Extracts atomic claims, checks each against the source |
| `verdict` | `src/nodes/verdict.py` | **Stub.** Tallies supported vs unsupported into a rate |

State is a single `EvalState` TypedDict (`src/state.py`); the graph is wired in
`src/graph.py`.

_TODO(human): the prose — why the eval logic lives inside the nodes rather than
alongside the graph._

## How the judge works

_TODO(human): claim extraction, the mandatory quoted supporting line, and how an
unciteable claim becomes `unsupported`. Not yet implemented._

## Validating the judge

_TODO(human): ~10 hand-labeled claims, and the agreement figure between those
labels and the judge. No numbers here until that run has actually happened._

## Running it

Setup:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env   # then add your ANTHROPIC_API_KEY
```

Run the graph end-to-end (currently exercises the stub nodes):

```bash
.venv/bin/python -m src.graph
```

Tests:

```bash
.venv/bin/python -m pytest tests/ -q
```

### Sample records

Synthetic patient records come from [Synthea](https://github.com/synthetichealth/synthea),
cloned into `vendor-synthea/` (not part of this package). The records in `data/`
were generated with:

```bash
cd vendor-synthea
./run_synthea -p 5 -s 12345 --exporter.baseDirectory ../data
```

`-s 12345` fixes the seed so the same records regenerate. Output is FHIR JSON in
`data/fhir/` — six patient bundles plus hospital and practitioner references,
~47 MB, so it is worth keeping out of version control.

_TODO(human): a worked example — a record, an answer, and the verdict — once the
judge is implemented._

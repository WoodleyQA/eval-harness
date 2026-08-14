# Eval Harness: Grounding LLM Output Against a Source of Truth

An LLM evaluation harness, built on LangGraph, that checks whether a model's output is actually supported by its source data, and flags exactly where it isn't.

Given an answer and a source record, the harness extracts every checkable claim, verifies each one against the source, and produces a hallucination rate with per-claim receipts: what the model said, whether it's supported, and the exact source line (or lack of one) backing that verdict.

Demonstrated here on synthetic patient records, but the approach applies anywhere an LLM's output needs to be checked against ground truth — not just healthcare.

## The Problem

Passing tests don't mean an LLM's output is correct — they often just mean it didn't crash. A model can generate a fluent, confident answer that includes fabricated details, and a naive check (did we get a response? does it mention the right topic?) will call that a pass.

This harness targets a sharper question: for every specific factual claim in an answer, is it actually backed by the source data, or did the model make it up? That's the difference between a system that looks correct and one that's verifiably correct.

## Architecture

A three-node LangGraph pipeline:

1. Ingest — loads a source record and a model-generated answer into state. Source records are flattened into plain key-value lines (e.g. Condition.code: Essential hypertension (disorder)) rather than passed as raw JSON, so every fact the judge cites traces to one unambiguous, quotable line.
2. Judge — two steps, both LLM calls, kept separate for auditability:
    * Extract: breaks the answer into atomic claims (one checkable fact per claim), tagging each as checkable or not. Unjudgeable statements (opinions, hedges) are kept and tagged, never silently dropped.
    * Check: for every checkable claim, verifies it against the source record. A supported verdict must quote the exact source line backing it. An unsupported verdict must explain why — not mentioned, or the source states something different.
3. Verdict — tallies the results into a hallucination rate (unsupported ÷ checkable claims) plus a full per-claim report: every claim, its verdict, its quote or explanation. Nothing is summarized away.

## How the Judge Works

The judge is deliberately narrow: for each claim, it asks one question — "can I point to a specific line in the source that confirms this exactly?" Partial matches, close-but-not-quite values, and unmentioned facts all count as unsupported. There's no partial-credit category; ambiguity is resolved in the required explanation text, not by fuzzying the verdict itself.

This makes the judge's output auditable rather than a black box: every "supported" comes with the exact line that proves it, and every "unsupported" comes with a specific reason, not just a flag.

## Validation

Before trusting the judge's verdicts, they were checked against independent human review — the same standard a real eval team would apply.

14 checkable claims were pulled from the judge's output across 4 synthetic patient records (a mix of accurate claims, subtly wrong claims — e.g. a swapped diagnosis date — and outright fabrications). Each claim was hand-labeled supported/unsupported by manually checking the source record, before looking at the judge's actual verdict.

Result: 14/14 agreement (100%) between the manual labels and the judge's verdicts.

One case worth calling out: a claim stated the patient "has type 1 diabetes." The source record contained only a diabetes screening test, not a diagnosis — the judge correctly distinguished a screening procedure from an actual condition, rather than pattern-matching on the word "diabetes" appearing nearby. Independent manual review caught the same distinction.

## Worked Example

A test answer was constructed with a mix of accurate and fabricated claims about a real synthetic patient record, then run through the harness.

Result: hallucination_rate: 0.4 (2 of 5 checkable claims unsupported)

* ✅ Correct claims, verified: patient sex, an essential hypertension diagnosis, and its diagnosis year — each returned supported with the exact source line quoted.
* ❌ Fabricated claim caught: "type 2 diabetes, treated with metformin." The judge didn't just note the condition was absent — it cited the patient's actual HbA1c reading (5.2%, within normal range) and the real medication list (none of which is metformin) as positive evidence against the claim.
* ⚪ Non-factual statement handled correctly: an opinion-style statement ("appears to be in reasonably good health") was extracted, tagged checkable: false, and correctly excluded from the hallucination rate — rather than silently dropped or wrongly penalized.

## Running It

```bash
git clone <your-repo-url>
cd eval-harness
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # add your Anthropic API key
python scripts/run_example.py
```

Sample Synthea patient records are included in data/.

## Future Work

The current harness judges one answer at a time. The natural next step is a meta-evaluation layer: aggregate verdicts across many runs to surface systemic patterns — which fields get hallucinated most often, which claim types are riskiest — rather than treating every run as an isolated check. That shift, from single-instance judgment to pattern-level insight across many runs, is how evaluation scales past being a one-off check into something that actually improves the system being evaluated over time.

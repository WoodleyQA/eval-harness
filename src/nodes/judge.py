"""judge — extract atomic claims from the answer and check each against the source.

STUB. The reasoning logic is deliberately unwritten; see TODO(human) below.

Intended contract
-----------------
Two steps, both inside this node:

1. **Extract.** Break `state["answer"]` into *atomic* claims — one assertion
   each, self-contained enough to be checked on its own. Write them to
   `claims`.

2. **Check.** For every claim, prompt the model with that claim plus
   `state["source_record"]` and require a verdict of `supported` or
   `unsupported`. A `supported` verdict must carry a **quoted supporting line**
   from the source record; if the model cannot quote one, the claim is
   `unsupported`. That quote is the receipt — it is what makes a verdict
   auditable rather than a vibe, and it is why the citation is mandatory rather
   than optional.

Returns `{"claims": [...], "verdicts": [...]}` with one verdict per claim, in
the same order.
"""

from src.state import EvalState


def judge(state: EvalState) -> dict:
    """Judge the answer's claims against the source record.

    Returns the shape only, so the graph runs end-to-end while unimplemented.
    """
    # TODO(human): implement claim extraction and per-claim judging.
    #   - Decide the claim/verdict record shapes (and keep `state.py` honest).
    #   - Write the extraction prompt and the per-claim judging prompt.
    #   - Decide how a claim that is neither clearly supported nor clearly
    #     contradicted is handled — unsupported, or a third bucket?
    #   - Decide the model + how it is called (langchain-anthropic is installed;
    #     the key comes from ANTHROPIC_API_KEY in .env).
    return {"claims": [], "verdicts": []}

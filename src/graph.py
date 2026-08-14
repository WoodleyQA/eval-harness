"""Wire the three eval nodes into a LangGraph.

The graph is deliberately linear: ingest -> judge -> verdict. Keeping the
skeleton this dumb means the interesting decisions all live inside the nodes,
and the pipeline stays runnable end-to-end even while those nodes are stubs.
"""

from langgraph.graph import END, START, StateGraph

from src.nodes.ingest import ingest
from src.nodes.judge import judge
from src.nodes.verdict import verdict
from src.state import EvalState


def build_graph():
    """Build and compile the eval graph.

    Returned compiled graph is invoked with an initial state carrying
    `source_record` and `answer` (each a path or literal text).
    """
    builder = StateGraph(EvalState)

    builder.add_node("ingest", ingest)
    builder.add_node("judge", judge)
    builder.add_node("verdict", verdict)

    builder.add_edge(START, "ingest")
    builder.add_edge("ingest", "judge")
    builder.add_edge("judge", "verdict")
    builder.add_edge("verdict", END)

    return builder.compile()


def run(source_record: str, answer: str) -> EvalState:
    """Run one evaluation and return the final state.

    Thin convenience wrapper so callers (tests, a future CLI) don't each have to
    know the initial-state keys.
    """
    return build_graph().invoke({"source_record": source_record, "answer": answer})


if __name__ == "__main__":
    # Smoke check: proves the graph is wired and executes with stub nodes.
    final_state = run(
        source_record="Patient reports a persistent cough.",
        answer="The patient has a cough.",
    )
    print(final_state)

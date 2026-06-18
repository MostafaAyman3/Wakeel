"""
M3 Customer Support Agent — LangGraph StateGraph.

Sprint 1 flow (linear):
    START → InputParser → DataFetcher → DataCompletenessCheck → END

Later sprints insert nodes between DataCompletenessCheck and END:
    … → IssueClassifier (S2) → ContextBuilder (S2)
       → ResponseGenerator (S3) → HumanReviewGate (S4)
       → [auto-send | review | escalate]

Blueprint reference: section 3.4 — Agent Workflow.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.m3.schemas.m3_state import M3State
from agents.m3.nodes.input_parser_node import parse_input
from agents.m3.nodes.data_fetcher_node import fetch_data
from agents.m3.nodes.data_completeness_node import check_completeness


def build_support_graph():
    """Build and compile the M3 support graph.

    Returns a ``CompiledStateGraph`` ready for ``ainvoke`` / ``astream``.
    """
    graph = StateGraph(M3State)

    # ── Register Sprint 1 nodes ───────────────────────────────────
    graph.add_node("input_parser", parse_input)
    graph.add_node("data_fetcher", fetch_data)
    graph.add_node("completeness_check", check_completeness)

    # ── Linear wiring ─────────────────────────────────────────────
    graph.add_edge(START, "input_parser")
    graph.add_edge("input_parser", "data_fetcher")
    graph.add_edge("data_fetcher", "completeness_check")
    graph.add_edge("completeness_check", END)

    # TODO (Sprint 2+): add issue_classifier, context_builder, then
    # response_generator (S3) and a conditional human_review_gate (S4).

    return graph.compile()


# ── Compiled graph instance ───────────────────────────────────────────────────
# Import this in the API endpoint:
#     from agents.m3.graphs.m3_graph import support_graph
support_graph = build_support_graph()

"""
M3 Customer Support Agent — LangGraph StateGraph.

Sprint 1 + 2 + 3 flow:
    START → InputParser → DataFetcher → DataCompletenessCheck
    → (conditional: escalate → ResponseGenerator | classify → IssueClassifier
       → ContextBuilder → ResponseGenerator) → END

Sprint 4 will insert HumanReviewGate between ResponseGenerator and END:
    → HumanReviewGate → [auto-send | review | escalate]

Blueprint reference: section 3.4 — Agent Workflow.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.m3.schemas.m3_state import M3State
from agents.m3.nodes.input_parser_node import parse_input
from agents.m3.nodes.data_fetcher_node import fetch_data
from agents.m3.nodes.data_completeness_node import check_completeness
from agents.m3.nodes.issue_classifier_node import classify_issue
from agents.m3.nodes.context_builder_node import build_context
from agents.m3.nodes.response_generator_node import generate_response  # Sprint 3
from agents.m3.nodes.human_review_node import human_review_gate        # Sprint 4
from agents.m3.nodes.escalation_node import escalate_case              # Sprint 4


def _escalation_router(state: M3State) -> str:
    """If escalation is needed, skip classifier/context — go to ResponseGenerator."""
    return "escalate" if state.get("escalation_needed", False) else "classify"


def _review_router(state: M3State) -> str:
    """Route after human review gate: escalate or end."""
    return "escalate" if state.get("escalation_needed", False) else "end"


def build_support_graph():
    """Build and compile the M3 support graph.

    Returns a ``CompiledStateGraph`` ready for ``ainvoke`` / ``astream``.
    """
    graph = StateGraph(M3State)

    # ── Register nodes ────────────────────────────────────────────────
    graph.add_node("input_parser",           parse_input)
    graph.add_node("data_fetcher",           fetch_data)
    graph.add_node("completeness_check",     check_completeness)
    graph.add_node("issue_classifier",       classify_issue)              # Sprint 2
    graph.add_node("context_builder",        build_context)               # Sprint 2
    graph.add_node("response_generator",     generate_response)           # Sprint 3
    graph.add_node("human_review_gate",      human_review_gate)           # Sprint 4
    graph.add_node("escalation_node",        escalate_case)               # Sprint 4

    # ── Pipeline ──────────────────────────────────────────────────────
    graph.add_edge(START, "input_parser")
    graph.add_edge("input_parser",            "data_fetcher")
    graph.add_edge("data_fetcher",            "completeness_check")
    graph.add_conditional_edges(
        "completeness_check",
        _escalation_router,
        {"classify": "issue_classifier", "escalate": "response_generator"},
    )
    graph.add_edge("issue_classifier",        "context_builder")         # Sprint 2
    graph.add_edge("context_builder",         "response_generator")      # Sprint 3
    graph.add_edge("response_generator",      "human_review_gate")       # Sprint 4
    graph.add_conditional_edges(                                         # Sprint 4
        "human_review_gate",
        _review_router,
        {"escalate": "escalation_node", "end": END},
    )
    graph.add_edge("escalation_node",         END)                       # Sprint 4

    return graph.compile()


# ── Compiled graph instance ───────────────────────────────────────────────────
# Import this in the API endpoint:
#     from agents.m3.graphs.m3_graph import support_graph
support_graph = build_support_graph()

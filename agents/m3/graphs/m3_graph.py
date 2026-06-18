"""
M3 LangGraph StateGraph — Customer Support Agent.

Sprint 2 flow:
    START → InputParser → DataFetcher → DataCompletenessCheck
    → IssueClassifier → ContextBuilder → END

Blueprint reference: M3_Sprints.md Sprint 1 + 2
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.m3.schemas.m3_state import M3State
from agents.m3.nodes.input_parser_node import parse_input
from agents.m3.nodes.data_fetcher_node import fetch_data
from agents.m3.nodes.data_completeness_node import check_data_completeness
from agents.m3.nodes.issue_classifier_node import classify_issue
from agents.m3.nodes.context_builder_node import build_context


def build_m3_graph():
    """Build and compile the M3 Customer Support Agent graph.

    Returns a ``CompiledStateGraph`` ready for ``ainvoke`` / ``astream``.
    """
    graph = StateGraph(M3State)

    # ── Register nodes ────────────────────────────────────────────────
    graph.add_node("input_parser",           parse_input)
    graph.add_node("data_fetcher",           fetch_data)
    graph.add_node("data_completeness_check", check_data_completeness)
    graph.add_node("issue_classifier",       classify_issue)        # Sprint 2
    graph.add_node("context_builder",        build_context)         # Sprint 2

    # ── Entry point ───────────────────────────────────────────────────
    graph.add_edge(START, "input_parser")

    # ── Sequential pipeline ───────────────────────────────────────────
    graph.add_edge("input_parser",            "data_fetcher")
    graph.add_edge("data_fetcher",            "data_completeness_check")
    graph.add_edge("data_completeness_check", "issue_classifier")   # Sprint 2
    graph.add_edge("issue_classifier",        "context_builder")    # Sprint 2
    graph.add_edge("context_builder",         END)                  # Sprint 2

    return graph.compile()


# ── Compiled graph instance ─────────────────────────────────────────
m3_graph = build_m3_graph()

"""
M3 Customer Support Agent — LangGraph StateGraph.

Unified Support Chatbot flow (Sprint 4 + Unified Router):

  START → intent_router
    ├─ general_knowledge → rag_node → response_generator → human_review_gate → [end | escalation_node]
    ├─ customer_issue    → input_parser → data_fetcher → completeness_check
    │                      → [escalate → response_generator | classify → issue_classifier → context_builder → response_generator]
    │                      → human_review_gate → [end | escalation_node]
    └─ hybrid            → rag_node → input_parser → data_fetcher → completeness_check → … (same as customer_issue)

Blueprint reference: section 3.4 — Agent Workflow.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.m3.schemas.m3_state import M3State
from agents.m3.nodes.intent_router_node import route_intent
from agents.m3.nodes.greeting_node import greet
from agents.m3.nodes.rag_node import run_rag
from agents.m3.nodes.input_parser_node import parse_input
from agents.m3.nodes.data_fetcher_node import fetch_data
from agents.m3.nodes.data_completeness_node import check_completeness
from agents.m3.nodes.issue_classifier_node import classify_issue
from agents.m3.nodes.context_builder_node import build_context
from agents.m3.nodes.response_generator_node import generate_response
from agents.m3.nodes.human_review_node import human_review_gate
from agents.m3.nodes.escalation_node import escalate_case
from agents.m3.nodes.clarification_node import clarify


# ── Routing helpers ───────────────────────────────────────────────────────────

def _route_from_intent(state: M3State) -> str:
    """After intent_router: dispatch greeting / RAG / CRM."""
    route = state.get("route", "customer_issue")
    if route == "greeting":
        return "greet"
    if route in ("general_knowledge", "hybrid"):
        return "rag"
    return "crm"


def _route_after_rag(state: M3State) -> str:
    """After rag_node: knowledge-only goes straight to response; hybrid goes to CRM."""
    route = state.get("route", "customer_issue")
    if route == "hybrid":
        return "crm"
    return "respond"


def _route_after_parse(state: M3State) -> str:
    """After input_parser: ask for a missing reference, or fetch data (Feature 004)."""
    return "clarify" if state.get("clarification_needed", False) else "fetch"


def _route_after_clarify(state: M3State) -> str:
    """After clarification_node: escalate (attempts spent) or end the turn (asked)."""
    return "escalate" if state.get("escalation_needed", False) else "end"


def _escalation_router(state: M3State) -> str:
    """If escalation is needed, skip classifier/context — go to ResponseGenerator."""
    return "escalate" if state.get("escalation_needed", False) else "classify"


def _review_router(state: M3State) -> str:
    """Route after human review gate: escalate or end."""
    return "escalate" if state.get("escalation_needed", False) else "end"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_support_graph():
    """Build and compile the M3 support graph.

    Returns a ``CompiledStateGraph`` ready for ``ainvoke`` / ``astream``.
    """
    graph = StateGraph(M3State)

    # ── Register nodes ────────────────────────────────────────────────
    graph.add_node("intent_router",       route_intent)
    graph.add_node("greeting_node",       greet)
    graph.add_node("rag_node",            run_rag)
    graph.add_node("input_parser",        parse_input)
    graph.add_node("data_fetcher",        fetch_data)
    graph.add_node("completeness_check",  check_completeness)
    graph.add_node("issue_classifier",    classify_issue)
    graph.add_node("context_builder",     build_context)
    graph.add_node("response_generator",  generate_response)
    graph.add_node("human_review_gate",   human_review_gate)
    graph.add_node("escalation_node",     escalate_case)
    graph.add_node("clarification_node",  clarify)              # Feature 004

    # ── Entry: intent router ──────────────────────────────────────────
    graph.add_edge(START, "intent_router")

    # intent_router → greeting_node OR rag_node (knowledge/hybrid) OR input_parser (issue)
    graph.add_conditional_edges(
        "intent_router",
        _route_from_intent,
        {"greet": "greeting_node", "rag": "rag_node", "crm": "input_parser"},
    )

    # greeting is terminal — no RAG, no CRM pipeline, no review gate
    graph.add_edge("greeting_node", END)

    # rag_node → response_generator (knowledge-only) OR input_parser (hybrid)
    graph.add_conditional_edges(
        "rag_node",
        _route_after_rag,
        {"respond": "response_generator", "crm": "input_parser"},
    )

    # CRM pipeline (customer_issue + hybrid after RAG)
    # Feature 004: after parsing, ask for a missing reference instead of escalating.
    graph.add_conditional_edges(
        "input_parser",
        _route_after_parse,
        {"fetch": "data_fetcher", "clarify": "clarification_node"},
    )
    graph.add_conditional_edges(
        "clarification_node",
        _route_after_clarify,
        {"escalate": "escalation_node", "end": END},
    )
    graph.add_edge("data_fetcher",           "completeness_check")
    graph.add_conditional_edges(
        "completeness_check",
        _escalation_router,
        {"classify": "issue_classifier", "escalate": "response_generator"},
    )
    graph.add_edge("issue_classifier",       "context_builder")
    graph.add_edge("context_builder",        "response_generator")

    # Shared tail: response → review → [end | escalate]
    graph.add_edge("response_generator",     "human_review_gate")
    graph.add_conditional_edges(
        "human_review_gate",
        _review_router,
        {"escalate": "escalation_node", "end": END},
    )
    graph.add_edge("escalation_node",        END)

    return graph.compile()


# ── Compiled graph instance ───────────────────────────────────────────────────
support_graph = build_support_graph()

"""
RouterNode — conditional edge function that routes by classified intent.

This is NOT a standalone graph node — it is used as the ``path`` argument
to ``StateGraph.add_conditional_edges`` after ``intent_classifier``.

Blueprint reference: section 2.5 — Router Node in Agent Workflow
"""

from __future__ import annotations

from agents.m1.schemas.m1_state import M1State


# Map intents to the next node name in the graph.
# Sprint 3: invoice_analysis_stub → invoice_analysis_tool (real implementation)
ROUTING_MAP: dict[str, str] = {
    "financial_query":      "db_query_tool",
    "operational_query":    "db_query_tool",
    "invoice_analysis":     "invoice_analysis_tool",   # Sprint 3 — real node
    "tax_reasoning":        "tax_rag_stub",
    "clarification_needed": "clarification",
}


def route_by_intent(state: M1State) -> str:
    """Return the next node name based on the classified intent.

    Falls back to ``"clarification"`` for any unknown intent value.
    """
    intent = state.get("intent", "clarification_needed")
    return ROUTING_MAP.get(intent, "clarification")

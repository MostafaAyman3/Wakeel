"""
M1 LangGraph StateGraph — wires all Sprint 1 nodes together.

Flow:
    START → IntentClassifier → Router (conditional)
        ├─ clarification_needed  → ClarificationNode       → END
        ├─ financial_query       → DB Query Stub            → ValidationEnrichment → END
        ├─ operational_query     → DB Query Stub            → ValidationEnrichment → END
        ├─ invoice_analysis      → Invoice Analysis Stub    → ValidationEnrichment → END
        └─ tax_reasoning         → Tax RAG Stub             → ValidationEnrichment → END

Blueprint reference: section 2.5 — Agent Workflow
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.m1.schemas.m1_state import M1State
from agents.m1.nodes.intent_classifier_node import classify_intent
from agents.m1.nodes.router_node import route_by_intent
from agents.m1.nodes.clarification_node import clarify
from agents.m1.nodes.validation_enrichment_node import validate_and_enrich
from agents.m1.tools.db_query_tool import db_query_tool
from agents.m1.nodes.stub_nodes import (
    invoice_analysis_stub,
    tax_rag_stub,
)


def build_m1_graph():
    """Build and compile the M1 Intelligence Agent graph.

    Returns a ``CompiledStateGraph`` ready for ``ainvoke`` / ``astream``.
    """
    graph = StateGraph(M1State)

    # ── Register nodes ────────────────────────────────────────
    graph.add_node("intent_classifier", classify_intent)
    graph.add_node("clarification", clarify)
    graph.add_node("db_query_tool", db_query_tool)
    graph.add_node("invoice_analysis_stub", invoice_analysis_stub)
    graph.add_node("tax_rag_stub", tax_rag_stub)
    graph.add_node("validation_enrichment", validate_and_enrich)

    # ── Entry point ───────────────────────────────────────────
    graph.add_edge(START, "intent_classifier")

    # ── Conditional routing after intent classification ───────
    graph.add_conditional_edges(
        "intent_classifier",
        route_by_intent,
        {
            "clarification":          "clarification",
            "db_query_tool":          "db_query_tool",
            "invoice_analysis_stub":  "invoice_analysis_stub",
            "tax_rag_stub":           "tax_rag_stub",
        },
    )

    # ── Clarification → END (no further processing needed) ───
    graph.add_edge("clarification", END)

    # ── Tool nodes → Validation → END ────────────────────────
    graph.add_edge("db_query_tool", "validation_enrichment")
    graph.add_edge("invoice_analysis_stub", "validation_enrichment")
    graph.add_edge("tax_rag_stub", "validation_enrichment")
    graph.add_edge("validation_enrichment", END)

    return graph.compile()


# ── Compiled graph instance ──────────────────────────────────────
# Import this in the API endpoint:
#     from agents.m1.graphs.m1_graph import m1_graph
m1_graph = build_m1_graph()

"""
M1 LangGraph StateGraph — wires all Sprint 1-5 nodes together.

Flow:
    START → IntentClassifier → Router (conditional)
        ├─ clarification_needed  → ClarificationNode         → END
        ├─ financial_query       → DBQueryTool                → ValidationEnrichment → OutputSelector → NarrativeGenerator → END
        ├─ operational_query     → DBQueryTool                → ValidationEnrichment → OutputSelector → NarrativeGenerator → END
        ├─ invoice_analysis      → InvoiceAnalysisToolNode    → ValidationEnrichment → OutputSelector → NarrativeGenerator → END
        └─ tax_reasoning         → TaxRAGNode (Sprint 4)      → ValidationEnrichment → OutputSelector → NarrativeGenerator → END

Blueprint reference: section 2.5 — Agent Workflow
Sprint 3: replaced invoice_analysis_stub with InvoiceAnalysisToolNode
Sprint 4: replaced tax_rag_stub with tax_rag_node (Tax RAG — pgvector)
Sprint 5: added output_selector + narrative_generator after validation_enrichment
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.m1.schemas.m1_state import M1State
from agents.m1.nodes.intent_classifier_node import classify_intent
from agents.m1.nodes.router_node import route_by_intent
from agents.m1.nodes.clarification_node import clarify
from agents.m1.nodes.validation_enrichment_node import validate_and_enrich
from agents.m1.tools.db_query_tool import db_query_tool
from agents.m1.nodes.invoice_analysis_tool_node import invoice_analysis_tool  # Sprint 3
from agents.m1.nodes.tax_rag_node import tax_rag_node  # Sprint 4 — real node
from agents.m1.nodes.output_selector_node import select_output  # Sprint 5
from agents.m1.nodes.narrative_generator_node import generate_narrative  # Sprint 5


def build_m1_graph():
    """Build and compile the M1 Intelligence Agent graph.

    Returns a ``CompiledStateGraph`` ready for ``ainvoke`` / ``astream``.
    """
    graph = StateGraph(M1State)

    # ── Register nodes ────────────────────────────────────────────────
    graph.add_node("intent_classifier",      classify_intent)
    graph.add_node("clarification",          clarify)
    graph.add_node("db_query_tool",          db_query_tool)
    graph.add_node("invoice_analysis_tool",  invoice_analysis_tool)  # Sprint 3 — real node
    graph.add_node("tax_rag_node",           tax_rag_node)           # Sprint 4 — real node
    graph.add_node("validation_enrichment",  validate_and_enrich)
    graph.add_node("output_selector",        select_output)          # Sprint 5
    graph.add_node("narrative_generator",    generate_narrative)      # Sprint 5

    # ── Entry point ───────────────────────────────────────────────────
    graph.add_edge(START, "intent_classifier")

    # ── Conditional routing after intent classification ───────────────
    graph.add_conditional_edges(
        "intent_classifier",
        route_by_intent,
        {
            "clarification":           "clarification",
            "db_query_tool":           "db_query_tool",
            "invoice_analysis_tool":   "invoice_analysis_tool",  # Sprint 3
            "tax_rag_node":            "tax_rag_node",           # Sprint 4
        },
    )

    # ── Clarification → END (no further processing needed) ───────────
    graph.add_edge("clarification", END)

    # ── Tool nodes → Validation → Output Selector → Narrative → END ──
    graph.add_edge("db_query_tool",         "validation_enrichment")
    graph.add_edge("invoice_analysis_tool", "validation_enrichment")  # Sprint 3
    graph.add_edge("tax_rag_node",          "validation_enrichment")  # Sprint 4
    graph.add_edge("validation_enrichment", "output_selector")        # Sprint 5
    graph.add_edge("output_selector",       "narrative_generator")    # Sprint 5
    graph.add_edge("narrative_generator",   END)                      # Sprint 5

    return graph.compile()


# ── Compiled graph instance ──────────────────────────────────────────────────
# Import this in the API endpoint:
#     from agents.m1.graphs.m1_graph import m1_graph
m1_graph = build_m1_graph()

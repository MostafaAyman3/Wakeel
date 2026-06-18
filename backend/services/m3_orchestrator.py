"""
M3 Orchestrator — invokes support_graph with customer input and returns structured results.

Sprint 1: basic invocation + response formatting.
Future sprints: audit trail logging, human review routing, escalation.

NOTE: This module is NOT imported by the API endpoint (which invokes the graph
directly). It exists as a convenience wrapper for standalone/CLI usage. Marked
as dead code — do NOT integrate into the API without a specific requirement.
"""

from __future__ import annotations

from agents.m3.graphs.m3_graph import support_graph
from agents.m3.schemas.m3_state import build_initial_state
from backend.core.logging import get_logger

logger = get_logger(__name__)


async def handle_support_request(
    query: str,
    identifier: dict | None = None,
) -> dict:
    """Process a customer support query through the M3 LangGraph.

    Returns the final graph state with all results.
    """
    state = build_initial_state(query=query, identifier=identifier)

    try:
        result = await support_graph.ainvoke(state)
        logger.info(
            "m3_graph_completed",
            identifier=result.get("customer_identifier"),
            data_completeness=result.get("data_completeness"),
            error=result.get("error", ""),
        )
        return result

    except Exception as exc:
        logger.error("m3_graph_failed", error=str(exc))
        return {
            **state,
            "error": f"M3 agent error: {exc}",
            "draft_response": "عذراً، حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى لاحقاً.",
            "confidence_score": 0.0,
            "review_required": True,
            "escalation_needed": True,
        }

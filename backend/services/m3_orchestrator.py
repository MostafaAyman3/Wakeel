"""
M3 Orchestrator — invokes the m3_graph with customer input and returns structured results.

Sprint 1: basic invocation + response formatting.
Future sprints: audit trail logging, human review routing, escalation.
"""

from __future__ import annotations

from typing import Any

import structlog

from agents.m3.graphs.m3_graph import m3_graph
from agents.m3.schemas.m3_state import M3State

logger = structlog.get_logger(__name__)


def _make_initial_state(
    query: str,
    identifier: dict | None = None,
) -> dict:
    """Build the initial M3State dict from the API request."""
    state: dict[str, Any] = {
        "customer_identifier": identifier or {"type": "customer_id", "value": "unknown"},
        "issue_description": query,
        "language": "en",
        "issue_type": "general_complaint",
        "issue_priority": "Medium",
        "context": {},
        "fetched_data": {"invoice": None, "order": None, "shipping": None, "history": None},
        "data_completeness": 0.0,
        "missing_fields": [],
        "draft_response": "",
        "confidence_score": 0.0,
        "review_required": False,
        "escalation_needed": False,
        "rejection_context": None,
        "final_response": "",
        "error": "",
    }
    return state


async def handle_support_request(
    query: str,
    identifier: dict | None = None,
) -> dict:
    """Process a customer support query through the M3 LangGraph.

    Returns the final graph state with all results.
    """
    state = _make_initial_state(query, identifier)

    try:
        result = await m3_graph.ainvoke(state)
        logger.info("m3_graph_completed",
                     identifier=result.get("customer_identifier"),
                     data_completeness=result.get("data_completeness"),
                     error=result.get("error", ""))
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

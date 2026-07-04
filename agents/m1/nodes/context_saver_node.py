"""Build bounded structured metadata for persistence after every M1 turn."""

from __future__ import annotations

from numbers import Number
from typing import Any

from agents.m1.config.constants import (
    CONTEXT_MAX_KEY_METRICS,
    CONTEXT_SCHEMA_VERSION,
)
from agents.m1.schemas.m1_state import M1State


def _key_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    metrics: dict[str, Any] = {}
    for key, value in rows[0].items():
        if isinstance(value, Number) and not isinstance(value, bool):
            metrics[key] = value
        if len(metrics) >= CONTEXT_MAX_KEY_METRICS:
            break
    return metrics


async def save_context(state: M1State) -> dict:
    rows = state.get("raw_data", [])
    clarification = None
    if state.get("clarification_pending") or state.get("assigned_tier") == "T4":
        clarification = {
            "pending": True,
            "original_query": state.get(
                "clarification_original_query",
                state.get("query", ""),
            ),
            "missing_slots": state.get("clarification_missing_slots", []),
            "question": state.get(
                "clarification_question",
                state.get("clarification_message", ""),
            ),
        }

    # A failed/empty turn must not poison the conversation context: keep the
    # last frame that actually produced data so follow-ups ("طب والسنة؟")
    # resolve against it instead of the dead-end frame.
    analysis_frame = state.get("analysis_frame", {})
    if (
        state.get("result_status") in ("empty", "failed")
        and state.get("prior_analysis_frame")
    ):
        analysis_frame = state["prior_analysis_frame"]

    metadata = {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "assigned_tier": state.get("assigned_tier", ""),
        "domain_intent": state.get("domain_intent", ""),
        "analysis_frame": analysis_frame,
        "matched_template": state.get("matched_template", ""),
        "query_mode": state.get("query_mode", "none"),
        "result_summary": {
            "status": state.get("result_status", ""),
            "coverage": state.get("result_coverage", 0.0),
            "row_count": len(rows),
            "columns": list(rows[0]) if rows else [],
            "key_metrics": _key_metrics(rows),
            "evidence": state.get("result_evidence", [])[:5],
            "gaps": state.get("result_gaps", [])[:5],
        },
        "output_format": state.get("output_format", "direct_text"),
        "clarification": clarification,
        "react_exit_reason": state.get("react_exit_reason", ""),
    }
    return {"context_metadata": metadata}


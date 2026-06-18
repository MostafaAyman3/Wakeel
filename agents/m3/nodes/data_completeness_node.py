"""
DataCompletenessCheckNode — scores how complete the fetched data is.

Scoring (Sprint 1, per blueprint section 3.4):
    All four sources present  → data_completeness = 1.0,  missing_fields = []
    Some present, some missing → data_completeness = 0.5,  missing_fields = [...]
    None present               → data_completeness = 0.0,  escalation_needed = True

Confidence (Sprint 1 only): confidence_score = data_completeness.
A richer, LLM-aware confidence lands in Sprint 3 (ResponseGenerator).

The ``get_confidence_label`` helper is shared with the API layer so the
High/Medium/Low mapping is defined in exactly one place.
"""

from __future__ import annotations

from agents.m3.schemas.m3_state import M3State
from backend.core.logging import get_logger

logger = get_logger(__name__)

# The four sources that define completeness, in display order.
_REQUIRED_SOURCES = ("invoice", "order", "shipping", "history")


def get_confidence_label(score: float) -> str:
    """Map a 0.0–1.0 confidence score to a High/Medium/Low label.

    Thresholds (blueprint section 3.5):
        score >= 0.8 -> "High"
        score >= 0.5 -> "Medium"
        else         -> "Low"
    """
    if score >= 0.8:
        return "High"
    if score >= 0.5:
        return "Medium"
    return "Low"


async def check_completeness(state: M3State) -> dict:
    """Compute data_completeness, missing_fields, confidence, and escalation.

    Returns a partial state update. Pure/deterministic — no I/O, no LLM.
    """
    fetched_data: dict = state.get("fetched_data") or {}

    present = [s for s in _REQUIRED_SOURCES if fetched_data.get(s)]
    missing = [s for s in _REQUIRED_SOURCES if not fetched_data.get(s)]

    if not present:
        completeness = 0.0
        escalation_needed = True
    elif not missing:
        completeness = 1.0
        escalation_needed = bool(state.get("escalation_needed", False))
    else:
        completeness = 0.5
        escalation_needed = bool(state.get("escalation_needed", False))

    confidence = completeness  # Sprint 1 equivalence

    logger.info(
        "completeness_checked",
        data_completeness=completeness,
        confidence_label=get_confidence_label(confidence),
        missing_fields=missing,
        escalation_needed=escalation_needed,
    )

    return {
        "data_completeness": completeness,
        "confidence_score": confidence,
        "missing_fields": missing,
        "escalation_needed": escalation_needed,
    }

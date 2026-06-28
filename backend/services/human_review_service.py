from __future__ import annotations

from backend.core.logging import get_logger
from backend.services.audit_service import log_decision

logger = get_logger(__name__)


async def _safe_log(**kwargs) -> None:
    """Best-effort audit write — a transient DB failure must never break the
    agent's review action (matches the escalation_node pattern)."""
    try:
        await log_decision(**kwargs)
    except Exception as exc:  # noqa: BLE001
        logger.warning("review_audit_failed", error=str(exc), **{
            k: kwargs.get(k) for k in ("case_id", "action_taken")
        })


async def approve_response(
    case_id: str,
    draft_response: str,
    issue_type: str | None = None,
    confidence_score: float = 0.0,
    reviewed_by: str = "system",
) -> dict:
    """Approve a draft response for sending.

    Logs the approval decision to the audit trail.

    Returns:
        Dict with ``case_id``, ``action``, and ``final_response``.
    """
    await _safe_log(
        case_id=case_id,
        issue_type=issue_type,
        confidence_score=confidence_score,
        review_required=False,
        action_taken="approved",
        agent_id=reviewed_by,
    )
    logger.info("response_approved", case_id=case_id, reviewed_by=reviewed_by)
    return {
        "case_id": case_id,
        "action": "approved",
        "final_response": draft_response,
    }


async def reject_response(
    case_id: str,
    draft_response: str,
    feedback: str,
    issue_type: str | None = None,
    confidence_score: float = 0.0,
    reviewed_by: str = "system",
) -> dict:
    """Reject a draft response and provide feedback for regeneration.

    Logs the rejection to the audit trail.
    The caller should re-invoke ``/support`` with the returned
    ``rejection_context`` to trigger a new generation.

    Returns:
        Dict with ``case_id``, ``action``, and ``rejection_context``.
    """
    await _safe_log(
        case_id=case_id,
        issue_type=issue_type,
        confidence_score=confidence_score,
        review_required=True,
        action_taken="rejected",
        agent_id=reviewed_by,
        details=feedback,
    )
    logger.info("response_rejected", case_id=case_id, reviewed_by=reviewed_by)
    return {
        "case_id": case_id,
        "action": "rejected",
        "rejection_context": {
            "reason": "human_rejection",
            "feedback": feedback,
            "previous_draft": draft_response,
        },
    }


async def escalate_manually(
    case_id: str,
    issue_type: str | None = None,
    confidence_score: float = 0.0,
    reviewed_by: str = "system",
    reason: str = "",
) -> dict:
    """Manually escalate a case to a senior agent.

    Logs the escalation to the audit trail.

    Returns:
        Dict with ``case_id``, ``action``, and ``escalation_reason``.
    """
    await _safe_log(
        case_id=case_id,
        issue_type=issue_type,
        confidence_score=confidence_score,
        review_required=True,
        action_taken="escalated",
        agent_id=reviewed_by,
        details=reason or "Manual escalation by reviewer",
    )
    logger.info("response_manually_escalated", case_id=case_id, reviewed_by=reviewed_by)
    return {
        "case_id": case_id,
        "action": "escalated",
        "escalation_reason": reason or "Manual escalation by reviewer",
    }

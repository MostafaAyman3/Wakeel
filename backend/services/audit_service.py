from __future__ import annotations

from backend.core.logging import get_logger
from backend.repositories.audit_logs import create_audit_log

logger = get_logger(__name__)


async def log_decision(
    case_id: str,
    issue_type: str | None,
    confidence_score: float,
    review_required: bool,
    action_taken: str,
    agent_id: str = "system",
    details: str | None = None,
) -> dict:
    """Log a decision to the audit trail.

    Args:
        case_id: Customer identifier value (order_id / invoice_id / customer_id).
        issue_type: Classified issue type.
        confidence_score: Agent confidence score (0.0-1.0).
        review_required: Whether human review was required.
        action_taken: One of "approved", "rejected", "escalated".
        agent_id: Who performed the action ("system" for auto-actions).
        details: Optional additional context (rejection reason, escalation reason).

    Returns:
        The created audit log entry as a dict.
    """
    try:
        result = await create_audit_log(
            case_id=case_id,
            issue_type=issue_type,
            confidence_score=confidence_score,
            review_required=review_required,
            action_taken=action_taken,
            agent_id=agent_id,
            details=details,
        )
        logger.info("audit_log_created", case_id=case_id, action_taken=action_taken)
        return result
    except Exception as exc:
        logger.error("audit_log_failed", case_id=case_id, error=str(exc))
        raise

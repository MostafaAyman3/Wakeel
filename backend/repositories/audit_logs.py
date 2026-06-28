from __future__ import annotations

import uuid

from sqlalchemy import select

from backend.core.database import get_db_session
from backend.models.audit_log import AuditLog


async def create_audit_log(
    case_id: str,
    issue_type: str | None,
    confidence_score: float,
    review_required: bool,
    action_taken: str,
    agent_id: str = "system",
    details: str | None = None,
) -> dict:
    """Create an audit log entry."""
    async with get_db_session() as session:
        entry = AuditLog(
            id=uuid.uuid4(),
            case_id=case_id,
            issue_type=issue_type,
            confidence_score=confidence_score,
            review_required=review_required,
            action_taken=action_taken,
            agent_id=agent_id,
            details=details,
        )
        session.add(entry)
        await session.flush()
        return {
            "id": str(entry.id),
            "case_id": entry.case_id,
            "issue_type": entry.issue_type,
            "confidence_score": entry.confidence_score,
            "review_required": entry.review_required,
            "action_taken": entry.action_taken,
            "agent_id": entry.agent_id,
            "details": entry.details,
            "created_at": entry.created_at.isoformat() if entry.created_at else "",
        }


async def get_audit_logs_by_case(case_id: str) -> list[dict]:
    """Get all audit log entries for a case."""
    async with get_db_session() as session:
        result = await session.execute(
            select(AuditLog)
            .where(AuditLog.case_id == case_id)
            .order_by(AuditLog.created_at)
        )
        entries = result.scalars().all()
        return [
            {
                "id": str(e.id),
                "case_id": e.case_id,
                "issue_type": e.issue_type,
                "confidence_score": e.confidence_score,
                "review_required": e.review_required,
                "action_taken": e.action_taken,
                "agent_id": e.agent_id,
                "details": e.details,
                "created_at": e.created_at.isoformat() if e.created_at else "",
            }
            for e in entries
        ]

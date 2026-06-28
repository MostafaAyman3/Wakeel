from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogCreate(BaseModel):
    case_id: str = Field(..., min_length=1, max_length=100)
    issue_type: str | None = None
    confidence_score: float = 0.0
    review_required: bool = False
    action_taken: str = Field(..., pattern="^(approved|rejected|escalated)$")
    agent_id: str = "system"
    details: str | None = None


class AuditLogResponse(AuditLogCreate):
    id: str
    created_at: datetime

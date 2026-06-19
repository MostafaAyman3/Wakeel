from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    case_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    issue_type: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    action_taken: Mapped[str] = mapped_column(String, nullable=False)
    agent_id: Mapped[str] = mapped_column(String, nullable=False, default="system")
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id!r} case_id={self.case_id!r} action={self.action_taken!r}>"

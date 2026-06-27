from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, field_validator


class RFQListItem(BaseModel):
    id: UUID
    product_id: UUID
    quantity: int
    unit: str
    status: str
    thread_id: Optional[str] = None
    alert_id: Optional[UUID] = None
    draft_preview: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RFQListResponse(BaseModel):
    rfqs: list[RFQListItem]
    total: int


class ApproveRFQRequest(BaseModel):
    approval_status: str
    notes: Optional[str] = None

    @field_validator("approval_status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        if v not in ("approved", "rejected"):
            raise ValueError("approval_status must be 'approved' or 'rejected'")
        return v


class ApproveRFQResponse(BaseModel):
    rfq_id: UUID
    approval_status: str
    message: str
    sent: bool = False

"""
M3 Customer Support Agent API router.

Endpoint: POST /api/v1/support
Accepts:  { query: str, identifier: { type: str, value: str } }
Returns:  {
    draft_response, confidence_score, review_required,
    escalation_needed, transparency_data (when review_required)
}

Sprint 1 will wire this to m3_graph.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.core.auth import UserContext, get_current_user
from backend.core.logging import get_logger

router = APIRouter(prefix="/support", tags=["M3 Customer Support"])
logger = get_logger(__name__)


class CustomerIdentifier(BaseModel):
    type: str = Field(..., pattern="^(order_id|invoice_id|customer_id)$")
    value: str = Field(..., min_length=1, max_length=100)


class SupportRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    identifier: CustomerIdentifier


class TransparencyData(BaseModel):
    invoice: dict | None = None
    order: dict | None = None
    shipping: dict | None = None
    history: list | None = None
    missing_fields: list[str] = []


class SupportResponse(BaseModel):
    draft_response: str
    confidence_score: float
    review_required: bool
    escalation_needed: bool
    transparency_data: TransparencyData | None = None


@router.post("", response_model=SupportResponse)
async def handle_support_request(
    request: SupportRequest,
    user: UserContext = Depends(get_current_user),
) -> SupportResponse:
    """
    Process a customer support query.

    Sprint 0 (M3): Mock data tables ready.
    Sprint 1 (M3): Input Parser + Data Fetcher + Completeness Check.
    Sprint 2 (M3): Issue Classifier + Context Builder.
    Sprint 3 (M3): Response Generator + Graceful Degradation.
    Sprint 4 (M3): Human Review Gate + Escalation + Audit Trail.
    """
    logger.info(
        "support_request_received",
        user_id=user.user_id,
        identifier_type=request.identifier.type,
        query_length=len(request.query),
    )

    # Placeholder until Sprint 1 wires m3_graph
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="M3 agent graph not yet wired. Implement M3 Sprint 1.",
    )

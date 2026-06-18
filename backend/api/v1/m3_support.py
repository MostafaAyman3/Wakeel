"""
M3 Customer Support Agent API router.

Endpoint: POST /api/v1/support
Accepts:  { query: str, identifier?: { type: str, value: str } }
Returns:  {
    draft_response, confidence_score, confidence_label, review_required,
    escalation_needed, issue_type, transparency_data, missing_fields
}

Sprint 1: wired to m3_graph (InputParser → DataFetcher → DataCompletenessCheck).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.core.auth import UserContext, get_current_user
from backend.core.logging import get_logger
from backend.services.m3_orchestrator import handle_support_request

router = APIRouter(prefix="/support", tags=["M3 Customer Support"])
logger = get_logger(__name__)


class CustomerIdentifier(BaseModel):
    type: str = Field(..., pattern="^(order_id|invoice_id|customer_id)$")
    value: str = Field(..., min_length=1, max_length=100)


class SupportRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    identifier: CustomerIdentifier | None = None


class TransparencyData(BaseModel):
    invoice: dict | None = None
    order: dict | None = None
    shipping: list | dict | None = None
    history: list | None = None
    missing_fields: list[str] = []


class SupportResponse(BaseModel):
    draft_response: str
    confidence_score: float
    confidence_label: str
    review_required: bool
    escalation_needed: bool
    issue_type: str
    transparency_data: TransparencyData | None = None
    missing_fields: list[str] = []


def _compute_confidence_label(score: float) -> str:
    if score >= 0.8:
        return "High"
    elif score >= 0.5:
        return "Medium"
    return "Low"


@router.post("", response_model=SupportResponse)
async def handle_support_request_endpoint(
    request: SupportRequest,
    user: UserContext = Depends(get_current_user),
) -> SupportResponse:
    """
    Process a customer support query through the M3 agent graph.
    """
    logger.info(
        "support_request_received",
        user_id=user.user_id,
        identifier=request.identifier.model_dump() if request.identifier else None,
        query_length=len(request.query),
    )

    identifier_dict = request.identifier.model_dump() if request.identifier else None

    try:
        result = await handle_support_request(
            query=request.query,
            identifier=identifier_dict,
        )

        if result.get("error"):
            logger.warning("support_request_partial_error",
                           error=result["error"],
                           user_id=user.user_id)

        fetched = result.get("fetched_data", {})
        fd_invoice = fetched.get("invoice") if isinstance(fetched, dict) else None
        fd_order = fetched.get("order") if isinstance(fetched, dict) else None
        fd_shipping = fetched.get("shipping") if isinstance(fetched, dict) else None
        fd_history = fetched.get("history") if isinstance(fetched, dict) else None

        transparency = None
        if fd_invoice or fd_order or fd_shipping or fd_history:
            transparency = TransparencyData(
                invoice=fd_invoice,
                order=fd_order,
                shipping=fd_shipping,
                history=fd_history,
                missing_fields=result.get("missing_fields", []),
            )

        draft = result.get("draft_response", "")
        if not draft:
            draft = _build_fallback_response(result)

        return SupportResponse(
            draft_response=draft,
            confidence_score=result.get("confidence_score", 0.0),
            confidence_label=_compute_confidence_label(result.get("confidence_score", 0.0)),
            review_required=result.get("review_required", False),
            escalation_needed=result.get("escalation_needed", False),
            issue_type=result.get("issue_type", "general_complaint"),
            transparency_data=transparency,
            missing_fields=result.get("missing_fields", []),
        )

    except Exception as exc:
        logger.error("support_request_failed",
                     error=str(exc),
                     user_id=user.user_id)
        return SupportResponse(
            draft_response="عذراً، حدث خطأ أثناء معالجة طلبك. يرجى المحاولة مرة أخرى لاحقاً.",
            confidence_score=0.0,
            confidence_label="Low",
            review_required=True,
            escalation_needed=True,
            issue_type="general_complaint",
            transparency_data=None,
            missing_fields=[],
        )


def _build_fallback_response(result: dict) -> str:
    """Build a fallback response when no draft was generated (Sprint 1)."""
    completeness = result.get("data_completeness", 0.0)
    missing = result.get("missing_fields", [])
    escalation = result.get("escalation_needed", False)

    if escalation:
        return (
            "لم نعثر على البيانات المطلوبة. "
            "يُرجى التأكد من الرقم أو التواصل مع فريق الدعم."
        )
    if completeness < 1.0 and missing:
        missing_str = "، ".join(f"بيانات {m}" for m in missing)
        return (
            f"تم العثور على بعض البيانات. "
            f"المعلومات التالية غير متاحة حالياً: {missing_str}. "
            "سيتواصل معك فريق الدعم خلال 24 ساعة."
        )
    return "تم استلام طلبك وجاري معالجته. سيتواصل معك فريق الدعم قريباً."

"""
M3 Customer Support Agent API router.

Endpoint: POST /api/v1/support
Accepts:  { query: str, identifier?: { type, value } }
          ``identifier`` is OPTIONAL — when omitted, InputParserNode extracts
          it from ``query``; when supplied it seeds the parser (used by the
          Sprint 5 customer form, and lets clients pin an exact reference).
Returns:  SupportResponse — always JSON, never an HTTP error for agent
          failures (keeps the frontend contract stable).

Wired to ``support_graph`` (LangGraph StateGraph) since M3 Sprint 1.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from agents.m3.schemas.m3_state import build_initial_state
from agents.m3.nodes.data_completeness_node import get_confidence_label
from backend.core.auth import UserContext, get_current_user
from backend.core.logging import get_logger
from backend.services.human_review_service import (
    approve_response,
    reject_response,
    escalate_manually,
)

router = APIRouter(prefix="/support", tags=["M3 Customer Support"])
logger = get_logger(__name__)


# ── Request schemas ──────────────────────────────────────────────

class CustomerIdentifier(BaseModel):
    type: str = Field(..., pattern="^(order_id|invoice_id|customer_id)$")
    value: str = Field(..., min_length=1, max_length=100)


class SupportRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    identifier: CustomerIdentifier | None = None
    rejection_context: dict | None = None  # Sprint 4: Reject & Regenerate


# ── Response schemas ─────────────────────────────────────────────

class TransparencyData(BaseModel):
    """Internal-only data the agent relied on.

    TODO (Sprint 5 UI): this block powers the Human Review "Transparency
    Panel". It MUST NOT be shown to the end customer in production — it is
    for the support agent's review screen only.
    """

    invoice: dict | None = None
    order: dict | None = None
    shipping: list | dict | None = None
    history: list | None = None


class SupportResponse(BaseModel):
    draft_response: str
    final_response: str            # Sprint 4: populated after review/escalation
    confidence_score: float
    confidence_label: str          # High | Medium | Low — review UI only
    review_required: bool
    escalation_needed: bool
    escalation_summary: dict       # Sprint 4: populated when escalated
    issue_type: str | None = None  # populated in Sprint 2
    transparency_data: TransparencyData
    missing_fields: list[str] = []


# ── Endpoint ─────────────────────────────────────────────────────

@router.post("", response_model=SupportResponse)
async def handle_support_request(
    request: SupportRequest,
    user: UserContext = Depends(get_current_user),
) -> SupportResponse:
    """Process a customer support query through the M3 agent graph.

    Sprint 1+2 scope: parse input -> fetch data (4 sources, parallel) ->
    score completeness -> classify issue -> build context. Response
    generation (draft_response) and the human review gate land in
    Sprints 3-4, so ``draft_response`` is empty here.
    """
    logger.info(
        "support_request_received",
        user_id=user.user_id,
        has_identifier=request.identifier is not None,
        query_length=len(request.query),
    )

    try:
        from agents.m3.graphs.m3_graph import support_graph

        identifier = request.identifier.model_dump() if request.identifier else None
        initial_state = build_initial_state(query=request.query, identifier=identifier)
        if request.rejection_context:
            initial_state["rejection_context"] = request.rejection_context

        result: dict = await support_graph.ainvoke(initial_state)

        fetched = result.get("fetched_data") or {}
        confidence = float(result.get("confidence_score", 0.0))

        logger.info(
            "support_request_completed",
            user_id=user.user_id,
            data_completeness=result.get("data_completeness", 0.0),
            escalation_needed=result.get("escalation_needed", False),
        )

        return SupportResponse(
            draft_response=result.get("draft_response", ""),
            final_response=result.get("final_response", ""),
            confidence_score=confidence,
            confidence_label=get_confidence_label(confidence),
            review_required=bool(result.get("review_required", False)),
            escalation_needed=bool(result.get("escalation_needed", False)),
            escalation_summary=result.get("escalation_summary", {}),
            issue_type=result.get("issue_type"),
            transparency_data=TransparencyData(
                invoice=fetched.get("invoice"),
                order=fetched.get("order"),
                shipping=fetched.get("shipping"),
                history=fetched.get("history"),
            ),
            missing_fields=result.get("missing_fields", []),
        )

    except Exception as exc:
        logger.error("support_request_failed", user_id=user.user_id, error=str(exc))

        lang = "ar" if any("\u0600" <= c <= "\u06FF" for c in request.query) else "en"
        message = (
            "\u062d\u062f\u062b \u062e\u0637\u0623 \u0623\u062b\u0646\u0627\u0621 "
            "\u0645\u0639\u0627\u0644\u062c\u0629 \u0637\u0644\u0628\u0643. "
            "\u0633\u064a\u062a\u0648\u0627\u0635\u0644 \u0645\u0639\u0643 "
            "\u0641\u0631\u064a\u0642 \u0627\u0644\u062f\u0639\u0645 \u0642\u0631\u064a\u0628\u0627\u064b."
            if lang == "ar"
            else "An error occurred while processing your request. "
            "Our support team will reach out shortly."
        )

        return SupportResponse(
            draft_response=message,
            final_response=message,
            confidence_score=0.0,
            confidence_label="Low",
            review_required=True,
            escalation_needed=True,
            escalation_summary={"escalation_reason": "System error during processing"},
            issue_type=None,
            transparency_data=TransparencyData(),
            missing_fields=["invoice", "order", "shipping", "history"],
        )


# ── Review Action Endpoints (Sprint 4) ──────────────────────────

class ApproveRequest(BaseModel):
    case_id: str
    draft_response: str
    issue_type: str | None = None
    confidence_score: float = 0.0


class RejectRequest(BaseModel):
    case_id: str
    draft_response: str
    feedback: str = Field(..., min_length=1, max_length=500)
    issue_type: str | None = None
    confidence_score: float = 0.0


class EscalateRequest(BaseModel):
    case_id: str
    issue_type: str | None = None
    confidence_score: float = 0.0
    reason: str = ""


class ReviewActionResponse(BaseModel):
    case_id: str
    action: str


@router.post("/approve", response_model=ReviewActionResponse)
async def approve_draft(
    request: ApproveRequest,
    user: UserContext = Depends(get_current_user),
) -> ReviewActionResponse:
    """Approve a draft response and send it to the customer."""
    result = await approve_response(
        case_id=request.case_id,
        draft_response=request.draft_response,
        issue_type=request.issue_type,
        confidence_score=request.confidence_score,
        reviewed_by=user.user_id,
    )
    return ReviewActionResponse(**result)


@router.post("/reject", response_model=ReviewActionResponse)
async def reject_draft(
    request: RejectRequest,
    user: UserContext = Depends(get_current_user),
) -> ReviewActionResponse:
    """Reject a draft response and request regeneration with feedback."""
    result = await reject_response(
        case_id=request.case_id,
        draft_response=request.draft_response,
        feedback=request.feedback,
        issue_type=request.issue_type,
        confidence_score=request.confidence_score,
        reviewed_by=user.user_id,
    )
    return ReviewActionResponse(**result)


@router.post("/escalate", response_model=ReviewActionResponse)
async def escalate_case(
    request: EscalateRequest,
    user: UserContext = Depends(get_current_user),
) -> ReviewActionResponse:
    """Manually escalate a case to a senior agent."""
    result = await escalate_manually(
        case_id=request.case_id,
        issue_type=request.issue_type,
        confidence_score=request.confidence_score,
        reviewed_by=user.user_id,
        reason=request.reason,
    )
    return ReviewActionResponse(**result)

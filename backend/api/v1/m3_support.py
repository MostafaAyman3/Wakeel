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
from backend.repositories.conversations import (
    load_conversation_history,
    append_conversation_turn,
)

router = APIRouter(prefix="/support", tags=["M3 Customer Support"])
logger = get_logger(__name__)


# ── Request schemas ──────────────────────────────────────────────

class CustomerIdentifier(BaseModel):
    type: str = Field(..., pattern="^(order_id|invoice_id|customer_id)$")
    value: str = Field(..., min_length=1, max_length=100)


class SupportRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)  # allow short greetings ("Hi")
    identifier: CustomerIdentifier | None = None
    rejection_context: dict | None = None
    session_id: str | None = None  # optional; enables conversation memory


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
    final_response: str            # customer-facing; "agent will follow up" when held
    confidence_score: float
    confidence_label: str          # High | Medium | Low — review UI only
    review_required: bool
    escalation_needed: bool
    escalation_summary: dict
    issue_type: str | None = None
    route: str = "customer_issue"  # greeting | general_knowledge | customer_issue | hybrid
    rag_sources: list[str] = []    # source doc names from Mini-RAG
    transparency_data: TransparencyData
    missing_fields: list[str] = []


# ── Endpoint ─────────────────────────────────────────────────────

_REVIEW_HOLD_AR = "\u0633\u064a\u062a\u0648\u0627\u0635\u0644 \u0645\u0639\u0643 \u0623\u062d\u062f \u0623\u0641\u0631\u0627\u062f \u0641\u0631\u064a\u0642 \u0627\u0644\u062f\u0639\u0645 \u0642\u0631\u064a\u0628\u0627\u064b \u0644\u0644\u0645\u062a\u0627\u0628\u0639\u0629."
_REVIEW_HOLD_EN = "An agent will follow up with you shortly."


@router.post("", response_model=SupportResponse)
async def handle_support_request(
    request: SupportRequest,
) -> SupportResponse:
    """Process a customer support query \u2014 public endpoint (no auth required).

    Routes through the M3 agent graph (intent router \u2192 RAG / CRM pipeline).
    When review_required=True the customer-facing final_response is replaced
    with a neutral waiting message; the draft stays in transparency_data for
    the agent review panel only.
    """
    logger.info(
        "support_request_received",
        has_identifier=request.identifier is not None,
        has_session=request.session_id is not None,
        query_length=len(request.query),
    )

    try:
        from agents.m3.graphs.m3_graph import support_graph

        # Load prior conversation turns for session memory
        chat_history: list[dict] = []
        if request.session_id:
            chat_history = await load_conversation_history(request.session_id)

        identifier = request.identifier.model_dump() if request.identifier else None
        initial_state = build_initial_state(query=request.query, identifier=identifier)
        if request.rejection_context:
            initial_state["rejection_context"] = request.rejection_context
        if chat_history:
            initial_state["chat_history"] = chat_history

        result: dict = await support_graph.ainvoke(initial_state)

        fetched = result.get("fetched_data") or {}
        confidence = float(result.get("confidence_score", 0.0))
        review_required = bool(result.get("review_required", False))
        escalation_needed = bool(result.get("escalation_needed", False))
        draft = result.get("draft_response", "")
        final = result.get("final_response", "")

        # Review-hold shaping: hide the draft from the customer
        lang = result.get("language", "en") or "en"
        if review_required and not escalation_needed:
            final = _REVIEW_HOLD_AR if lang == "ar" else _REVIEW_HOLD_EN

        # Persist this turn for session memory
        if request.session_id:
            await append_conversation_turn(
                session_id=request.session_id,
                user_message=request.query,
                assistant_message=final,
            )

        logger.info(
            "support_request_completed",
            route=result.get("route", "customer_issue"),
            data_completeness=result.get("data_completeness", 0.0),
            escalation_needed=escalation_needed,
            review_required=review_required,
        )

        return SupportResponse(
            draft_response=draft,
            final_response=final,
            confidence_score=confidence,
            confidence_label=get_confidence_label(confidence),
            review_required=review_required,
            escalation_needed=escalation_needed,
            escalation_summary=result.get("escalation_summary", {}),
            issue_type=result.get("issue_type"),
            route=result.get("route", "customer_issue"),
            rag_sources=result.get("rag_sources", []),
            transparency_data=TransparencyData(
                invoice=fetched.get("invoice"),
                order=fetched.get("order"),
                shipping=fetched.get("shipping"),
                history=fetched.get("history"),
            ),
            missing_fields=result.get("missing_fields", []),
        )

    except Exception as exc:
        logger.error("support_request_failed", error=str(exc))

        lang = "ar" if any("\u0600" <= c <= "\u06FF" for c in request.query) else "en"
        message = (
            "\u062d\u062f\u062b \u062e\u0637\u0623 \u0623\u062b\u0646\u0627\u0621 \u0645\u0639\u0627\u0644\u062c\u0629 \u0637\u0644\u0628\u0643. \u0633\u064a\u062a\u0648\u0627\u0635\u0644 \u0645\u0639\u0643 \u0641\u0631\u064a\u0642 \u0627\u0644\u062f\u0639\u0645 \u0642\u0631\u064a\u0628\u0627\u064b."
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
            route="customer_issue",
            rag_sources=[],
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

"""
M2 RFQ endpoints.

GET  /api/v1/m2/rfqs                    — list all RFQs with status
POST /api/v1/m2/rfqs/{rfq_id}/approve  — approve or reject a pending RFQ,
                                         then resume the LangGraph so it
                                         either sends the RFQ or stops.

Approval flow (Sprint 6):
  1. m2_analyze runs graph → pauses before human_approval_node → rfq saved with status='draft'
  2. Manager calls this endpoint with approval_status='approved'|'rejected'
  3. Endpoint injects approval_status into the checkpointed graph state via aupdate_state()
  4. Endpoint resumes the graph via ainvoke(None, config)
  5. Graph: human_approval_node reads state → route → rfq_send_node (if approved) → END
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db_session, get_db_session_dep
from backend.models.m2_rfq import RFQ
from backend.schemas.m2_rfq import (
    ApproveRFQRequest,
    ApproveRFQResponse,
    RFQListItem,
    RFQListResponse,
)

router = APIRouter(prefix="/m2/rfqs", tags=["M2 RFQs"])

_APPROVAL_MESSAGES = {
    "approved": "RFQ approved and sent to supplier.",
    "rejected": "RFQ rejected.",
}


@router.get("", response_model=RFQListResponse)
async def list_rfqs(
    session: AsyncSession = Depends(get_db_session_dep),
) -> Any:
    """Returns all RFQs ordered by creation date (newest first)."""
    result = await session.execute(select(RFQ).order_by(RFQ.created_at.desc()))
    rfqs = result.scalars().all()

    items = [
        RFQListItem(
            id=r.id,
            product_id=r.product_id,
            quantity=r.quantity,
            unit=r.unit,
            status=r.status,
            thread_id=r.thread_id,
            alert_id=r.alert_id,
            draft_preview=(r.draft_text or "")[:200] or None,
            created_at=r.created_at,
        )
        for r in rfqs
    ]
    return RFQListResponse(rfqs=items, total=len(items))


@router.post("/{rfq_id}/approve", response_model=ApproveRFQResponse)
async def approve_rfq(
    rfq_id: uuid.UUID,
    body: ApproveRFQRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_db_session_dep),
) -> Any:
    """
    Approve or reject an RFQ, then resume the paused LangGraph thread.

    When the graph resumes:
      - approved → rfq_send_node updates status='sent' + fires mock webhook
      - rejected → graph ends, status stays 'rejected' (set below as fallback)
    """
    # ── 1. Load RFQ ───────────────────────────────────────────────
    result = await session.execute(select(RFQ).where(RFQ.id == rfq_id))
    rfq = result.scalar_one_or_none()

    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if rfq.status not in ("draft", "pending"):
        raise HTTPException(status_code=409, detail=f"RFQ is already '{rfq.status}'")
    if not rfq.thread_id:
        raise HTTPException(
            status_code=409,
            detail="RFQ has no associated graph thread — cannot resume.",
        )

    # ── 2. Resume graph via checkpointer ─────────────────────────
    m2_graph = getattr(http_request.app.state, "m2_graph", None)
    sent = False

    if m2_graph is not None:
        config = {"configurable": {"thread_id": rfq.thread_id}}

        # Inject the approval decision into the checkpointed state
        await m2_graph.aupdate_state(
            config,
            {
                "approval_status": body.approval_status,
                "approval_notes": body.notes or "",
            },
        )

        # Resume — graph runs human_approval_node → route → rfq_send_node (or END)
        await m2_graph.ainvoke(None, config=config)
        sent = body.approval_status == "approved"

    else:
        # No checkpointer available (e.g. running tests without lifespan).
        # Fall back: update DB status manually.
        new_status = "sent" if body.approval_status == "approved" else "rejected"
        async with get_db_session() as db:
            await db.execute(
                update(RFQ).where(RFQ.id == rfq_id).values(status=new_status)
            )
        sent = body.approval_status == "approved"

    return ApproveRFQResponse(
        rfq_id=rfq_id,
        approval_status=body.approval_status,
        message=_APPROVAL_MESSAGES[body.approval_status],
        sent=sent,
    )

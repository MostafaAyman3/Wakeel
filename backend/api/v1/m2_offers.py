"""
M2 Offers endpoints.

POST /api/v1/m2/offers
  Receives supplier offers for a sent RFQ, saves them to DB, then resumes
  the paused LangGraph thread so OfferAnalysisNode can run.

GET  /api/v1/m2/offers/{rfq_id}
  Returns all offers saved for a given RFQ (for the Dashboard table).

Offer intake flow (Sprint 7):
  1. RFQ is sent (status='sent') — graph paused inside await_offers_node.
  2. Procurement officer submits offers via this endpoint.
  3. Offers are persisted to supplier_offers table.
  4. Graph is resumed with Command(resume={"supplier_offers": [...]}).
  5. offer_analysis_node runs (GPT-4o) → recommended_offer returned.
  6. Graph pauses again before final_approval_node.
  7. Manager calls POST /rfqs/{id}/approve for final sign-off.

vendor_id mapping:
  vendor_id is derived deterministically from vendor_name using uuid5
  so the same vendor always maps to the same UUID — no vendor pre-registration needed.
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from langgraph.types import Command
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db_session_dep
from backend.models.m2_rfq import RFQ
from backend.models.m2_supplier_offer import SupplierOffer
from backend.schemas.m2_offers import (
    OfferListItem,
    RecommendedOffer,
    SubmitOffersRequest,
    SubmitOffersResponse,
)

router = APIRouter(prefix="/m2/offers", tags=["M2 Offers"])

# Namespace UUID for deterministic vendor_id generation
_VENDOR_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def _vendor_uuid(vendor_name: str) -> uuid.UUID:
    """Derive a stable UUID from vendor name — no pre-registration required."""
    return uuid.uuid5(_VENDOR_NS, vendor_name.strip().lower())


@router.post("", response_model=SubmitOffersResponse)
async def submit_offers(
    body: SubmitOffersRequest,
    http_request: Request,
    session: AsyncSession = Depends(get_db_session_dep),
) -> Any:
    """
    Submit supplier offers for a sent RFQ, then resume the LangGraph thread
    to trigger OfferAnalysisNode.
    """
    # ── 1. Validate RFQ ───────────────────────────────────────────
    result = await session.execute(select(RFQ).where(RFQ.id == body.rfq_id))
    rfq = result.scalar_one_or_none()

    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if rfq.status != "sent":
        raise HTTPException(
            status_code=409,
            detail=f"RFQ is '{rfq.status}' — offers can only be submitted for 'sent' RFQs",
        )
    if not rfq.thread_id:
        raise HTTPException(
            status_code=409,
            detail="RFQ has no graph thread — cannot resume analysis",
        )

    # ── 2. Persist offers to DB ───────────────────────────────────
    saved_offers = []
    offer_dicts = []

    for item in body.offers:
        vendor_id = _vendor_uuid(item.vendor_name)
        total = item.price_per_unit * (rfq.quantity or 1)

        db_offer = SupplierOffer(
            rfq_id=rfq.id,
            vendor_id=vendor_id,
            price_per_unit=item.price_per_unit,
            total_price=total,
            lead_time_days=item.lead_time_days,
            payment_terms=item.payment_terms,
            notes=item.notes,
            raw_message=item.notes,
        )
        session.add(db_offer)
        saved_offers.append(db_offer)

        offer_dicts.append({
            "vendor_name":    item.vendor_name,
            "vendor_id":      str(vendor_id),
            "price_per_unit": item.price_per_unit,
            "total_price":    total,
            "lead_time_days": item.lead_time_days,
            "payment_terms":  item.payment_terms,
            "notes":          item.notes,
        })

    await session.commit()

    # ── 3. Resume graph with offers ───────────────────────────────
    m2_graph = getattr(http_request.app.state, "m2_graph", None)
    recommended: RecommendedOffer | None = None
    analysis_triggered = False

    if m2_graph is not None:
        config = {"configurable": {"thread_id": rfq.thread_id}}

        # Resume await_offers_node — pass offers via Command(resume=...)
        graph_result = await m2_graph.ainvoke(
            Command(resume={"supplier_offers": offer_dicts}),
            config=config,
        )

        analysis_triggered = True

        rec = graph_result.get("recommended_offer", {})
        justification = graph_result.get("pricing_recommendation", "")

        if rec:
            recommended = RecommendedOffer(
                vendor_name=rec.get("vendor_name", ""),
                price_per_unit=rec.get("price_per_unit", 0),
                lead_time_days=rec.get("lead_time_days"),
                score=rec.get("score", 0),
                justification=justification,
            )
    else:
        # No checkpointer — dev fallback: just save offers, no graph resume
        analysis_triggered = False

    return SubmitOffersResponse(
        rfq_id=body.rfq_id,
        offers_saved=len(saved_offers),
        analysis_triggered=analysis_triggered,
        recommended_offer=recommended,
        message=(
            f"{len(saved_offers)} offer(s) saved. "
            + ("Analysis complete — awaiting final approval." if analysis_triggered
               else "Analysis skipped (no graph available).")
        ),
    )


@router.get("/{rfq_id}", response_model=list[OfferListItem])
async def list_offers_for_rfq(
    rfq_id: uuid.UUID,
    session: AsyncSession = Depends(get_db_session_dep),
) -> Any:
    """Returns all offers submitted for a given RFQ."""
    result = await session.execute(
        select(SupplierOffer)
        .where(SupplierOffer.rfq_id == rfq_id)
        .order_by(SupplierOffer.received_at.asc())
    )
    offers = result.scalars().all()

    return [
        OfferListItem(
            id=o.id,
            rfq_id=o.rfq_id,
            vendor_name=None,        # not stored in DB, lookup via vendor_id if needed
            price_per_unit=float(o.price_per_unit),
            lead_time_days=o.lead_time_days,
            payment_terms=o.payment_terms,
            received_at=o.received_at,
        )
        for o in offers
    ]

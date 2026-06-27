"""
RFQSendNode — executes the send action after manager approves an RFQ.

Sprint 6: mock webhook — logs the full payload and updates rfqs.status = 'sent'.
Sprint 9: real httpx POST to n8n webhook URL (N8N_RFQ_WEBHOOK_URL in .env).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import httpx
from sqlalchemy import update

from agents.m2.schemas.m2_state import M2State
from backend.core.config import get_settings
from backend.core.database import get_db_session
from backend.models.m2_rfq import RFQ

logger = logging.getLogger(__name__)


async def _fire_webhook(payload: Dict[str, Any]) -> None:
    """
    POSTs the RFQ payload to n8n if N8N_RFQ_WEBHOOK_URL is configured.
    Falls back to logging when the URL is empty (dev / tests).
    """
    webhook_url = get_settings().n8n_rfq_webhook_url

    if not webhook_url:
        logger.info(
            "rfq_webhook_skipped_no_url",
            extra={"rfq_id": payload.get("rfq_id"), "product": payload.get("product_name")},
        )
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
        logger.info("rfq_webhook_fired", extra={"rfq_id": payload.get("rfq_id"), "status": resp.status_code})
    except Exception as exc:
        logger.warning("rfq_webhook_failed", extra={"rfq_id": payload.get("rfq_id"), "error": str(exc)})


async def rfq_send_node(state: M2State) -> Dict[str, Any]:
    """
    1. Updates rfqs.status = 'sent' in the DB.
    2. Fires a mock webhook payload (real n8n call in Sprint 9).
    3. Returns final_response update with sent metadata.
    """
    rfq_id = state.get("rfq_id", "")
    current_product = state.get("current_product", {})
    sent_at = datetime.now(timezone.utc).isoformat()

    # ── 1. Persist status ─────────────────────────────────────────
    if rfq_id:
        async with get_db_session() as session:
            await session.execute(
                update(RFQ)
                .where(RFQ.id == uuid.UUID(rfq_id))
                .values(status="sent")
            )

    # ── 2. Build webhook payload ──────────────────────────────────
    # vendor_email / vendor_name were written to state by rfq_builder_node.
    # Fall back to DB lookup if the graph was resumed from a checkpoint
    # and the in-memory state no longer holds them.
    vendor_email = state.get("vendor_email", "")
    vendor_name  = state.get("vendor_name", "")

    if (not vendor_email) and rfq_id:
        async with get_db_session() as session:
            from sqlalchemy import select
            row = (await session.execute(
                select(RFQ.vendor_email, RFQ.vendor_name)
                .where(RFQ.id == uuid.UUID(rfq_id))
            )).first()
            if row:
                vendor_email = row.vendor_email or ""
                vendor_name  = row.vendor_name  or ""

    webhook_payload = {
        "event": "rfq_sent",
        "rfq_id": rfq_id,
        "vendor_email": vendor_email,
        "vendor_name": vendor_name,
        "product_id": current_product.get("product_id", ""),
        "product_name": current_product.get("name", ""),
        "product_name_ar": current_product.get("name_ar", ""),
        "sku": current_product.get("sku", ""),
        "suggested_quantity": current_product.get("suggested_quantity", 0),
        "unit": "unit",
        "rfq_draft": state.get("rfq_draft", ""),
        "approval_notes": state.get("approval_notes", ""),
        "sent_at": sent_at,
    }
    await _fire_webhook(webhook_payload)

    # ── 3. Return state update ────────────────────────────────────
    return {
        "final_response": {
            **state.get("final_response", {}),
            "rfq_sent": True,
            "rfq_id": rfq_id,
            "sent_at": sent_at,
        }
    }

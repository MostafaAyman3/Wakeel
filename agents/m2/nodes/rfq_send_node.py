"""
RFQSendNode — executes the send action after manager approves an RFQ.

Sprint 6: mock webhook — logs the full payload and updates rfqs.status = 'sent'.
Sprint 9: replace _fire_mock_webhook() with a real httpx POST to the n8n
          webhook URL that triggers Email Node → supplier email.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import update

from backend.core.database import get_db_session
from backend.models.m2_rfq import RFQ
from agents.m2.schemas.m2_state import M2State

logger = logging.getLogger(__name__)


async def _fire_mock_webhook(payload: Dict[str, Any]) -> None:
    """
    Sprint 6 stub.  Sprint 9 replaces this body with:
        async with httpx.AsyncClient() as client:
            await client.post(settings.n8n_rfq_webhook_url, json=payload, timeout=10)
    """
    logger.info(
        "rfq_mock_webhook_fired",
        extra={
            "rfq_id": payload.get("rfq_id"),
            "product": payload.get("product_name"),
            "quantity": payload.get("suggested_quantity"),
        },
    )


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

    # ── 2. Mock webhook ───────────────────────────────────────────
    webhook_payload = {
        "event": "rfq_sent",
        "rfq_id": rfq_id,
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
    await _fire_mock_webhook(webhook_payload)

    # ── 3. Return state update ────────────────────────────────────
    return {
        "final_response": {
            **state.get("final_response", {}),
            "rfq_sent": True,
            "rfq_id": rfq_id,
            "sent_at": sent_at,
        }
    }

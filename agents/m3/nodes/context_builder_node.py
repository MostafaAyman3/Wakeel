"""
ContextBuilderNode — merges fetched_data into a structured context dict for the LLM.

Output context schema:
{
  customer_name, identifier_used,
  invoice: { number, date, amount, status, line_items },
  order:   { id, status, items, estimated_delivery },
  shipping:{ carrier, tracking, location },
  history: [ { date, issue_type, resolution } ],
  missing_fields (if data_completeness < 1.0)
}

Blueprint reference: M3_Sprints.md Sprint 2 — ContextBuilderNode
"""

from __future__ import annotations

from typing import Any

import structlog

from agents.m3.schemas.m3_state import M3State

logger = structlog.get_logger(__name__)


def _pick_name(customer: dict | None) -> str:
    """Return Arabic name if available, else English name, else 'Customer'."""
    if not customer:
        return "Customer"
    return customer.get("name_ar") or customer.get("name") or "Customer"


def _build_invoice_context(invoice: dict | None) -> dict | None:
    if not invoice:
        return None
    return {
        "number": invoice.get("display_id"),
        "date": invoice.get("invoice_date"),
        "amount": invoice.get("total_amount"),
        "status": invoice.get("payment_status"),
        "type": invoice.get("type"),
        "line_items": invoice.get("line_items", []),
    }


def _build_order_context(order: dict | None) -> dict | None:
    if not order:
        return None
    return {
        "id": order.get("display_id") or order.get("id"),
        "status": order.get("status"),
        "total_amount": order.get("total_amount"),
        "estimated_delivery": order.get("estimated_delivery"),
        "created_at": order.get("created_at"),
    }


def _build_shipping_context(shipping: Any) -> list[dict] | None:
    """Normalize shipping to a list of dicts."""
    if not shipping:
        return None
    if isinstance(shipping, dict):
        shipping = [shipping]
    return [
        {
            "tracking": s.get("tracking_id"),
            "carrier": s.get("carrier"),
            "location": s.get("location"),
            "status": s.get("status"),
            "last_update": s.get("last_update"),
        }
        for s in shipping
    ]


def _build_history_context(history: list[dict] | None) -> list[dict] | None:
    if not history:
        return None
    return [
        {
            "date": h.get("date"),
            "issue_type": h.get("issue_type"),
            "resolution": h.get("resolution"),
            "interaction_type": h.get("interaction_type"),
        }
        for h in history
    ]


async def build_context(state: M3State) -> dict:
    """Build structured context from fetched_data and identifier info."""
    identifier: dict = state.get("customer_identifier", {})
    fetched: dict = state.get("fetched_data", {})
    missing: list[str] = state.get("missing_fields", [])
    completeness: float = state.get("data_completeness", 0.0)

    # Customer info may be embedded in invoice or order data
    invoice = fetched.get("invoice")
    order = fetched.get("order")
    customer_name = None

    # Try to derive customer name from available data
    if invoice and invoice.get("customer_id"):
        customer_name = f"Customer ({invoice['customer_id'][:8]}...)"
    if order and order.get("customer_id"):
        customer_name = f"Customer ({order['customer_id'][:8]}...)"

    context = {
        "customer_name": customer_name or "Customer",
        "identifier_used": identifier,
        "invoice": _build_invoice_context(invoice),
        "order": _build_order_context(order),
        "shipping": _build_shipping_context(fetched.get("shipping")),
        "history": _build_history_context(fetched.get("history")),
    }

    if completeness < 1.0 and missing:
        context["missing_fields"] = missing

    logger.info("context_built",
                customer_name=context["customer_name"],
                has_invoice=context["invoice"] is not None,
                has_order=context["order"] is not None,
                has_shipping=context["shipping"] is not None,
                has_history=context["history"] is not None)

    return {"context": context}

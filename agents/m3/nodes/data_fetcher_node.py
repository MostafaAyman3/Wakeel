"""
DataFetcherNode — fetches data from 4 sources in parallel.

  - invoice_data      → REAL PostgreSQL (invoices table)
  - order_status      → MOCK in-memory
  - shipping_status   → MOCK in-memory
  - customer_history  → MOCK in-memory

Blueprint reference: M3_Sprints.md Sprint 1 — DataFetcherNode
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from sqlalchemy import text

from agents.m3.schemas.m3_state import M3State
from agents.m3.data import mock_data as m3_mock
from backend.repositories import m3_repository as repo
from backend.core.database import get_db_session

logger = structlog.get_logger(__name__)


async def fetch_data(state: M3State) -> dict:
    """Fetch all data for the identified customer/order/invoice."""
    identifier: dict = state.get("customer_identifier", {})
    id_type: str = identifier.get("type", "")
    id_value: str = identifier.get("value", "")

    result: dict[str, Any] = {
        "fetched_data": {
            "invoice": None,
            "order": None,
            "shipping": None,
            "history": None,
        },
    }

    await m3_mock.ensure_loaded()

    async with get_db_session() as session:
        if id_type == "invoice_id":
            result = await _fetch_by_invoice(session, id_value, result)
        elif id_type == "order_id":
            result = await _fetch_by_order(session, id_value, result)
        elif id_type == "customer_id":
            result = await _fetch_by_customer(session, id_value, result)

    return result


async def _fetch_by_invoice(session, invoice_display_id: str, result: dict) -> dict:
    """Fetch data using invoice display_id (e.g. INV-890)."""
    invoice = await repo.fetch_invoice_by_display_id(session, invoice_display_id)
    if not invoice:
        return result
    result["fetched_data"]["invoice"] = invoice

    customer_id = invoice.get("customer_id")
    if customer_id:
        order = await _fetch_order_by_customer(session, customer_id)
        result["fetched_data"]["order"] = order
        if order:
            shipping = m3_mock.get_shipping_status(order["id"])
            result["fetched_data"]["shipping"] = shipping or None
        history = m3_mock.get_customer_history(customer_id)
        result["fetched_data"]["history"] = history or None

    return result


async def _fetch_by_order(session, order_display_id: str, result: dict) -> dict:
    """Fetch data using order display_id (e.g. ORD-2024-1567)."""
    order_uuid = await repo.resolve_order_display_id(session, order_display_id)
    if not order_uuid:
        return result

    invoice_task = repo.fetch_invoice_by_order_id(session, order_uuid)
    order_task = _fetch_order_by_uuid(session, order_uuid)
    invoice, order_data = await asyncio.gather(invoice_task, order_task)

    result["fetched_data"]["invoice"] = invoice
    result["fetched_data"]["order"] = order_data

    shipping = m3_mock.get_shipping_status(order_uuid)
    result["fetched_data"]["shipping"] = shipping or None

    customer_id = None
    if order_data:
        customer_id = order_data.get("customer_id")
    elif invoice:
        customer_id = invoice.get("customer_id")

    if customer_id:
        history = m3_mock.get_customer_history(customer_id)
        result["fetched_data"]["history"] = history or None

    return result


async def _fetch_by_customer(session, customer_display_id: str, result: dict) -> dict:
    """Fetch data using customer display_id (e.g. CUST-001)."""
    customer = await repo.fetch_customer_by_display_id(session, customer_display_id)
    if not customer:
        return result

    customer_uuid = customer["id"]

    invoice_task = _fetch_latest_invoice(session, customer_uuid)
    order_task = _fetch_order_by_customer(session, customer_uuid)
    invoice, order_data = await asyncio.gather(invoice_task, order_task)

    result["fetched_data"]["invoice"] = invoice
    result["fetched_data"]["order"] = order_data

    if order_data:
        shipping = m3_mock.get_shipping_status(order_data["id"])
        result["fetched_data"]["shipping"] = shipping or None

    history = m3_mock.get_customer_history(customer_uuid)
    result["fetched_data"]["history"] = history or None

    return result


async def _fetch_order_by_uuid(session, order_uuid: str) -> dict | None:
    """Fetch order details by UUID."""
    row = await session.execute(text("""
        SELECT
            id::text, display_id, customer_id::text,
            status, total_amount, estimated_delivery, created_at
        FROM orders WHERE id = :uuid::uuid
    """), {"uuid": order_uuid})
    r = row.fetchone()
    if not r:
        return None
    return {
        "id": r.id,
        "display_id": r.display_id,
        "customer_id": r.customer_id,
        "status": r.status,
        "total_amount": float(r.total_amount) if r.total_amount else 0.0,
        "estimated_delivery": r.estimated_delivery.isoformat() if r.estimated_delivery else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


async def _fetch_order_by_customer(session, customer_uuid: str) -> dict | None:
    """Fetch latest order for a customer."""
    row = await session.execute(text("""
        SELECT
            id::text, display_id, customer_id::text,
            status, total_amount, estimated_delivery, created_at
        FROM orders
        WHERE customer_id = :uuid::uuid
        ORDER BY created_at DESC LIMIT 1
    """), {"uuid": customer_uuid})
    r = row.fetchone()
    if not r:
        return None
    return {
        "id": r.id,
        "display_id": r.display_id,
        "customer_id": r.customer_id,
        "status": r.status,
        "total_amount": float(r.total_amount) if r.total_amount else 0.0,
        "estimated_delivery": r.estimated_delivery.isoformat() if r.estimated_delivery else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


async def _fetch_latest_invoice(session, customer_uuid: str) -> dict | None:
    """Fetch most recent invoice for a customer."""
    invoices = await repo.fetch_invoice_by_customer_id(session, customer_uuid)
    return invoices[0] if invoices else None

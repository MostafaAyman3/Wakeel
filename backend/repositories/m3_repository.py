"""
M3 Repository — data access layer for the Customer Support Agent.

Invoice data comes from REAL PostgreSQL tables.
Order/Shipping/History come from MOCK in-memory data stores.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from agents.m3.data import mock_data
from backend.core.logging import get_logger

logger = get_logger(__name__)


# ── Real DB queries ────────────────────────────────────────────────

async def fetch_invoice_by_display_id(session, display_id: str) -> dict | None:
    """Fetch invoice by display_id (e.g. INV-890). Returns dict or None."""
    row = await session.execute(text("""
        SELECT
            i.id::text,
            i.display_id,
            i.type,
            i.customer_id::text,
            i.invoice_date,
            i.total_amount,
            i.tax_amount,
            i.due_date,
            i.payment_status,
            i.notes,
            COALESCE(
                jsonb_agg(
                    jsonb_build_object(
                        'description',  ii.description,
                        'quantity',     ii.quantity,
                        'unit_price',   ii.unit_price,
                        'total_price',  ii.total_price,
                        'tax_amount',   ii.tax_amount
                    )
                ) FILTER (WHERE ii.id IS NOT NULL),
                '[]'::jsonb
            ) AS line_items
        FROM invoices i
        LEFT JOIN invoice_items ii ON ii.invoice_id = i.id
        WHERE i.display_id = :display_id
        GROUP BY i.id
    """), {"display_id": display_id})
    row_data = row.fetchone()
    if not row_data:
        return None
    return {
        "id": row_data.id,
        "display_id": row_data.display_id,
        "type": row_data.type,
        "customer_id": row_data.customer_id,
        "invoice_date": row_data.invoice_date.isoformat() if row_data.invoice_date else None,
        "total_amount": float(row_data.total_amount) if row_data.total_amount else 0.0,
        "tax_amount": float(row_data.tax_amount) if row_data.tax_amount else 0.0,
        "due_date": row_data.due_date.isoformat() if row_data.due_date else None,
        "payment_status": row_data.payment_status,
        "notes": row_data.notes,
        "line_items": row_data.line_items,
    }


async def fetch_invoice_by_order_id(session, order_id: str) -> dict | None:
    """Fetch invoice by order UUID. Returns dict or None."""
    row = await session.execute(text("""
        SELECT
            i.id::text,
            i.display_id,
            i.type,
            i.customer_id::text,
            i.invoice_date,
            i.total_amount,
            i.tax_amount,
            i.due_date,
            i.payment_status
        FROM invoices i
        WHERE i.order_id = :order_id::uuid
        LIMIT 1
    """), {"order_id": order_id})
    row_data = row.fetchone()
    if not row_data:
        return None
    return {
        "id": row_data.id,
        "display_id": row_data.display_id,
        "type": row_data.type,
        "customer_id": row_data.customer_id,
        "invoice_date": row_data.invoice_date.isoformat() if row_data.invoice_date else None,
        "total_amount": float(row_data.total_amount) if row_data.total_amount else 0.0,
        "tax_amount": float(row_data.tax_amount) if row_data.tax_amount else 0.0,
        "due_date": row_data.due_date.isoformat() if row_data.due_date else None,
        "payment_status": row_data.payment_status,
    }


async def fetch_invoice_by_customer_id(session, customer_id: str) -> list[dict]:
    """Fetch all invoices for a customer UUID. Returns list of dicts."""
    rows = await session.execute(text("""
        SELECT
            i.id::text,
            i.display_id,
            i.type,
            i.invoice_date,
            i.total_amount,
            i.payment_status
        FROM invoices i
        WHERE i.customer_id = :customer_id::uuid
        ORDER BY i.invoice_date DESC
        LIMIT 20
    """), {"customer_id": customer_id})
    return [
        {
            "id": r.id,
            "display_id": r.display_id,
            "type": r.type,
            "invoice_date": r.invoice_date.isoformat() if r.invoice_date else None,
            "total_amount": float(r.total_amount) if r.total_amount else 0.0,
            "payment_status": r.payment_status,
        }
        for r in await rows.fetchall()
    ]


async def fetch_customer_by_display_id(session, display_id: str) -> dict | None:
    """Fetch customer by display_id (e.g. CUST-001). Returns dict or None."""
    row = await session.execute(text("""
        SELECT id::text, display_id, name, name_ar, email, phone, city, tier
        FROM customers
        WHERE display_id = :display_id
        LIMIT 1
    """), {"display_id": display_id})
    r = row.fetchone()
    if not r:
        return None
    return {
        "id": r.id,
        "display_id": r.display_id,
        "name": r.name,
        "name_ar": r.name_ar,
        "email": r.email,
        "phone": r.phone,
        "city": r.city,
        "tier": r.tier,
    }


async def fetch_customer_by_id(session, customer_id: str) -> dict | None:
    """Fetch customer by UUID string."""
    row = await session.execute(text("""
        SELECT id::text, display_id, name, name_ar, email, phone, city, tier
        FROM customers
        WHERE id = :id::uuid
        LIMIT 1
    """), {"id": customer_id})
    r = row.fetchone()
    if not r:
        return None
    return {
        "id": r.id,
        "display_id": r.display_id,
        "name": r.name,
        "name_ar": r.name_ar,
        "email": r.email,
        "phone": r.phone,
        "city": r.city,
        "tier": r.tier,
    }


async def resolve_order_display_id(session, display_id: str) -> str | None:
    """Resolve order display_id (e.g. ORD-2024-1567) to UUID string. Returns None if not found."""
    row = await session.execute(text("""
        SELECT id::text FROM orders WHERE display_id = :display_id LIMIT 1
    """), {"display_id": display_id})
    r = row.fetchone()
    return r.id if r else None


async def resolve_invoice_display_id(session, display_id: str) -> str | None:
    """Resolve invoice display_id (e.g. INV-890) to UUID string. Returns None if not found."""
    row = await session.execute(text("""
        SELECT id::text FROM invoices WHERE display_id = :display_id LIMIT 1
    """), {"display_id": display_id})
    r = row.fetchone()
    return r.id if r else None


async def resolve_customer_display_id(session, display_id: str) -> str | None:
    """Resolve customer display_id (e.g. CUST-001) to UUID string. Returns None if not found."""
    row = await session.execute(text("""
        SELECT id::text FROM customers WHERE display_id = :display_id LIMIT 1
    """), {"display_id": display_id})
    r = row.fetchone()
    return r.id if r else None


# ── Mock data queries ──────────────────────────────────────────────

def fetch_order_status_from_mock(order_id: str) -> dict | None:
    """Fetch order_status from mock data by order UUID string."""
    return mock_data.get_order_status(order_id)


def fetch_shipping_from_mock(order_id: str) -> list[dict] | None:
    """Fetch shipping records from mock data by order UUID string."""
    return mock_data.get_shipping_status(order_id)


def fetch_customer_history_from_mock(customer_id: str) -> list[dict] | None:
    """Fetch customer history from mock data by customer UUID string."""
    return mock_data.get_customer_history(customer_id)


# ── Composite fetchers ─────────────────────────────────────────────

async def fetch_all_invoice_data(session, identifier: dict) -> dict | None:
    """Fetch invoice data based on identifier type and value."""
    id_type = identifier.get("type", "")
    id_value = identifier.get("value", "")

    if id_type == "invoice_id":
        return await fetch_invoice_by_display_id(session, id_value)
    elif id_type == "order_id":
        order_uuid = await resolve_order_display_id(session, id_value)
        if order_uuid:
            return await fetch_invoice_by_order_id(session, order_uuid)
    elif id_type == "customer_id":
        cust = await fetch_customer_by_display_id(session, id_value)
        if cust:
            invoices = await fetch_invoice_by_customer_id(session, cust["id"])
            return invoices[0] if invoices else None
    return None

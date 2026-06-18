"""
M3 Mock Data — in-memory data store for order_status, shipping, and customer_history.

Populated lazily from real DB tables + test scenario overrides.
Follows the M3_Sprints.md mock table schemas:
  - order_status:     (order_id, customer_id, status, created_at, estimated_delivery, items)
  - shipping:         (tracking_id, order_id, status, carrier, location, last_update)
  - customer_history: (customer_id, interaction_type, issue_type, resolution, date)
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

import structlog
from sqlalchemy import text

from backend.core.database import get_db_session

logger = structlog.get_logger(__name__)

# ── In-memory data stores ──────────────────────────────────────────
_order_status_map: dict[str, dict[str, Any]] = {}
_shipping_map: dict[str, list[dict[str, Any]]] = {}
_customer_history_map: dict[str, list[dict[str, Any]]] = {}
_loaded: bool = False


async def ensure_loaded() -> None:
    """Load mock data from real DB tables (lazy, once)."""
    global _order_status_map, _shipping_map, _customer_history_map, _loaded
    if _loaded:
        return

    async with get_db_session() as session:
        await _load_from_real_tables(session)
        _add_test_scenarios()

    _loaded = True
    logger.info("m3_mock_data_loaded",
                orders=len(_order_status_map),
                shipping=sum(len(v) for v in _shipping_map.values()),
                history=sum(len(v) for v in _customer_history_map.values()))


async def _load_from_real_tables(session):
    """Populate mock stores from real orders, shipments, customer_interactions tables."""
    rows = await session.execute(text("""
        SELECT
            o.id::text AS order_id,
            o.customer_id::text AS customer_id,
            o.status,
            o.created_at,
            o.estimated_delivery,
            COALESCE(
                jsonb_agg(
                    jsonb_build_object(
                        'product_name',       p.name,
                        'product_name_ar',    p.name_ar,
                        'quantity',           oi.quantity,
                        'unit_price',         oi.unit_price,
                        'total_price',        oi.total_price
                    )
                ) FILTER (WHERE oi.id IS NOT NULL),
                '[]'::jsonb
            ) AS items
        FROM orders o
        LEFT JOIN order_items oi ON oi.order_id = o.id
        LEFT JOIN products p ON p.id = oi.product_id
        GROUP BY o.id
    """))
    for row in await rows.fetchall():
        _order_status_map[row.order_id] = {
            "order_id": row.order_id,
            "customer_id": row.customer_id,
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "estimated_delivery": row.estimated_delivery.isoformat() if row.estimated_delivery else None,
            "items": row.items,
        }

    rows = await session.execute(text("""
        SELECT
            s.tracking_number AS tracking_id,
            s.order_id::text AS order_id,
            s.status,
            s.carrier,
            s.current_location AS location,
            s.updated_at AS last_update
        FROM shipments s
    """))
    for row in await rows.fetchall():
        oid = row.order_id
        if oid not in _shipping_map:
            _shipping_map[oid] = []
        _shipping_map[oid].append({
            "tracking_id": row.tracking_id,
            "order_id": oid,
            "status": row.status,
            "carrier": row.carrier,
            "location": row.location,
            "last_update": row.last_update.isoformat() if row.last_update else None,
        })

    rows = await session.execute(text("""
        SELECT
            ci.customer_id::text AS customer_id,
            ci.interaction_type,
            ci.issue_type,
            ci.resolution,
            ci.created_at AS date
        FROM customer_interactions ci
        ORDER BY ci.created_at DESC
    """))
    for row in await rows.fetchall():
        cid = row.customer_id
        if cid not in _customer_history_map:
            _customer_history_map[cid] = []
        _customer_history_map[cid].append({
            "customer_id": cid,
            "interaction_type": row.interaction_type,
            "issue_type": row.issue_type,
            "resolution": row.resolution,
            "date": row.date.isoformat() if row.date else None,
        })


def _add_test_scenarios():
    """Add test data for demo scenarios."""
    now = datetime.now(timezone.utc)

    repeat_customer_id = None
    for record in _order_status_map.values():
        repeat_customer_id = record["customer_id"]
        break

    if repeat_customer_id:
        if repeat_customer_id not in _customer_history_map:
            _customer_history_map[repeat_customer_id] = []
        existing = _customer_history_map[repeat_customer_id]
        shipping_entries = [e for e in existing if e.get("issue_type") == "shipping_issue"]
        needed = max(0, 3 - len(shipping_entries))
        for i in range(needed):
            days_ago = 30 * (i + 1)
            _customer_history_map[repeat_customer_id].append({
                "customer_id": repeat_customer_id,
                "interaction_type": "complaint",
                "issue_type": "shipping_issue",
                "resolution": "Reimbursed shipping fees" if i > 0 else "Apologized, order re-sent",
                "date": (now - timedelta(days=days_ago)).isoformat(),
            })


# ── Public query functions ─────────────────────────────────────────

def get_order_status(order_id: str) -> dict | None:
    return _order_status_map.get(order_id)


def get_shipping_status(order_id: str) -> list[dict] | None:
    return _shipping_map.get(order_id)


def get_shipping_by_tracking(tracking_id: str) -> dict | None:
    for records in _shipping_map.values():
        for rec in records:
            if rec["tracking_id"] == tracking_id:
                return rec
    return None


def get_customer_history(customer_id: str) -> list[dict] | None:
    return _customer_history_map.get(customer_id)


def is_loaded() -> bool:
    return _loaded

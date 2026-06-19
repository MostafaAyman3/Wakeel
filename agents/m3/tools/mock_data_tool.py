"""
mock_data_tool — fetches the three "mock" support data sources from the DB.

Blueprint terminology (section 3.3): order_status, shipping_status, and
customer_history are "MOCK" sources. In this project they were seeded as real
Supabase tables during M3 Sprint 0, so we read them from PostgreSQL just like
real data — "mock" refers to the data being synthetic, not in-memory.

Actual table names (differ from the sprint spec — see db_schema_reference.md):
    order_status     → orders
    shipping_status  → shipments
    customer_history → customer_interactions

Each fetcher is self-contained and resolves the row(s) for any of the three
identifier types with a single SELECT-only query, so they can run in parallel.
"""

from __future__ import annotations

from sqlalchemy import text

from agents.shared.db_utils import jsonify_row, jsonify_rows
from backend.core.database import get_db_session
from backend.core.logging import get_logger

logger = get_logger(__name__)


# ── Order status (orders table) ──────────────────────────────────────────────

_ORDER_COLS = """
    o.display_id        AS display_id,
    c.display_id        AS customer_id,
    o.status            AS status,
    o.order_date        AS created_at,
    o.estimated_delivery AS estimated_delivery,
    o.total_amount      AS total_amount
"""

_ORDER_QUERIES: dict[str, str] = {
    "order_id": f"""
        SELECT {_ORDER_COLS}
        FROM orders o
        LEFT JOIN customers c ON o.customer_id = c.id
        WHERE o.display_id = :value
        LIMIT 1
    """,
    "invoice_id": f"""
        SELECT {_ORDER_COLS}
        FROM orders o
        JOIN invoices i ON i.order_id = o.id
        LEFT JOIN customers c ON o.customer_id = c.id
        WHERE i.display_id = :value
        LIMIT 1
    """,
    "customer_id": f"""
        SELECT {_ORDER_COLS}
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE c.display_id = :value
        ORDER BY o.order_date DESC
        LIMIT 1
    """,
}


async def fetch_order(identifier: dict) -> dict | None:
    """Fetch order status for the given identifier, or ``None``."""
    return await _fetch_single(identifier, _ORDER_QUERIES, source="order")


# ── Shipping status (shipments table) ────────────────────────────────────────

_SHIP_COLS = """
    s.tracking_number   AS tracking_id,
    o.display_id        AS order_id,
    s.status            AS status,
    s.carrier           AS carrier,
    s.current_location  AS location,
    s.estimated_delivery AS estimated_delivery,
    s.updated_at        AS last_update
"""

_SHIP_QUERIES: dict[str, str] = {
    "order_id": f"""
        SELECT {_SHIP_COLS}
        FROM shipments s
        JOIN orders o ON s.order_id = o.id
        WHERE o.display_id = :value
        ORDER BY s.updated_at DESC
        LIMIT 1
    """,
    "invoice_id": f"""
        SELECT {_SHIP_COLS}
        FROM shipments s
        JOIN orders o ON s.order_id = o.id
        JOIN invoices i ON i.order_id = o.id
        WHERE i.display_id = :value
        ORDER BY s.updated_at DESC
        LIMIT 1
    """,
    "customer_id": f"""
        SELECT {_SHIP_COLS}
        FROM shipments s
        JOIN orders o ON s.order_id = o.id
        JOIN customers c ON o.customer_id = c.id
        WHERE c.display_id = :value
        ORDER BY s.updated_at DESC
        LIMIT 1
    """,
}


async def fetch_shipping(identifier: dict) -> dict | None:
    """Fetch shipping status for the given identifier, or ``None``."""
    return await _fetch_single(identifier, _SHIP_QUERIES, source="shipping")


# ── Customer history (customer_interactions table) ───────────────────────────

_HISTORY_COLS = """
    ci.interaction_type AS interaction_type,
    ci.issue_type       AS issue_type,
    ci.description      AS description,
    ci.resolution       AS resolution,
    ci.status           AS status,
    ci.created_at       AS date
"""

# History returns MULTIPLE rows (needed for Sprint 3 repeat-issue detection).
_HISTORY_QUERIES: dict[str, str] = {
    "customer_id": f"""
        SELECT {_HISTORY_COLS}
        FROM customer_interactions ci
        JOIN customers c ON ci.customer_id = c.id
        WHERE c.display_id = :value
        ORDER BY ci.created_at DESC
    """,
    "order_id": f"""
        SELECT {_HISTORY_COLS}
        FROM customer_interactions ci
        WHERE ci.customer_id = (
            SELECT customer_id FROM orders WHERE display_id = :value LIMIT 1
        )
        ORDER BY ci.created_at DESC
    """,
    "invoice_id": f"""
        SELECT {_HISTORY_COLS}
        FROM customer_interactions ci
        WHERE ci.customer_id = (
            SELECT customer_id FROM invoices WHERE display_id = :value LIMIT 1
        )
        ORDER BY ci.created_at DESC
    """,
}


async def fetch_history(identifier: dict) -> list[dict] | None:
    """Fetch the customer's interaction history, or ``None`` if empty.

    Returns a list of interactions (most recent first). Multiple rows are
    intentional — Sprint 3 uses this for repeat-issue detection.
    """
    id_type = identifier.get("type")
    value = identifier.get("value")
    query = _HISTORY_QUERIES.get(id_type)

    if not query or not value:
        return None

    try:
        async with get_db_session() as session:
            result = await session.execute(text(query), {"value": value})
            rows = result.mappings().all()
            return jsonify_rows(list(rows)) or None
    except Exception as exc:  # noqa: BLE001
        logger.error("history_fetch_failed", identifier=identifier, error=str(exc))
        return None


# ── Shared single-row fetch helper ───────────────────────────────────────────

async def _fetch_single(
    identifier: dict,
    queries: dict[str, str],
    *,
    source: str,
) -> dict | None:
    """Run a single-row SELECT for ``identifier`` against ``queries``.

    Never raises — logs and returns ``None`` on missing data or error.
    """
    id_type = identifier.get("type")
    value = identifier.get("value")
    query = queries.get(id_type)

    if not query or not value:
        return None

    try:
        async with get_db_session() as session:
            result = await session.execute(text(query), {"value": value})
            return jsonify_row(result.mappings().first())
    except Exception as exc:  # noqa: BLE001
        logger.error(f"{source}_fetch_failed", identifier=identifier, error=str(exc))
        return None

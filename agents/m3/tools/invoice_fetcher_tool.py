"""
invoice_fetcher_tool — fetches REAL invoice data from PostgreSQL.

This is the only "REAL" data source in M3 (per blueprint section 3.3):
invoice data comes from the live ``invoices`` + ``customers`` tables that
M1 already populates. Order / shipping / history live in ``mock_data_tool``.

The fetch is self-contained: given a customer identifier of any of the three
supported types, it resolves the right invoice with a single parametrized,
SELECT-only query. This lets DataFetcherNode run all four sources in parallel.
"""

from __future__ import annotations

from sqlalchemy import text

from agents.shared.db_utils import jsonify_row
from backend.core.database import get_db_session
from backend.core.logging import get_logger

logger = get_logger(__name__)

# Columns are aliased to the blueprint's expected response shape:
#   { display_id, total_amount, payment_status, customer_id, customer_name, ... }
_SELECT_COLS = """
    i.display_id     AS display_id,
    i.total_amount   AS total_amount,
    i.tax_amount     AS tax_amount,
    i.payment_status AS payment_status,
    i.invoice_date   AS invoice_date,
    i.due_date       AS due_date,
    c.display_id     AS customer_id,
    c.name           AS customer_name
"""

# One query per identifier type. All are SELECT-only and parametrized.
_QUERIES: dict[str, str] = {
    "invoice_id": f"""
        SELECT {_SELECT_COLS}
        FROM invoices i
        LEFT JOIN customers c ON i.customer_id = c.id
        WHERE i.display_id = :value
        LIMIT 1
    """,
    "order_id": f"""
        SELECT {_SELECT_COLS}
        FROM invoices i
        JOIN orders o ON i.order_id = o.id
        LEFT JOIN customers c ON i.customer_id = c.id
        WHERE o.display_id = :value
        ORDER BY i.invoice_date DESC
        LIMIT 1
    """,
    "customer_id": f"""
        SELECT {_SELECT_COLS}
        FROM invoices i
        JOIN customers c ON i.customer_id = c.id
        WHERE c.display_id = :value
        ORDER BY i.invoice_date DESC
        LIMIT 1
    """,
}


async def fetch_invoice(identifier: dict) -> dict | None:
    """Fetch the most relevant invoice for the given identifier.

    Args:
        identifier: ``{"type": "order_id|invoice_id|customer_id", "value": str}``.

    Returns:
        A JSON-safe invoice dict, or ``None`` if no row matches (or on error).
        Never raises — failures are logged and degrade to ``None``.
    """
    id_type = identifier.get("type")
    value = identifier.get("value")
    query = _QUERIES.get(id_type)

    if not query or not value:
        return None

    try:
        async with get_db_session() as session:
            result = await session.execute(text(query), {"value": value})
            row = result.mappings().first()
            return jsonify_row(row)
    except Exception as exc:  # noqa: BLE001 — one source must not crash the pipeline
        logger.error("invoice_fetch_failed", identifier=identifier, error=str(exc))
        return None

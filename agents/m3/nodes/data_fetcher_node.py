"""
DataFetcherNode — fetches all four customer data sources in parallel.

Sources (blueprint section 3.4):
    invoice   → REAL  (invoices + customers)        — invoice_fetcher_tool
    order     → "MOCK" (orders)                     — mock_data_tool
    shipping  → "MOCK" (shipments)                  — mock_data_tool
    history   → "MOCK" (customer_interactions)      — mock_data_tool

Rules (Sprint 1):
    • All four run concurrently via ``asyncio.gather`` (return_exceptions).
    • A missing source resolves to ``None``.
    • One source failing must not crash the pipeline — its slot becomes
      ``None`` and the error is logged.
"""

from __future__ import annotations

import asyncio

from agents.m3.schemas.m3_state import M3State
from agents.m3.tools.invoice_fetcher_tool import fetch_invoice
from agents.m3.tools.mock_data_tool import fetch_order, fetch_shipping, fetch_history
from backend.core.logging import get_logger

logger = get_logger(__name__)

# Order matters: it maps 1:1 onto the fetched_data keys below.
_SOURCE_KEYS = ("invoice", "order", "shipping", "history")


async def fetch_data(state: M3State) -> dict:
    """Run the four source fetchers concurrently and assemble ``fetched_data``.

    Returns a partial state update. If parsing already escalated (no
    identifier), it skips fetching and leaves ``fetched_data`` empty.
    """
    identifier: dict = state.get("customer_identifier") or {}

    # Upstream parser found no identifier → nothing to fetch.
    if not identifier.get("type") or not identifier.get("value"):
        logger.info("data_fetcher_skipped_no_identifier")
        return {"fetched_data": {key: None for key in _SOURCE_KEYS}}

    logger.info(
        "data_fetcher_start",
        identifier_type=identifier["type"],
        identifier_value=identifier["value"],
    )

    # ── Parallel fetch — one coroutine per source ─────────────────
    results = await asyncio.gather(
        fetch_invoice(identifier),
        fetch_order(identifier),
        fetch_shipping(identifier),
        fetch_history(identifier),
        return_exceptions=True,
    )

    fetched_data: dict = {}
    for key, result in zip(_SOURCE_KEYS, results):
        if isinstance(result, Exception):
            # Defensive: tools already swallow their own errors, but if a
            # coroutine raises before its try/except, gather captures it here.
            logger.error("data_fetcher_source_error", source=key, error=str(result))
            fetched_data[key] = None
        else:
            fetched_data[key] = result

    found = [k for k, v in fetched_data.items() if v]
    logger.info("data_fetcher_done", sources_found=found, total=len(_SOURCE_KEYS))

    return {"fetched_data": fetched_data}

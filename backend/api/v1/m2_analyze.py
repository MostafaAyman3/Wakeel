"""
POST /api/v1/m2/analyze

Triggers the M2 LangGraph for all active products:
  1. inventory_check_node — scans DB, flags products, saves inventory_alerts rows
  2. For each flagged product, runs the graph (per-product thread):
       procurement path (low_stock / predicted_shortage):
         alert_generator_node → rfq_builder_node → [INTERRUPT before human_approval_node]
         Returns: rfq_draft, rfq_id (graph paused, awaiting POST /rfqs/{id}/approve)
       pricing path (slow_moving / near_expiry):
         → END immediately  (PricingAdvisorNode added in Sprint 5)

Sprint 6 additions:
  - Generates a thread_id per product before calling the graph, so each
    RFQ approval can resume the correct checkpoint.
  - Uses app.state.m2_graph (AsyncPostgresSaver) when available; falls back
    to the module-level m2_app (MemorySaver) for dev/tests.
"""

import time
from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import update

from agents.m2.graphs.m2_graph import m2_app
from agents.m2.nodes.inventory_check_node import inventory_check_node
from backend.core.database import get_db_session
from backend.models.m2_inventory_alert import InventoryAlert
from backend.schemas.m2_analyze import (
    AlertData,
    AnalyzeRequest,
    AnalyzeResponse,
    PricingRecData,
    RFQDraftData,
)

router = APIRouter(prefix="/m2", tags=["M2 Analyze"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_inventory(http_request: Request, body: AnalyzeRequest) -> Any:
    """
    Triggers the LangGraph for all active products.

    Returns immediately after all per-product graphs are started.
    Procurement-path graphs are paused at the human approval gate;
    the frontend polls GET /m2/rfqs to show pending RFQs to the manager.
    """
    # ── 1. Inventory scan (no LLM) ────────────────────────────────
    init_state = {"trigger_source": body.trigger_source}
    inv_result = await inventory_check_node(init_state)

    flagged_products = inv_result.get("flagged_products", [])
    scan_summary = inv_result.get("scan_summary", {})
    alerts_generated_raw = inv_result.get("alerts_generated", [])

    alerts: list[AlertData] = []
    rfq_drafts: list[RFQDraftData] = []
    pricing_recs: list[PricingRecData] = []

    prod_to_alert = {a["product_id"]: a["alert_id"] for a in alerts_generated_raw}

    # Prefer the production graph (AsyncPostgresSaver) if lifespan set it up
    current_graph = getattr(http_request.app.state, "m2_graph", None) or m2_app

    # ── 2. Per-product graph runs ─────────────────────────────────
    async with get_db_session() as session:
        for p in flagged_products:
            prod_id = p["product_id"]

            # Unique thread_id per product run — used as the checkpoint key.
            # Format keeps it human-readable for debugging.
            thread_id = f"m2-{prod_id[:8]}-{int(time.time())}"
            config = {"configurable": {"thread_id": thread_id}}

            state_input = {
                "trigger_source": body.trigger_source,
                "current_product": p,
                "detection_type": p["detection_type"],
                "thread_id": thread_id,
                "user_context": {"language": body.language},
            }

            graph_result = await current_graph.ainvoke(state_input, config=config)

            # Update alert row with LLM explanation (if generated)
            explanation = graph_result.get("explanation")
            alert_id = prod_to_alert.get(prod_id)
            if explanation and alert_id:
                await session.execute(
                    update(InventoryAlert)
                    .where(InventoryAlert.id == alert_id)
                    .values(message=explanation)
                )

            # Collect RFQ drafts (procurement path)
            if graph_result.get("rfq_draft") and graph_result.get("rfq_id"):
                rfq_drafts.append(
                    RFQDraftData(
                        rfq_id=graph_result["rfq_id"],
                        product_id=prod_id,
                        draft_text=graph_result["rfq_draft"],
                    )
                )

            # Collect pricing recommendations (Sprint 5)
            if graph_result.get("pricing_recommendation"):
                pricing_recs.append(
                    PricingRecData(
                        product_id=prod_id,
                        recommendation=graph_result["pricing_recommendation"],
                    )
                )

        await session.commit()

    # ── 3. Build alert list ───────────────────────────────────────
    for a in alerts_generated_raw:
        alerts.append(
            AlertData(
                alert_id=a["alert_id"],
                product_id=a["product_id"],
                alert_type=a["alert_type"],
                metadata=a["metadata"],
            )
        )

    return AnalyzeResponse(
        scan_summary=scan_summary,
        alerts=alerts,
        rfq_drafts=rfq_drafts,
        pricing_recs=pricing_recs,
        language=body.language,
    )

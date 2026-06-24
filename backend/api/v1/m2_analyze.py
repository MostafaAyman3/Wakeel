from fastapi import APIRouter, Depends
from typing import Any
from sqlalchemy import update

from backend.schemas.m2_analyze import AnalyzeRequest, AnalyzeResponse, AlertData, RFQDraftData, PricingRecData
from agents.m2.nodes.inventory_check_node import inventory_check_node
from agents.m2.graphs.m2_graph import m2_app
from backend.core.database import get_db_session
from backend.models.m2_inventory_alert import InventoryAlert
from backend.models.m2_pricing_recommendation import PricingRecommendation

router = APIRouter(prefix="/m2", tags=["M2 Analyze"])

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_inventory(request: AnalyzeRequest) -> Any:
    """
    Triggers the LangGraph for all active products.
    1. Runs inventory_check_node to scan inventory and flag products.
    2. Loops over flagged products and runs the LLM graph to generate alerts and RFQs.
    """
    # 1. Run inventory scan
    init_state = {"trigger_source": request.trigger_source}
    inv_result = await inventory_check_node(init_state)
    
    flagged_products = inv_result.get("flagged_products", [])
    scan_summary = inv_result.get("scan_summary", {})
    alerts_generated_raw = inv_result.get("alerts_generated", [])
    
    alerts = []
    rfq_drafts = []
    pricing_recs = []
    
    # Map product_id to alert_id to update the alert message
    prod_to_alert = {a["product_id"]: a["alert_id"] for a in alerts_generated_raw}

    async with get_db_session() as session:
        # 2. Iterate and run the graph for each flagged product
        for p in flagged_products:
            prod_id = p["product_id"]
            state_input = {
                "trigger_source": request.trigger_source,
                "current_product": p,
                "detection_type": p["detection_type"],
                "user_context": {"language": request.language}
            }
            
            # Run LangGraph
            graph_result = await m2_app.ainvoke(state_input)
            
            # Update the alert with the generated explanation
            explanation = graph_result.get("explanation")
            alert_id = prod_to_alert.get(prod_id)
            if explanation and alert_id:
                stmt = update(InventoryAlert).where(InventoryAlert.id == alert_id).values(message=explanation)
                await session.execute(stmt)
            
            # Collect RFQ drafts
            if "rfq_draft" in graph_result and "rfq_id" in graph_result:
                rfq_drafts.append(RFQDraftData(
                    rfq_id=graph_result["rfq_id"],
                    product_id=prod_id,
                    draft_text=graph_result["rfq_draft"]
                ))
                
            # Collect Pricing recs (Sprint 5)
            if "pricing_recommendation" in graph_result:
                rec_text = graph_result["pricing_recommendation"]
                pricing_recs.append(PricingRecData(
                    product_id=prod_id,
                    recommendation=rec_text
                ))
                # Save to database
                new_rec = PricingRecommendation(
                    product_id=prod_id,
                    recommendation_text=rec_text
                )
                session.add(new_rec)
        
        await session.commit()
        
    for a in alerts_generated_raw:
        alerts.append(AlertData(
            alert_id=a["alert_id"],
            product_id=a["product_id"],
            alert_type=a["alert_type"],
            metadata=a["metadata"]
        ))
        
    return AnalyzeResponse(
        scan_summary=scan_summary,
        alerts=alerts,
        rfq_drafts=rfq_drafts,
        pricing_recs=pricing_recs,
        language=request.language
    )

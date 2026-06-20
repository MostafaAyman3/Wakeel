from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.core.auth import UserContext, get_current_user
from backend.core.logging import get_logger
from agents.m2.tools.inventory_tools import get_all_inventory, get_low_stock_items

router = APIRouter(prefix="/m2", tags=["M2 Inventory"])
logger = get_logger(__name__)

class AnalyzeRequest(BaseModel):
    language: str = Field(default="ar", pattern="^(ar|en)$")
    trigger: str = Field(default="manual", pattern="^(manual|scheduled)$")

class InventoryResponse(BaseModel):
    inventory_items: list
    low_stock_items: list

class AnalyzeResponse(BaseModel):
    status: str
    low_stock_count: int
    alerts: list
    rfq_drafts: list
    message: str | None = None

@router.get("/inventory", response_model=InventoryResponse)
async def get_inventory(user: UserContext = Depends(get_current_user)):
    all_inventory = await get_all_inventory()
    low_stock = await get_low_stock_items()
    
    return InventoryResponse(
        inventory_items=all_inventory,
        low_stock_items=low_stock
    )

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_inventory(
    request: AnalyzeRequest,
    user: UserContext = Depends(get_current_user)
):
    logger.info("trigger_m2_analysis", user_id=user.user_id, language=request.language)
    
    try:
        # Import dynamically to avoid circular imports
        from agents.m2.graphs.m2_graph import m2_graph
        
        initial_state = {
            "trigger": request.trigger,
            "language": request.language,
        }
        
        result = await m2_graph.ainvoke(initial_state)
        final_response = result.get("final_response", {})
        
        if final_response.get("status") == "ok":
            return AnalyzeResponse(
                status="ok",
                low_stock_count=0,
                alerts=[],
                rfq_drafts=[],
                message=final_response.get("message")
            )
            
        return AnalyzeResponse(
            status="alerts_generated",
            low_stock_count=len(result.get("low_stock_items", [])),
            alerts=result.get("alerts", []),
            rfq_drafts=result.get("rfq_drafts", [])
        )
        
    except Exception as exc:
        logger.error("m2_analysis_failed", user_id=user.user_id, error=str(exc))
        return AnalyzeResponse(
            status="error",
            low_stock_count=0,
            alerts=[],
            rfq_drafts=[],
            message=str(exc)
        )

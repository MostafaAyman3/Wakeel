import structlog
from agents.m2.schemas.m2_state import M2State
from agents.m2.tools.inventory_tools import get_low_stock_items

logger = structlog.get_logger(__name__)

async def inventory_check_node(state: M2State) -> dict:
    """Node that checks database for low stock items."""
    logger.info("checking_inventory_for_low_stock")
    try:
        low_stock = await get_low_stock_items()
        
        # Determine if we should proceed or just end
        if not low_stock:
            logger.info("no_low_stock_found")
            return {
                "low_stock_items": [],
                "final_response": {
                    "status": "ok",
                    "message": "لا يوجد نقص في المخزون." if state.get("language") == "ar" else "No low stock found."
                }
            }
            
        logger.info("low_stock_found", count=len(low_stock))
        return {
            "low_stock_items": low_stock
        }
    except Exception as e:
        logger.error("inventory_check_failed", error=str(e))
        return {"error": str(e)}

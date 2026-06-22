from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any

from backend.core.database import get_db_session
from backend.schemas.m2_inventory import InventoryStatusResponse, InventoryProductStatus, InventorySummary
from agents.m2.tools.inventory_tools import fetch_inventory_status
from agents.m2.nodes.inventory_check_node import SLOW_MOVING_THRESHOLD, NEAR_EXPIRY_WINDOW, MIN_AVG_DAILY_SALES
from datetime import date, timedelta

router = APIRouter(prefix="/m2/inventory", tags=["M2 Inventory"])

@router.get("", response_model=InventoryStatusResponse)
async def get_inventory_status(session: AsyncSession = Depends(get_db_session)) -> Any:
    """
    Returns current inventory status for all active products.
    Evaluates detection scenarios on the fly (low_stock, predicted_shortage, slow_moving, near_expiry).
    """
    inventory_data = await fetch_inventory_status(session)
    
    products = []
    summary = InventorySummary(total=len(inventory_data))
    
    today = date.today()

    for row in inventory_data:
        qty = row["quantity"] or 0
        reorder_point = row["reorder_point"] or 0
        lead_time = row["lead_time_days"] or 0
        daily_sales = max(row["computed_daily_sales"] or 0, MIN_AVG_DAILY_SALES)
        turnover_rate = row["computed_turnover_rate_per_month"] or 0
        expiry = row["expiry_date"]
        
        days_until_stockout = qty / daily_sales
        
        status = "safe"
        
        if qty <= reorder_point:
            status = "low_stock"
            summary.low_stock += 1
        elif days_until_stockout < lead_time:
            status = "predicted_shortage"
            summary.predicted_shortage += 1
        elif turnover_rate < SLOW_MOVING_THRESHOLD:
            status = "slow_moving"
            summary.slow_moving += 1
        elif expiry and expiry <= today + timedelta(days=NEAR_EXPIRY_WINDOW):
            status = "near_expiry"
            summary.near_expiry += 1
        else:
            summary.safe += 1

        products.append(InventoryProductStatus(
            product_id=row["product_id"],
            sku=row["sku"],
            name=row["name"],
            name_ar=row["name_ar"],
            category=row["category"],
            quantity=qty,
            reorder_point=reorder_point,
            lead_time_days=lead_time,
            avg_daily_sales=daily_sales,
            days_until_stockout=days_until_stockout,
            status=status,
            expiry_date=expiry
        ))

    return InventoryStatusResponse(
        products=products,
        summary=summary
    )

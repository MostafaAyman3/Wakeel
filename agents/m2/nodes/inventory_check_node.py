from datetime import date, datetime, timedelta
from typing import Dict, Any

from backend.core.database import get_db_session
from backend.models.m2_inventory_alert import InventoryAlert
from agents.m2.schemas.m2_state import M2State
from agents.m2.tools.inventory_tools import fetch_inventory_status

SLOW_MOVING_THRESHOLD = 0.5   # turnover_rate per month
NEAR_EXPIRY_WINDOW    = 30    # days
MIN_AVG_DAILY_SALES   = 0.01  # avoid division by zero
DEFAULT_MIN_ORDER_QTY = 10

async def inventory_check_node(state: M2State) -> Dict[str, Any]:
    """
    InventoryCheckNode: Scans inventory, identifies issues, and flags products.
    """
    flagged_products = []
    alerts_generated = []
    
    scan_summary = {
        "total_products_checked": 0,
        "low_stock_count": 0,
        "predicted_shortage_count": 0,
        "slow_moving_count": 0,
        "near_expiry_count": 0,
        "scanned_at": datetime.now().isoformat(),
    }

    async with get_db_session() as session:
        # Fetch data
        inventory_data = await fetch_inventory_status(session)
        scan_summary["total_products_checked"] = len(inventory_data)
        
        today = date.today()

        for row in inventory_data:
            qty = row["quantity"] or 0
            reorder_point = row["reorder_point"] or 0
            lead_time = row["lead_time_days"] or 0
            daily_sales = max(row["computed_daily_sales"] or 0, MIN_AVG_DAILY_SALES)
            turnover_rate = row["computed_turnover_rate_per_month"] or 0
            expiry = row["expiry_date"]
            
            days_until_stockout = qty / daily_sales
            suggested_qty = max(reorder_point * 2 - qty, DEFAULT_MIN_ORDER_QTY)
            
            detection_type = None
            
            # 1. Low stock
            if qty <= reorder_point:
                detection_type = "low_stock"
                scan_summary["low_stock_count"] += 1
            # 2. Predicted shortage
            elif days_until_stockout < lead_time:
                detection_type = "predicted_shortage"
                scan_summary["predicted_shortage_count"] += 1
            # 3. Slow moving
            elif turnover_rate < SLOW_MOVING_THRESHOLD:
                detection_type = "slow_moving"
                scan_summary["slow_moving_count"] += 1
            # 4. Near expiry
            elif expiry and expiry <= today + timedelta(days=NEAR_EXPIRY_WINDOW):
                detection_type = "near_expiry"
                scan_summary["near_expiry_count"] += 1
                
            if detection_type:
                # Flag product
                flagged_product = {
                    "product_id": str(row["product_id"]),
                    "sku": row["sku"],
                    "name": row["name"],
                    "name_ar": row["name_ar"],
                    "category": row["category"],
                    "quantity": qty,
                    "reorder_point": reorder_point,
                    "lead_time_days": lead_time,
                    "avg_daily_sales": daily_sales,
                    "expiry_date": expiry.isoformat() if expiry else None,
                    "detection_type": detection_type,
                    "days_until_stockout": days_until_stockout,
                    "turnover_rate": turnover_rate,
                    "suggested_quantity": int(suggested_qty)
                }
                flagged_products.append(flagged_product)
                
                # Save alert to DB
                alert = InventoryAlert(
                    product_id=row["product_id"],
                    alert_type=detection_type,
                    metadata_={
                        "current_quantity": qty,
                        "reorder_point": reorder_point,
                        "suggested_quantity": int(suggested_qty),
                        "lead_time_days": lead_time,
                        "days_until_stockout": days_until_stockout,
                        "turnover_rate": turnover_rate,
                        "avg_daily_sales": daily_sales,
                        "days_to_expiry": (expiry - today).days if expiry else None
                    }
                )
                session.add(alert)
                
                # We won't have the ID yet until flush/commit, but we can store it for the API response.
                alerts_generated.append(alert)

        # Commit alerts
        await session.commit()
        
        # After commit, alert IDs are populated
        for alert in alerts_generated:
            # Refresh if needed or just access attributes (since expire_on_commit=False is set in get_db_session)
            pass

    return {
        "flagged_products": flagged_products,
        "scan_summary": scan_summary,
        # In a real run, alerts_generated could be serialized here
        # But we'll just return the count or basic info for now
        "alerts_generated": [
            {
                "alert_id": str(a.id),
                "product_id": str(a.product_id),
                "alert_type": a.alert_type,
                "metadata": a.metadata_
            } for a in alerts_generated
        ]
    }

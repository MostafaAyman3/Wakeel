from typing import List, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def fetch_inventory_status(session: AsyncSession) -> List[Dict[str, Any]]:
    """
    Fetches the current inventory status for all active products.
    Returns a list of dictionaries with inventory and product details.
    Uses computed_daily_sales from orders if available, otherwise falls back to cached avg_daily_sales.
    """
    query = text("""
        SELECT
            i.id            AS inv_id,
            p.id            AS product_id,
            p.sku, 
            p.name, 
            p.name_ar, 
            p.category,
            i.quantity,
            i.reorder_point,
            i.lead_time_days,
            i.avg_daily_sales,
            i.expiry_date,
            -- Compute avg daily sales from last 90 days of orders
            COALESCE(
                (SELECT SUM(oi.quantity)::float / 90
                 FROM order_items oi
                 JOIN orders o ON o.id = oi.order_id
                 WHERE oi.product_id = p.id
                   AND o.order_date >= now() - interval '90 days'),
                i.avg_daily_sales  -- fallback to cached value
            ) AS computed_daily_sales,
            -- Compute turnover rate (units sold / current inventory) simplified for last 90 days
            COALESCE(
                (SELECT SUM(oi.quantity)::float / NULLIF(i.quantity, 0)
                 FROM order_items oi
                 JOIN orders o ON o.id = oi.order_id
                 WHERE oi.product_id = p.id
                   AND o.order_date >= now() - interval '90 days'),
                0
            ) / 3 AS computed_turnover_rate_per_month -- 90 days is approx 3 months
        FROM inventory i
        JOIN products p ON p.id = i.product_id
        WHERE p.is_active = true
        ORDER BY p.category, p.name;
    """)

    result = await session.execute(query)
    rows = result.mappings().all()
    
    # Convert mappings to normal dictionaries for easier handling in LangGraph
    inventory_data = []
    for row in rows:
        inventory_data.append(dict(row))
        
    return inventory_data

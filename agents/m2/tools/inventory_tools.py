import structlog
from backend.core.database import get_readonly_session
from sqlalchemy import text

logger = structlog.get_logger(__name__)

async def get_all_inventory() -> list[dict]:
    query = text("""
        SELECT p.product_id, p.name_ar, p.name_en, p.sku, p.category,
               i.quantity, i.reorder_point, i.warehouse_location
        FROM products p
        JOIN inventory i ON p.product_id = i.product_id
        ORDER BY i.quantity ASC
    """)
    async with get_readonly_session() as session:
        result = await session.execute(query)
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

async def get_low_stock_items() -> list[dict]:
    query = text("""
        SELECT p.product_id, p.name_ar, p.name_en, p.sku, p.category,
               i.quantity, i.reorder_point, i.warehouse_location,
               v.vendor_name, v.vendor_id
        FROM products p
        JOIN inventory i ON p.product_id = i.product_id
        LEFT JOIN vendors v ON p.vendor_id = v.vendor_id
        WHERE i.quantity <= i.reorder_point
        ORDER BY i.quantity ASC
    """)
    async with get_readonly_session() as session:
        result = await session.execute(query)
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

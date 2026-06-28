from typing import List, Optional
from pydantic import BaseModel
from datetime import date
from uuid import UUID

class InventoryProductStatus(BaseModel):
    product_id: UUID
    sku: str
    name: str
    name_ar: str
    category: str
    quantity: int
    reorder_point: int
    lead_time_days: int
    avg_daily_sales: float
    days_until_stockout: float
    status: str
    expiry_date: Optional[date] = None

class InventorySummary(BaseModel):
    total: int = 0
    low_stock: int = 0
    predicted_shortage: int = 0
    slow_moving: int = 0
    near_expiry: int = 0
    safe: int = 0

class InventoryStatusResponse(BaseModel):
    products: List[InventoryProductStatus]
    summary: InventorySummary

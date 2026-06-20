from typing import TypedDict, Literal

class M2State(TypedDict, total=False):
    trigger: Literal["manual", "scheduled"]
    language: Literal["ar", "en"]
    inventory_items: list          # Raw inventory items from DB
    low_stock_items: list          # Items where qty <= reorder_point
    alerts: list                   # AI-generated alerts {product_id, message, severity}
    rfq_drafts: list               # AI-generated RFQ emails
    final_response: dict
    error: str

import structlog
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from agents.shared.llm_client import llm_fast
from agents.m2.schemas.m2_state import M2State

logger = structlog.get_logger(__name__)

class AlertData(BaseModel):
    product_id: int
    severity: str = Field(description="High, Medium, or Low based on stock level")
    message: str = Field(description="A short smart alert message")

class AlertsResponse(BaseModel):
    alerts: list[AlertData]

ALERT_SYSTEM_PROMPT = """You are an expert Inventory Manager Assistant.
Given a list of low stock items, analyze the situation and generate smart alerts.
Determine severity based on how far below the reorder point the quantity is (e.g. qty=0 is High, qty=reorder_point is Low).
Provide a short, actionable message in the user's requested language.
If language is "ar", use natural Egyptian Colloquial Arabic (عامية مصرية) for the alert message.
"""

async def alert_generation_node(state: M2State) -> dict:
    logger.info("generating_alerts")
    low_stock = state.get("low_stock_items", [])
    if not low_stock:
        return {"alerts": []}
    
    language = state.get("language", "ar")
    
    items_text = "\n".join(
        f"- ID: {i['product_id']}, Name: {i['name_en']}/{i['name_ar']}, Qty: {i['quantity']}, Reorder Point: {i['reorder_point']}"
        for i in low_stock
    )
    
    messages = [
        SystemMessage(content=ALERT_SYSTEM_PROMPT),
        HumanMessage(content=f"Requested Language: {language}\n\nLow Stock Items:\n{items_text}")
    ]
    
    chain = llm_fast.with_structured_output(AlertsResponse, method="function_calling")
    
    try:
        result = await chain.ainvoke(messages)
        alerts_list = [a.model_dump() for a in result.alerts]
        return {"alerts": alerts_list}
    except Exception as e:
        logger.error("alert_generation_failed", error=str(e))
        return {"alerts": []}

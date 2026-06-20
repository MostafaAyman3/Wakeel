import structlog
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from agents.shared.llm_client import llm_fast
from agents.m2.schemas.m2_state import M2State

logger = structlog.get_logger(__name__)

class RFQDraft(BaseModel):
    vendor_id: int | None
    vendor_name: str
    suggested_quantity: int
    rfq_text: str = Field(description="The full email draft to the supplier")

class RFQResponse(BaseModel):
    drafts: list[RFQDraft]

RFQ_SYSTEM_PROMPT = """You are a professional Purchasing Agent.
Generate Request for Quotation (RFQ) email drafts for the suppliers of the low stock items.
Group items by vendor_id/vendor_name if possible. 
Calculate a suggested order quantity (e.g., reorder_point * 2 minus current qty).
The user language determines the tone/language of the final AI summary, but the email itself should be formal. 
CRITICAL RULE: If the user language is "ar", generate the response in Egyptian Colloquial Arabic (عامية مصرية) for the voice summary, but the RFQ text must be a formal Arabic email. If "en", use English.
"""

async def rfq_builder_node(state: M2State) -> dict:
    logger.info("building_rfqs")
    low_stock = state.get("low_stock_items", [])
    if not low_stock:
        return {"rfq_drafts": []}
    
    language = state.get("language", "ar")
    
    items_text = "\n".join(
        f"- ID: {i['product_id']}, Name: {i['name_ar']}, Qty: {i['quantity']}, Reorder Point: {i['reorder_point']}, Vendor: {i.get('vendor_name', 'Unknown')} (ID: {i.get('vendor_id')})"
        for i in low_stock
    )
    
    messages = [
        SystemMessage(content=RFQ_SYSTEM_PROMPT),
        HumanMessage(content=f"Requested Language: {language}\n\nItems to order:\n{items_text}")
    ]
    
    chain = llm_fast.with_structured_output(RFQResponse, method="function_calling")
    
    try:
        result = await chain.ainvoke(messages)
        drafts_list = [d.model_dump() for d in result.drafts]
        
        # Prepare final response summary
        msg = ("انا جهزتلك مسودات طلبات الشراء للعناصر اللي نقصت في المخزن، تقدر تراجعها دلوقتي." if language == "ar" else "I have drafted the RFQs for the low stock items.")
        return {
            "rfq_drafts": drafts_list,
            "final_response": {
                "status": "alerts_generated",
                "message": msg
            }
        }
    except Exception as e:
        logger.error("rfq_generation_failed", error=str(e))
        return {
            "rfq_drafts": [], 
            "final_response": {
                "status": "error",
                "message": "Failed to generate RFQs."
            }
        }

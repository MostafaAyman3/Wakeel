from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage

from agents.shared.llm_client import llm_fast
from agents.m2.schemas.m2_state import M2State

ALERT_PROMPT = """
You are an inventory management assistant for an Egyptian ERP system.
Generate a concise, action-oriented alert message for the manager.

Product: {name} ({name_ar}) | SKU: {sku} | Category: {category}
Issue type: {detection_type}
Current quantity: {quantity} | Reorder point: {reorder_point}
Days until stockout: {days_until_stockout:.1f} | Lead time: {lead_time_days} days

Language: {language}  (ar-EG = Egyptian Arabic dialect; en = English)

Rules:
- Maximum 2 sentences
- Include the exact numbers
- Mention the recommended action (reorder / discount / urgent check)
- Egyptian Arabic: use informal dialect (عامية مصرية), not Modern Standard Arabic
- Do NOT use markdown formatting
"""

async def alert_generator_node(state: M2State) -> Dict[str, Any]:
    """
    Generates a human-readable alert message explaining the inventory issue.
    """
    current_product = state.get("current_product", {})
    language = state.get("user_context", {}).get("language", "ar-EG")
    
    prompt = ALERT_PROMPT.format(
        name=current_product.get("name", "Unknown"),
        name_ar=current_product.get("name_ar", "غير معروف"),
        sku=current_product.get("sku", "N/A"),
        category=current_product.get("category", "N/A"),
        detection_type=state.get("detection_type", "unknown"),
        quantity=current_product.get("quantity", 0),
        reorder_point=current_product.get("reorder_point", 0),
        days_until_stockout=current_product.get("days_until_stockout", 0.0),
        lead_time_days=current_product.get("lead_time_days", 0),
        language=language
    )
    
    messages = [HumanMessage(content=prompt)]
    
    try:
        response = await llm_fast.ainvoke(messages)
        return {"explanation": response.content.strip()}
    except Exception as exc:
        return {"explanation": f"Failed to generate alert explanation: {exc}", "error": str(exc)}

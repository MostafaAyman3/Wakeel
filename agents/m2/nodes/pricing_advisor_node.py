from typing import Dict, Any
from langchain_core.messages import HumanMessage

from agents.shared.llm_client import llm_fast
from agents.m2.schemas.m2_state import M2State

PRICING_PROMPT = """
You are an expert pricing advisor for an Egyptian ERP system.
Analyze the slow-moving or near-expiry product and recommend a pricing strategy or discount to clear the inventory.

Product: {name} ({name_ar}) | SKU: {sku} | Category: {category}
Issue type: {detection_type}
Current quantity: {quantity}
Turnover rate: {turnover_rate:.2f} per month
Days to expiry: {days_to_expiry}

Language: {language} (ar-EG = Egyptian Arabic dialect; en = English)

Rules:
- Provide a clear, actionable pricing recommendation (e.g., "Apply a 15% discount to clear stock before expiry").
- Give a brief reasoning for the recommendation (1-2 sentences).
- If the issue is near_expiry, focus on clearing the stock urgently.
- If the issue is slow_moving, suggest a moderate promotional discount or bundling.
- Egyptian Arabic: use informal dialect (عامية مصرية), not Modern Standard Arabic.
- Do NOT use markdown formatting.
"""

async def pricing_advisor_node(state: M2State) -> Dict[str, Any]:
    """
    Generates a pricing recommendation for slow-moving or near-expiry products.
    """
    current_product = state.get("current_product", {})
    language = state.get("user_context", {}).get("language", "ar-EG")
    
    # Calculate days to expiry if applicable
    days_to_expiry = "N/A"
    expiry_date = current_product.get("expiry_date")
    if expiry_date:
        from datetime import datetime
        try:
            exp = datetime.fromisoformat(expiry_date).date()
            today = datetime.now().date()
            days_to_expiry = str((exp - today).days)
        except ValueError:
            pass

    prompt = PRICING_PROMPT.format(
        name=current_product.get("name", "Unknown"),
        name_ar=current_product.get("name_ar", "غير معروف"),
        sku=current_product.get("sku", "N/A"),
        category=current_product.get("category", "N/A"),
        detection_type=state.get("detection_type", "unknown"),
        quantity=current_product.get("quantity", 0),
        turnover_rate=current_product.get("turnover_rate", 0.0),
        days_to_expiry=days_to_expiry,
        language=language
    )
    
    messages = [HumanMessage(content=prompt)]
    
    try:
        response = await llm_fast.ainvoke(messages)
        return {"pricing_recommendation": response.content.strip()}
    except Exception as exc:
        return {"pricing_recommendation": f"Failed to generate pricing recommendation: {exc}", "error": str(exc)}

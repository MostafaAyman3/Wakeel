import uuid
from typing import Dict, Any
from langchain_core.messages import HumanMessage

from agents.shared.llm_client import llm_primary
from agents.m2.schemas.m2_state import M2State
from backend.core.database import get_db_session
from backend.models.m2_rfq import RFQ

RFQ_PROMPT = """
You are drafting a professional Request-For-Quotation email on behalf of
an Egyptian company's procurement department.

Product: {name} ({name_ar}) | SKU: {sku}
Quantity needed: {suggested_quantity} {unit}
Reason: {explanation}

Language: {language}

Write a complete, formal email body (no subject line).
Include:
  - Polite greeting
  - Clear product specification (name, SKU, quantity)
  - Request for: unit price, total price, delivery timeline, payment terms
  - Deadline for response (3 business days)
  - Professional closing

For Arabic: use formal Modern Standard Arabic (فصحى مهنية) for business emails,
NOT Egyptian dialect. Dialect is for internal chat only.
"""

async def rfq_builder_node(state: M2State) -> Dict[str, Any]:
    """
    Generates a formal RFQ draft and saves it to the database as a draft.
    """
    current_product = state.get("current_product", {})
    language = state.get("user_context", {}).get("language", "ar-EG")
    explanation = state.get("explanation", "")
    suggested_qty = current_product.get("suggested_quantity", 0)
    
    prompt = RFQ_PROMPT.format(
        name=current_product.get("name", "Unknown"),
        name_ar=current_product.get("name_ar", "غير معروف"),
        sku=current_product.get("sku", "N/A"),
        suggested_quantity=suggested_qty,
        unit="unit", # Assuming default unit for now
        explanation=explanation,
        language=language
    )
    
    messages = [HumanMessage(content=prompt)]
    
    try:
        response = await llm_primary.ainvoke(messages)
        rfq_text = response.content.strip()
        
        # Save to DB
        rfq_id = str(uuid.uuid4())
        async with get_db_session() as session:
            new_rfq = RFQ(
                id=uuid.UUID(rfq_id),
                product_id=uuid.UUID(current_product["product_id"]),
                quantity=suggested_qty,
                unit="unit",
                draft_text=rfq_text,
                status="draft",
            )
            session.add(new_rfq)
            await session.commit()
            
        return {
            "rfq_draft": rfq_text,
            "rfq_id": rfq_id
        }
    except Exception as exc:
        return {"rfq_draft": f"Failed to generate RFQ: {exc}", "error": str(exc)}

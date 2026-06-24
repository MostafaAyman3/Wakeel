"""
OfferAnalysisNode — GPT-4o compares supplier offers and recommends the best one.

Scoring weights (aligned with procurement best-practice):
  Price      : 50%  (lowest unit price wins)
  Lead time  : 30%  (shortest delivery time wins)
  Terms      : 20%  (qualitative, LLM-evaluated)

The node returns:
  recommended_offer  — the winning offer dict with composite score
  pricing_recommendation — LLM-generated justification paragraph (language-aware)
"""

from typing import Any, Dict

from langchain_core.messages import HumanMessage

from agents.m2.schemas.m2_state import M2State
from agents.shared.llm_client import llm_primary

ANALYSIS_PROMPT = """
You are a procurement analyst for an Egyptian company.
Evaluate the following supplier offers for the RFQ and recommend the best one.

Product: {product_name} ({product_name_ar}) | SKU: {sku}
Required quantity: {quantity} units

Offers received:
{offers_text}

Scoring criteria:
  - Price      (50%): lower unit price is better
  - Lead time  (30%): shorter delivery time is better
  - Terms      (20%): more flexible payment terms are better

Instructions:
1. Score each offer out of 100 using the criteria above.
2. Identify the best offer.
3. Write a clear recommendation paragraph for the manager.

Language: {language}
  ar-EG → write recommendation in Egyptian Arabic (عامية مصرية)
  en    → write in English

Output format (JSON only, no markdown):
{{
  "recommended_vendor": "<vendor_name>",
  "recommended_offer_index": <0-based index>,
  "score": <0-100>,
  "scores": [<score for offer 0>, <score for offer 1>, ...],
  "justification": "<recommendation paragraph in the requested language>"
}}
"""


def _format_offers(offers: list) -> str:
    lines = []
    for i, o in enumerate(offers):
        lines.append(
            f"Offer {i + 1}:\n"
            f"  Vendor      : {o.get('vendor_name', 'Unknown')}\n"
            f"  Price/unit  : {o.get('price_per_unit', 0):.2f}\n"
            f"  Total price : {o.get('total_price', 0):.2f}\n"
            f"  Lead time   : {o.get('lead_time_days', '?')} days\n"
            f"  Payment     : {o.get('payment_terms', 'N/A')}\n"
            f"  Notes       : {o.get('notes', '')}"
        )
    return "\n\n".join(lines)


async def offer_analysis_node(state: M2State) -> Dict[str, Any]:
    """
    Analyzes supplier_offers from state, scores them, and returns
    the recommended offer + justification.
    """
    offers = state.get("supplier_offers", [])
    current_product = state.get("current_product", {})
    language = state.get("user_context", {}).get("language", "ar-EG")

    if not offers:
        return {
            "recommended_offer": {},
            "pricing_recommendation": "No offers received to analyze.",
            "error": "offer_analysis_skipped: no offers in state",
        }

    offers_text = _format_offers(offers)

    prompt = ANALYSIS_PROMPT.format(
        product_name=current_product.get("name", "Unknown"),
        product_name_ar=current_product.get("name_ar", "غير معروف"),
        sku=current_product.get("sku", "N/A"),
        quantity=current_product.get("suggested_quantity", 0),
        offers_text=offers_text,
        language=language,
    )

    try:
        response = await llm_primary.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        # Parse JSON response
        import json
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)

        best_idx = parsed.get("recommended_offer_index", 0)
        best_offer = offers[best_idx] if best_idx < len(offers) else offers[0]

        recommended = {
            **best_offer,
            "vendor_name": parsed.get("recommended_vendor", best_offer.get("vendor_name")),
            "score": parsed.get("score", 0),
            "all_scores": parsed.get("scores", []),
        }

        return {
            "recommended_offer": recommended,
            "pricing_recommendation": parsed.get("justification", ""),
        }

    except Exception as exc:
        # Fallback: pick cheapest offer
        cheapest = min(offers, key=lambda o: o.get("price_per_unit", float("inf")))
        return {
            "recommended_offer": {**cheapest, "score": 0, "fallback": True},
            "pricing_recommendation": f"Auto-selected cheapest offer (LLM error: {exc})",
            "error": str(exc),
        }

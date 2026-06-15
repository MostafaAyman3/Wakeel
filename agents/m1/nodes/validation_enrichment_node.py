"""
ValidationEnrichmentNode — validates retrieved data and enriches state.

Blueprint reference: Sprint 1 spec — "يتحقق من اكتمال البيانات المُسترجعة ويُثريها بالسياق"

Sprint 1 (simplified):
  • Checks whether raw_data is populated.
  • Sets data_confidence accordingly.
  • Passes through existing final_response from stub nodes.

Sprint 2+:
  • Schema validation against db_schema_reference.
  • Data quality scoring.
  • Context enrichment with related data.
"""

from __future__ import annotations

from agents.m1.schemas.m1_state import M1State


async def validate_and_enrich(state: M1State) -> dict:
    """Validate and enrich the data in the current state.

    In Sprint 1 this is intentionally lightweight — it sets
    ``data_confidence`` and ensures ``final_response`` is present.
    """
    raw_data: list = state.get("raw_data", [])
    intent: str = state.get("intent", "unknown")
    existing_response: dict = state.get("final_response", {})

    # ── Data-confidence score ─────────────────────────────────
    data_confidence: float = 1.0 if raw_data else 0.0

    # ── If the upstream node already built a final_response,
    #    just augment it with the confidence and pass through. ──
    if existing_response:
        return {"data_confidence": data_confidence}

    # ── Fallback: build a minimal valid response ──────────────
    return {
        "data_confidence": data_confidence,
        "final_response": {
            "format": "direct_text",
            "data": raw_data or None,
            "chart_config": None,
            "narrative": f"Query processed. Intent: {intent}.",
            "alert": None,
            "disclaimer": None,
        },
    }

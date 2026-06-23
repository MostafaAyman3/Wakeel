"""T6 adapter. M1 delegates support work and never queries support tables."""

from __future__ import annotations

import re

from agents.m1.schemas.m1_state import M1State

_IDENTIFIER_PATTERN = re.compile(
    r"\b(?:ORD|INV|CUST|TRK)-[A-Z0-9-]+\b",
    re.IGNORECASE,
)


async def delegate_to_m3(state: M1State) -> dict:
    query = state.get("query", "")
    identifiers = _IDENTIFIER_PATTERN.findall(query)
    payload = {
        "source": "m1",
        "session_id": state.get("session_id", ""),
        "user_query": query,
        "language": state.get("language", "en"),
        "user_context": state.get("user_context", {}),
        "conversation_summary": state.get("prior_analysis_frame", {}),
        "detected_support_signals": state.get("route_signals", []),
        "identifier_candidates": identifiers,
    }
    language = state.get("language", "en")
    narrative = (
        "الطلب ده يخص دعم العملاء، فتم توجيهه لمسار M3 المختص. مسار الدعم الكامل "
        "لسه غير متاح في النسخة الحالية؛ من فضلك احتفظ برقم الطلب أو الفاتورة."
        if language == "ar"
        else "This is a customer-support request, so it has been delegated to "
        "the M3 boundary. The full M3 workflow is not available in this build yet."
    )
    return {
        "m3_delegation_payload": payload,
        "query_mode": "none",
        "output_format": "direct_text",
        "narrative": narrative,
        "final_response": {
            "format": "direct_text",
            "data": None,
            "chart_config": None,
            "narrative": narrative,
            "alert": None,
            "disclaimer": None,
            "metadata": {
                "delegated_to": "M3",
                "delegation_available": False,
                "identifier_candidates": identifiers,
            },
        },
    }


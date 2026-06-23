"""Natural no-tool response for T0."""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from agents.m1.schemas.m1_state import M1State
from agents.shared.llm_client import llm_fast

_SYSTEM_PROMPT = """\
You are Wakeel, a natural bilingual business data analyst copilot.
Respond in the same language as the user. This turn is conversational and must
not use tools or claim that data was queried. Be concise and helpful. If useful,
mention that you can analyze sales, finance, collections, inventory, invoices,
and tax knowledge.
"""


async def t0_conversation(state: M1State) -> dict:
    query = state.get("query", "")
    language = state.get("language", "en")
    try:
        response = await llm_fast.ainvoke(
            [
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=query),
            ]
        )
        narrative = response.content.strip()
    except Exception:
        narrative = (
            "أنا وكيل، مساعد تحليل بيانات الأعمال. أقدر أساعدك في المبيعات "
            "والتحصيل والمخزون والفواتير."
            if language == "ar"
            else "I’m Wakeel, a business data analyst copilot for sales, "
            "collections, inventory, and invoices."
        )
    return {
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
        },
    }


"""
ClarificationNode — generates a follow-up question when intent is ambiguous.

Uses ``llm_fast`` (GPT-4o-mini) to produce a helpful clarification
question **in the same language** as the user's original query.

Activated when:
  • intent == "clarification_needed"
  • intent_confidence < LOW_CONFIDENCE_THRESHOLD (auto-set by classifier)
"""

from __future__ import annotations

from langchain_core.messages import SystemMessage, HumanMessage

from agents.shared.llm_client import llm_fast
from agents.m1.schemas.m1_state import M1State


# ── System prompt ────────────────────────────────────────────────

CLARIFICATION_SYSTEM_PROMPT = """\
You are a helpful ERP assistant. The user's query was too vague or \
ambiguous to classify into a specific action.

Your job: generate a clear, professional clarification question in the \
SAME LANGUAGE as the user's query.

Guidelines:
• If the user wrote in Arabic, respond entirely in Arabic.
• If the user wrote in English, respond entirely in English.
• Suggest 2-3 concrete options the user might mean.
• Keep it concise (1-3 sentences max).
• Reference what they CAN ask about:
  – Financial reports (revenue, expenses, profit, aging)
  – Sales / operational analysis
  – Invoice analysis (vendor invoices, payment patterns)
  – Tax questions (VAT, tax rules)

Example AR:
"ممكن توضح أكتر؟ تقدر تسأل عن: إيرادات المبيعات، تحليل فواتير الموردين، \
حالة الطلبات، أو أسئلة ضريبية."

Example EN:
"Could you be more specific? You can ask about: sales revenue, \
vendor invoices, order status, or tax questions."
"""


# ── Fallback messages ────────────────────────────────────────────

_FALLBACK_AR = (
    "ممكن توضح أكتر؟ تقدر تسأل عن: إيرادات المبيعات، "
    "تحليل فواتير الموردين، حالة الطلبات، أو أسئلة ضريبية."
)
_FALLBACK_EN = (
    "Could you be more specific? You can ask about: sales revenue, "
    "vendor invoices, order status, or tax questions."
)


# ── Node function ────────────────────────────────────────────────

async def clarify(state: M1State) -> dict:
    """Generate a clarification question for ambiguous / vague queries.

    Sets ``needs_clarification = True`` and builds ``final_response``
    directly — no further pipeline stages needed.
    """
    query: str = state["query"]
    language: str = state.get("language", "ar")

    try:
        messages = [
            SystemMessage(content=CLARIFICATION_SYSTEM_PROMPT),
            HumanMessage(
                content=f"User query: {query}\nLanguage: {language}"
            ),
        ]
        response = await llm_fast.ainvoke(messages)
        clarification_msg: str = response.content.strip()
    except Exception:
        # Deterministic fallback — never leave the user hanging
        clarification_msg = _FALLBACK_AR if language == "ar" else _FALLBACK_EN

    return {
        "needs_clarification": True,
        "clarification_message": clarification_msg,
        "final_response": {
            "format": "clarification",
            "data": None,
            "chart_config": None,
            "narrative": clarification_msg,
            "alert": None,
            "disclaimer": None,
        },
    }

"""
ClarificationNode (Feature 004) — asks the customer for a missing/ambiguous
reference instead of escalating.

Flow: input_parser flags ``clarification_needed`` (missing identifier or an
ambiguous bare value). This node:
  1. Counts how many times we've already asked in this conversation
     (assistant turns tagged ``metadata.clarification`` in chat_history).
  2. If that count has reached the configured limit → escalate (hand off).
  3. Otherwise composes a short, language-matched follow-up question and ends
     the turn (no DB fetch, no escalation).

Never raises — falls back to a static AR/EN question on any LLM error.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from agents.m3.schemas.m3_state import M3State
from agents.prompts.clarification_agent import CLARIFICATION_SYSTEM_PROMPT
from agents.shared.llm_client import llm_fast
from backend.core.config import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

# Static fallbacks (LLM failure) ------------------------------------------------
_ASK_IDENTIFIER_AR = (
    "تمام، أقدر أساعدك. ممكن تبعتلي رقم الطلب أو رقم الفاتورة أو رقم العميل "
    "عشان أقدر أتابع طلبك؟"
)
_ASK_IDENTIFIER_EN = (
    "I'd be glad to help. Could you share your order number, invoice number, "
    "or customer number so I can look it up?"
)


def _ask_ambiguous(value: str, lang: str) -> str:
    if lang == "ar":
        return f"شكراً! الرقم {value} ده رقم طلب، رقم فاتورة، ولا رقم عميل؟"
    return f"Thanks! Is {value} an order number, an invoice number, or your customer number?"


def _count_prior_asks(chat_history: list | None) -> int:
    """Number of prior assistant turns that were clarification questions."""
    if not chat_history:
        return 0
    count = 0
    for turn in chat_history:
        if not isinstance(turn, dict):
            continue
        if turn.get("role") == "assistant":
            meta = turn.get("metadata") or {}
            if isinstance(meta, dict) and meta.get("clarification"):
                count += 1
    return count


async def clarify(state: M3State) -> dict:
    """Ask for the missing/ambiguous reference, or escalate once asks are spent."""
    lang: str = state.get("language", "en") or "en"
    if lang == "auto":
        lang = "en"
    slot: str = state.get("missing_slot") or "identifier"
    pending_value: str = state.get("pending_value") or ""
    chat_history = state.get("chat_history")  # type: ignore[assignment]

    settings = get_settings()
    max_attempts = settings.m3_clarification_max_attempts
    prior_asks = _count_prior_asks(chat_history)

    # ── Attempts exhausted → escalate (FR-007) ────────────────────
    if prior_asks >= max_attempts:
        logger.info("clarification_exhausted", prior_asks=prior_asks, max_attempts=max_attempts)
        return {
            "clarification_needed": False,
            "clarification_pending": False,
            "escalation_needed": True,
            "clarification_attempts": prior_asks,
            "error": "clarification_exhausted",
        }

    # ── Compose the follow-up question ────────────────────────────
    if slot == "ambiguous_type" and pending_value:
        situation = (
            f"The customer gave the value '{pending_value}' but did not say whether it is an "
            f"order, invoice, or customer number."
        )
    else:
        situation = (
            "The customer's question needs a record lookup but they did not provide any "
            "order, invoice, or customer number."
        )

    lang_name = "Arabic" if lang == "ar" else "English"
    system_prompt = CLARIFICATION_SYSTEM_PROMPT.format(
        situation=situation,
        lang=lang,
        lang_name=lang_name,
        pending_value=pending_value or "the number",
    )

    question = ""
    try:
        result = await llm_fast.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=state.get("issue_description", "") or "I need help"),
        ])
        question = (result.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.warning("clarification_generation_failed", error=str(exc))

    if not question:
        if slot == "ambiguous_type" and pending_value:
            question = _ask_ambiguous(pending_value, lang)
        else:
            question = _ASK_IDENTIFIER_AR if lang == "ar" else _ASK_IDENTIFIER_EN

    logger.info(
        "clarification_asked",
        slot=slot,
        prior_asks=prior_asks,
        language=lang,
        length=len(question),
    )

    return {
        "language": lang,
        "draft_response": question,
        "final_response": question,
        "clarification_needed": False,   # handled this turn
        "clarification_pending": True,   # this turn is a question
        "clarification_attempts": prior_asks + 1,
        "review_required": False,
        "escalation_needed": False,
        "confidence_score": 0.0,
        "rag_sources": [],
    }

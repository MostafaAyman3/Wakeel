"""
GreetingNode — answers pure social / small-talk messages directly.

Shortest path in the graph: intent_router -> greeting_node -> END.
No RAG, no CRM/DB lookup, no human-review gate. Never raises.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from agents.m3.schemas.m3_state import M3State
from agents.prompts.greeting_agent import GREETING_SYSTEM_PROMPT
from agents.shared.llm_client import llm_fast
from backend.core.logging import get_logger

logger = get_logger(__name__)

# Static fallbacks if the LLM call fails.
_FALLBACK_AR = "أهلاً بك! كيف يمكنني مساعدتك اليوم؟"
_FALLBACK_EN = "Hello! How can I help you today?"


def _detect_language(text: str) -> str:
    """Arabic if any char is in the Arabic Unicode range, else English."""
    return "ar" if any("؀" <= c <= "ۿ" for c in text) else "en"


async def greet(state: M3State) -> dict:
    """Generate a short friendly reply to a social message."""
    message: str = state.get("issue_description", "") or ""
    lang: str = state.get("language", "auto") or "auto"
    if lang == "auto" or not lang:
        lang = _detect_language(message)

    lang_name = "Arabic" if lang == "ar" else "English"
    system_prompt = GREETING_SYSTEM_PROMPT.format(lang=lang, lang_name=lang_name)

    reply = ""
    try:
        result = await llm_fast.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=message or "Hi"),
        ])
        reply = (result.content or "").strip()
    except Exception as exc:
        logger.warning("greeting_generation_failed", error=str(exc))

    if not reply:
        reply = _FALLBACK_AR if lang == "ar" else _FALLBACK_EN

    logger.info("greeting_generated", language=lang, length=len(reply))

    return {
        "language": lang,
        "draft_response": reply,
        "final_response": reply,
        "review_required": False,
        "escalation_needed": False,
        "confidence_score": 1.0,
        "rag_sources": [],
    }

"""
IntentRouterNode — classifies an incoming support message into a route.

Routes:
  greeting           → greeting_node (friendly reply)
  general_knowledge  → rag_node → response_generator
  customer_issue     → input_parser → … (existing M3 pipeline)
  hybrid             → rag_node → input_parser → … (merged answer)

Falls back to customer_issue when confidence < 0.5 or on any LLM error.

Conversation-aware (Fix 3): when ``chat_history`` is present in state (only when
the request carried a ``session_id``), the last 3 turns are given to the router so
follow-up messages inherit the previous turn's intent. Without a ``session_id``
the router is single-turn (known limitation, not a bug).
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from agents.m3.schemas.m3_state import M3State
from agents.prompts.support_router import SUPPORT_ROUTER_SYSTEM_PROMPT
from agents.shared.llm_client import llm_primary
from backend.core.logging import get_logger

logger = get_logger(__name__)

_LOW_CONFIDENCE_THRESHOLD = 0.5
_VALID_ROUTES = {"greeting", "general_knowledge", "customer_issue", "hybrid"}
_VALID_COLLECTIONS = {"support_kb", "tax", "none"}
_HISTORY_TURNS = 3  # hard cap (default 3) — last N turns fed to the router


def _detect_language(text: str) -> str:
    """Arabic if any char is in the Arabic Unicode range, else English.

    Detected here (the router runs first for every message) so all downstream
    paths — including the knowledge path that skips InputParser — inherit the
    language. (Fix 2 Part A)
    """
    return "ar" if any("؀" <= c <= "ۿ" for c in text or "") else "en"


def _format_history(chat_history: list[dict] | None) -> str:
    """Format the last _HISTORY_TURNS turns as 'role: text' lines (trimmed)."""
    if not chat_history:
        return ""
    recent = chat_history[-_HISTORY_TURNS:]
    lines = []
    for turn in recent:
        role = turn.get("role", "user")
        content = (turn.get("content", "") or "").strip().replace("\n", " ")
        if len(content) > 200:
            content = content[:200] + "…"
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


class RouterOutput(BaseModel):
    route: str = Field(default="customer_issue")
    collection: str = Field(default="none")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reasoning: str = Field(default="")


# Routing is the single most critical classification in the graph: a misroute
# sends a knowledge question into the CRM/escalation path. gpt-4o-mini proved
# non-deterministic on Arabic here (knowledge questions collapsed to
# customer_issue), so the router uses the primary model (gpt-4o) for reliability.
_router_llm = llm_primary.with_structured_output(RouterOutput, method="function_calling")


async def route_intent(state: M3State) -> dict:
    """Classify the customer message and set route/rag_collection.

    Always returns — never raises.
    """
    query: str = state.get("issue_description", "") or ""
    language: str = state.get("language", "auto") or "auto"
    if language == "auto":
        language = _detect_language(query)

    # Conversation-aware routing (Fix 3): include the last N turns when available.
    history_block = _format_history(state.get("chat_history"))
    user_content = ""
    if history_block:
        user_content += f"Recent conversation (oldest first):\n{history_block}\n\n"
    user_content += f"Customer message: {query}\nDetected language: {language}"

    messages = [
        SystemMessage(content=SUPPORT_ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    try:
        result: RouterOutput = await _router_llm.ainvoke(messages)

        route = result.route if result.route in _VALID_ROUTES else "customer_issue"
        collection = result.collection if result.collection in _VALID_COLLECTIONS else "none"
        confidence = max(0.0, min(1.0, result.confidence))

        if confidence < _LOW_CONFIDENCE_THRESHOLD:
            route = "customer_issue"
            collection = "none"

        logger.info(
            "intent_routed",
            route=route,
            collection=collection,
            confidence=confidence,
            reasoning=result.reasoning,
        )

        return {
            "route": route,
            "route_confidence": confidence,
            "rag_collection": collection,
            "language": language,
        }

    except Exception as exc:
        logger.warning("intent_router_failed", error=str(exc))
        return {
            "route": "customer_issue",
            "route_confidence": 0.0,
            "rag_collection": "none",
            "language": language,
        }

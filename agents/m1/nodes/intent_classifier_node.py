"""
IntentClassifierNode — classifies user query intent using GPT-4o-mini.

Blueprint reference: M1 Sprint 1, sections 2.3 + 2.5
5 intents: financial_query · operational_query · invoice_analysis ·
           tax_reasoning · clarification_needed

Also performs automatic language detection (AR/EN) from the query text
when the ``language`` field is empty or set to ``"auto"``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agents.shared.llm_client import llm_fast
from agents.m1.schemas.m1_state import M1State
from agents.prompts.intent_classifier import INTENT_CLASSIFIER_SYSTEM_PROMPT


# ── Structured‑output schema ────────────────────────────────────

class IntentClassification(BaseModel):
    """JSON schema returned by the LLM via ``with_structured_output``."""

    intent: str = Field(
        description=(
            "Exactly one of: financial_query, operational_query, "
            "invoice_analysis, tax_reasoning, clarification_needed"
        ),
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0",
        ge=0.0,
        le=1.0,
    )
    extracted_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters extracted from the query",
    )
    reasoning: str = Field(
        default="",
        description="One-sentence justification for the classification",
    )


# ── Constants ────────────────────────────────────────────────────

VALID_INTENTS: set[str] = {
    "financial_query",
    "operational_query",
    "invoice_analysis",
    "tax_reasoning",
    "clarification_needed",
}

LOW_CONFIDENCE_THRESHOLD: float = 0.4


# ── Language auto-detection ──────────────────────────────────────

def detect_language(text: str) -> str:
    """Auto-detect language from text using the Arabic Unicode range.

    Rule (from user spec):
        ``"ar"`` if any character is in U+0600–U+06FF, else ``"en"``.
    """
    return "ar" if any("\u0600" <= c <= "\u06FF" for c in text) else "en"


# ── Node function ────────────────────────────────────────────────

async def classify_intent(state: M1State) -> dict:
    """Classify the user's query intent and extract parameters.

    • Uses ``llm_fast`` (GPT-4o-mini) with structured output.
    • Auto-detects language when ``language`` is absent or ``"auto"``.
    • Injects ``chat_history`` as prior turns for multi-turn context.
    • Falls back to ``clarification_needed`` on any LLM error.
    """
    query: str = state["query"]
    language: str = state.get("language", "") or ""
    chat_history: list = state.get("chat_history", [])

    # ── Auto-detect language ────────────────────────────
    if not language or language == "auto":
        language = detect_language(query)

    # ── Build LLM messages ────────────────────────────
    # Start with the system prompt, then inject prior conversation
    # turns (up to last 6 messages) so the LLM can resolve pronouns
    # and relative references (e.g. "قارنه", "same year").
    messages = [SystemMessage(content=INTENT_CLASSIFIER_SYSTEM_PROMPT)]

    # Inject history — role mapping: "user" → HumanMessage, anything else → AIMessage
    for turn in chat_history[-6:]:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if not content:
            continue
        if role == "user":
            messages.append(HumanMessage(content=f"[previous turn] {content}"))
        else:
            messages.append(AIMessage(content=f"[previous turn] {content}"))

    # Current query (the one to classify)
    messages.append(
        HumanMessage(content=f"User query: {query}\nDetected language: {language}")
    )

    # ── Call LLM with structured output ───────────────────────
    # Use method="function_calling" because OpenAI's strict structured
    # output mode rejects `dict` fields with additionalProperties.
    classifier = llm_fast.with_structured_output(
        IntentClassification, method="function_calling"
    )

    try:
        result: IntentClassification = await classifier.ainvoke(messages)

        # Validate intent value
        intent = result.intent if result.intent in VALID_INTENTS else "clarification_needed"
        confidence = max(0.0, min(1.0, result.confidence))

        # Low confidence → ask for clarification
        if confidence < LOW_CONFIDENCE_THRESHOLD and intent != "clarification_needed":
            intent = "clarification_needed"

        return {
            "language": language,
            "intent": intent,
            "intent_confidence": confidence,
            "extracted_params": result.extracted_params,
            "needs_clarification": intent == "clarification_needed",
        }

    except Exception as exc:
        # Graceful fallback — never crash the graph
        return {
            "language": language,
            "intent": "clarification_needed",
            "intent_confidence": 0.0,
            "extracted_params": {},
            "needs_clarification": True,
            "error": f"Intent classification failed: {exc}",
        }

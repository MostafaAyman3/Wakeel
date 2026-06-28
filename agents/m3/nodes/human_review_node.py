from __future__ import annotations

from agents.m3.schemas.m3_state import M3State
from backend.core.logging import get_logger

logger = get_logger(__name__)

_FINANCIAL_KEYWORDS = [
    "refund", "compensation", "discount", "will pay", "will receive",
    "credit", "reimburse", "waive",
    "استرداد", "تعويض", "خصم", "سيدفع", "سوف تحصل",
]
_DELIVERY_PROMISE_KEYWORDS = [
    "will arrive", "will be delivered",
    "سيصل", "سيتم التوصيل", "خلال", "في موعد",
]
# Phrase-level patterns: specific enough to avoid common false positives.
# "by X" is only a promise when X is a time reference, not a preposition of agent.
_DELIVERY_PROMISE_PHRASES = [
    "by tomorrow", "by end of", "by monday", "by tuesday", "by wednesday",
    "by thursday", "by friday", "by saturday", "by sunday", "by next",
    "within 24", "within 48", "within 1 ", "within 2 ", "within 3 ",
    "within one", "within two", "within three",
]


def _contains_financial_commitment(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    for kw in _FINANCIAL_KEYWORDS:
        if kw in text_lower:
            return True
    for kw in _DELIVERY_PROMISE_KEYWORDS:
        if kw in text_lower:
            return True
    padded = f" {text_lower} "
    for phrase in _DELIVERY_PROMISE_PHRASES:
        if phrase in padded:
            return True
    return False


async def human_review_gate(state: M3State) -> dict:
    """Evaluate routing rules and set ``review_required``.

    Rules (M3_Sprints.md §Sprint 4):

    ======================================  ============================
    Condition                               Decision
    ======================================  ============================
    ``issue_type == billing_dispute``       Mandatory review
    ``issue_type == refund_request``        Mandatory review
    ``confidence_score < 0.70``            Mandatory review
    Response has financial/delivery promise Mandatory review
    ``escalation_needed == True``           Skip review → direct escalate
    ``status_inquiry`` / high-confidence    No review required (optional)
    ======================================  ============================
    """
    issue_type = state.get("issue_type")
    confidence = state.get("confidence_score", 0.0)
    escalation_needed = state.get("escalation_needed", False)
    draft_response = state.get("draft_response", "")
    route = state.get("route", "customer_issue")

    # Fix 1 (Option A): pure-knowledge / greeting answers are grounded in the
    # curated KB and make no account-specific or financial commitment, so they
    # never need human review. Short-circuit BEFORE the confidence/keyword checks
    # (a CRM-centric confidence of 0.0 must not hold a valid knowledge answer).
    if route in ("greeting", "general_knowledge"):
        logger.info("review_gate_routing", decision="auto_send", reason="knowledge_or_greeting", route=route)
        return {"review_required": False}

    # escalation_needed → skip review, go directly to escalation
    if escalation_needed:
        logger.info("review_gate_routing", decision="escalate", issue_type=issue_type)
        return {"review_required": False}

    # billing_dispute → mandatory review
    if issue_type == "billing_dispute":
        logger.info("review_gate_routing", decision="mandatory_review", reason="billing_dispute")
        return {"review_required": True}

    # refund_request → mandatory review
    if issue_type == "refund_request":
        logger.info("review_gate_routing", decision="mandatory_review", reason="refund_request")
        return {"review_required": True}

    # confidence < 0.70 → mandatory review
    if confidence < 0.70:
        logger.info("review_gate_routing", decision="mandatory_review", reason="low_confidence", confidence=confidence)
        return {"review_required": True}

    # Financial commitment or delivery promise in draft → mandatory review
    if _contains_financial_commitment(draft_response):
        logger.info("review_gate_routing", decision="mandatory_review", reason="financial_commitment")
        return {"review_required": True}

    # status_inquiry, general_complaint, high-confidence → optional (no review required)
    logger.info("review_gate_routing", decision="optional", issue_type=issue_type, confidence=confidence)
    return {"review_required": False}

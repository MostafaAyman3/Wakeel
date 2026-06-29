"""
InvalidIdNode — handles the "supplied identifier not found" branch (Feature 006).

Invoked when completeness_check returns data_completeness == 0.0 AND the
customer_identifier has a non-empty type + value (i.e., an ID was given but
matched no record).

Flow:
    1. Count the trailing streak of prior assistant turns tagged metadata.invalid_id.
    2. attempt = streak + 1.
    3. attempt < max_attempts  → friendly retry message.
    4. attempt >= max_attempts → escalation menu (re-enter / human / phone-email).
    5. Return partial M3State update; never raises.
"""

from __future__ import annotations

from backend.core.config import get_settings
from agents.m3.schemas.m3_state import M3State
from backend.core.logging import get_logger

logger = get_logger(__name__)

# ── Static message templates ──────────────────────────────────────────────────

_RETRY_EN = (
    "We couldn't find your order/invoice using that ID. "
    "Please rewrite your ID carefully and try again."
)
_RETRY_AR = (
    "لم نتمكن من العثور على طلبك/فاتورتك بهذا الرقم. "
    "من فضلك أعد كتابة الرقم بعناية وحاول مرة أخرى."
)

_MENU_EN_FULL = (
    "We still cannot find your order after 3 attempts. "
    "Please choose one of the following:\n"
    "1) Re-enter your ID\n"
    "2) Talk to a human agent\n"
    "3) Search using phone/email instead"
)
_MENU_EN_SHORT = (
    "We still cannot find your order after 3 attempts. "
    "Please choose one of the following:\n"
    "1) Re-enter your ID\n"
    "2) Talk to a human agent"
)
_MENU_AR_FULL = (
    "ما زلنا غير قادرين على العثور على طلبك بعد 3 محاولات. "
    "من فضلك اختر أحد الخيارات التالية:\n"
    "١) إعادة إدخال الرقم\n"
    "٢) التحدث مع موظف خدمة العملاء\n"
    "٣) البحث باستخدام رقم الهاتف أو البريد الإلكتروني"
)
_MENU_AR_SHORT = (
    "ما زلنا غير قادرين على العثور على طلبك بعد 3 محاولات. "
    "من فضلك اختر أحد الخيارات التالية:\n"
    "١) إعادة إدخال الرقم\n"
    "٢) التحدث مع موظف خدمة العملاء"
)


# ── Streak helper ─────────────────────────────────────────────────────────────

def _trailing_invalid_id_streak(chat_history: list) -> int:
    """Count consecutive most-recent assistant turns tagged metadata.invalid_id == True.

    Mirrors clarification_node._count_prior_asks — scans backwards through
    chat_history, stops at the first assistant turn NOT tagged invalid_id (or
    at any non-assistant turn that breaks the streak).  Never raises.
    """
    count = 0
    for turn in reversed(chat_history):
        if not isinstance(turn, dict):
            continue
        role = turn.get("role", "")
        if role != "assistant":
            # user turns don't break the streak — skip them and keep looking back
            continue
        metadata = turn.get("metadata") or {}
        if metadata.get("invalid_id"):
            count += 1
        else:
            # First untagged assistant turn ends the streak
            break
    return count


# ── Node ──────────────────────────────────────────────────────────────────────

async def handle_invalid_id(state: M3State) -> dict:
    """Return retry message (attempts 1–2) or escalation menu (attempt 3+).

    Never raises — any unexpected exception returns the EN retry message as a
    safe fallback so the customer always gets a reply.
    """
    settings = get_settings()

    try:
        chat_history: list = state.get("chat_history") or []
        language: str = (state.get("language") or "en").lower()
        identifier: dict = state.get("customer_identifier") or {}

        prior = _trailing_invalid_id_streak(chat_history)
        attempt = prior + 1
        max_attempts = settings.m3_invalid_id_max_attempts

        logger.info(
            "invalid_id_attempt",
            attempt=attempt,
            max_attempts=max_attempts,
            identifier_type=identifier.get("type"),
            language=language,
        )

        if attempt < max_attempts:
            # ── Retry branch (attempts 1 to max-1) ───────────────────
            message = _RETRY_AR if language == "ar" else _RETRY_EN
            logger.info("invalid_id_retry", attempt=attempt, language=language)
            return {
                "final_response": message,
                "draft_response": message,
                "invalid_id_attempts": attempt,
                "invalid_id_pending": True,
                "invalid_id_menu_shown": False,
                "escalation_needed": False,
                "review_required": False,
                "confidence_score": 0.0,
                "rag_sources": [],
            }

        else:
            # ── Escalation menu branch (attempt >= max_attempts) ──────
            alt_enabled = settings.m3_alt_lookup_enabled
            if language == "ar":
                message = _MENU_AR_FULL if alt_enabled else _MENU_AR_SHORT
            else:
                message = _MENU_EN_FULL if alt_enabled else _MENU_EN_SHORT

            logger.info(
                "invalid_id_menu", attempt=attempt, alt_enabled=alt_enabled, language=language
            )
            return {
                "final_response": message,
                "draft_response": message,
                "invalid_id_attempts": attempt,
                "invalid_id_pending": True,
                "invalid_id_menu_shown": True,
                "escalation_needed": False,
                "review_required": False,
                "confidence_score": 0.0,
                "rag_sources": [],
            }

    except Exception as exc:  # pragma: no cover
        logger.error("invalid_id_node_error", error=str(exc))
        fallback = _RETRY_EN
        return {
            "final_response": fallback,
            "draft_response": fallback,
            "invalid_id_attempts": 1,
            "invalid_id_pending": True,
            "invalid_id_menu_shown": False,
            "escalation_needed": False,
            "review_required": False,
            "confidence_score": 0.0,
            "rag_sources": [],
        }

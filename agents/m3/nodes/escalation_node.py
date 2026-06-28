from __future__ import annotations

from agents.m3.schemas.m3_state import M3State
from backend.core.logging import get_logger

logger = get_logger(__name__)


async def escalate_case(state: M3State) -> dict:
    """Generate escalation summary, log to audit trail, and set final response.

    Called by the graph when ``escalation_needed`` is ``True``.

    Produces:
        - Case summary (identifier, issue_type, fetched data, escalation reason)
        - Audit trail log entry
        - ``final_response`` with an escalation message for the customer
        - ``escalation_summary`` dict for the frontend escalation view
    """
    identifier = state.get("customer_identifier", {})
    issue_type = state.get("issue_type")
    fetched_data = state.get("fetched_data", {})
    issue_description = state.get("issue_description", "")

    # Fix 5: the no-data escalation branch skips the IssueClassifier, so issue_type
    # is often None here. Infer a lightweight category from the message text so the
    # escalation summary + audit trail are labelled (no customer-facing impact).
    if not issue_type:
        issue_type = _infer_issue_type(issue_description)

    reason = _get_escalation_reason(state)

    summary: dict = {
        "identifier": identifier,
        "issue_type": issue_type,
        "issue_description": issue_description,
        "data_summary": {k: bool(v) for k, v in fetched_data.items()},
        "escalation_reason": reason,
    }

    # Log to audit trail (best-effort — never blocks the response)
    try:
        from backend.services.audit_service import log_decision

        case_id = str(identifier.get("value", "unknown"))
        await log_decision(
            case_id=case_id,
            issue_type=issue_type,
            confidence_score=state.get("confidence_score", 0.0),
            review_required=False,
            action_taken="escalated",
            details=str(reason),
        )
    except Exception as exc:
        logger.warning("escalation_audit_failed", error=str(exc))

    # Final response — escalation message. When a reference was provided but
    # matched no record, name it so the customer can verify (FR-008).
    lang = state.get("language", "en") or "en"
    ref_value = (identifier or {}).get("value")
    no_data = state.get("data_completeness", 0.0) == 0.0
    if lang == "ar":
        if ref_value and no_data:
            final_response = (
                f"لم نتمكن من العثور على \"{ref_value}\" في نظامنا. "
                "يرجى التأكد من الرقم، وقد قمنا بتحويل حالتك إلى فريق الدعم للمتابعة."
            )
        else:
            final_response = (
                "تم إحالة حالتك إلى فريق الدعم المختص. "
                "سيتواصل معك أحد ممثلي الدعم خلال 24 ساعة للمتابعة."
            )
    else:
        if ref_value and no_data:
            final_response = (
                f"We couldn't find \"{ref_value}\" in our system. "
                "Please double-check the reference — we've also routed your case to our support team."
            )
        else:
            final_response = (
                "Your case has been escalated to our support team. "
                "A support representative will contact you within 24 hours."
            )

    logger.info(
        "case_escalated",
        case_id=str(identifier.get("value", "unknown")),
        issue_type=issue_type,
        reason=reason,
    )

    return {
        "final_response": final_response,
        "escalation_summary": summary,
    }


_ISSUE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "refund_request": ("refund", "money back", "استرداد", "ارجاع فلوس", "استرجاع"),
    "billing_dispute": ("invoice", "charge", "overcharge", "bill", "فاتورة", "خصم", "مبلغ"),
    "shipping_issue": ("ship", "delivery", "deliver", "courier", "track", "شحن", "توصيل", "تتبع"),
    "status_inquiry": ("where is", "status", "when will", "أين", "حالة", "متى"),
}


def _infer_issue_type(text: str) -> str | None:
    """Best-effort keyword classification when the classifier was skipped."""
    if not text:
        return None
    low = text.lower()
    # refund/billing take precedence (financial) over status/shipping
    for itype in ("refund_request", "billing_dispute", "shipping_issue", "status_inquiry"):
        if any(kw in low for kw in _ISSUE_KEYWORDS[itype]):
            return itype
    return "general_complaint"


def _get_escalation_reason(state: M3State) -> str:
    """Determine the reason for escalation based on state."""
    reasons: list[str] = []

    if state.get("data_completeness", 0.0) == 0.0:
        reasons.append("No data found for the provided identifier")
    if state.get("missing_fields"):
        reasons.append(f"Missing data sources: {', '.join(state['missing_fields'])}")

    return "; ".join(reasons) if reasons else "System escalation flag set"

"""Stratified router separating business intent from execution complexity."""

from __future__ import annotations

import re
import unicodedata
from datetime import date

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from agents.m1.schemas.analysis_models import RouteDecision
from agents.m1.schemas.m1_state import M1State
from agents.prompts.m1_router import M1_ROUTER_SYSTEM_PROMPT
from agents.shared.llm_client import llm_fast

logger = structlog.get_logger(__name__)

_ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
_SUPPORT_SIGNALS = (
    "شكوى", "مشكله", "مشكلة", "refund", "استرجاع", "تصعيد", "كلم مدير",
    "ticket", "case", "فين طلبي", "تتبع", "اتأخر طلبي",
    "الفاتوره غلط", "الفاتورة غلط", "لم اطلب", "ما طلبتش",
)
_GREETING_SIGNALS = (
    "اهلا", "مرحبا", "صباح الخير", "مساء الخير", "hello", "hi", "hey",
    "مين انت", "من انت", "what can you do", "تقدر تعمل ايه",
)
_OOS_SIGNALS = (
    "الطقس", "weather", "اكتب قصيده", "اكتب قصيدة", "football",
    "كره القدم", "كرة القدم",
)
_PREDICTION_SIGNALS = (
    "السنه الجايه", "السنة الجاية", "next year", "forecast", "predict",
    "توقع",
)
_FOLLOWUP_SIGNALS = (
    "ليه", "كده", "دول", "دي", "ده", "تفاصيل", "كمان", "قارنها",
    "قارنهم", "compare it", "those", "them", "show more", "breakdown",
    "ركزلي", "طب ", "طيب ",
)
_COMPLEXITY_SIGNALS = (
    "ليه", "سبب", "اسباب", "أسباب", "حلل", "تحليل", "drivers", "why",
    "reason", "analyse", "analyze", "مقارنة", "مقارنه", "compare", " vs ",
    "والمنتج", "والفرع", "حسب المنتج وحسب", "what caused",
)
_AMBIGUOUS_SIGNALS = (
    "عايز تقرير", "وريني الارقام", "وريني ارقام", "هات بيانات",
    "show me something", "show me data", "i need a report",
)
_DOMAIN_SIGNALS: dict[str, tuple[str, ...]] = {
    "tax": (
        "ضريبه", "ضريبة", "القيمه المضافه", "القيمة المضافة", "vat", "tax",
    ),
    "invoice": (
        "فواتير المورد", "فاتوره مورد", "فاتورة مورد", "vendor invoice",
        "invoice analysis", "analyze vendor invoices",
    ),
    "collections": (
        "متاخر", "متأخر", "تحصيل", "aging", "overdue", "late payment",
    ),
    "inventory": (
        "مخزون", "اعاده الطلب", "إعادة الطلب", "inventory", "stock",
    ),
    "orders": (
        "عدد الطلبات", "حاله الطلبات", "حالة الطلبات", "orders were",
        "orders delivered", "pending orders", "delivered this", "كام طلب",
    ),
    "sales": (
        "مبيعات", "ايرادات", "إيرادات", "revenue", "sales", "top products",
        "product category", "customers by revenue",
    ),
    "financial": (
        "مصروفات", "ارباح", "أرباح", "صافي الدخل", "expenses", "profit",
        "financial summary", "executive summary",
    ),
}

_DOMAIN_TO_LEGACY_INTENT = {
    "financial": "financial_query",
    "sales": "financial_query",
    "collections": "financial_query",
    "inventory": "operational_query",
    "orders": "operational_query",
    "invoice": "invoice_analysis",
    "tax": "tax_reasoning",
    "support": "support",
    "conversation": "conversation",
    "out_of_scope": "out_of_scope",
    "ambiguous": "clarification_needed",
}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text).lower().strip()
    normalized = _ARABIC_DIACRITICS.sub("", normalized)
    return (
        normalized.replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ى", "ي")
        .replace("ة", "ه")
    )


def _signal_present(text: str, signal: str) -> bool:
    normalized_signal = normalize_text(signal)
    if normalized_signal.isascii():
        return bool(
            re.search(
                rf"(?<!\w){re.escape(normalized_signal)}(?!\w)",
                text,
            )
        )
    return normalized_signal in text


def _contains_any(text: str, signals: tuple[str, ...]) -> list[str]:
    return [signal for signal in signals if _signal_present(text, signal)]


def _infer_domain(text: str) -> tuple[str, list[str]]:
    for domain, signals in _DOMAIN_SIGNALS.items():
        matches = _contains_any(text, signals)
        if matches:
            return domain, matches
    return "financial", []


def _heuristic_route(state: M1State) -> RouteDecision | None:
    query = state.get("query", "")
    text = normalize_text(query)
    has_context = bool(state.get("prior_analysis_frame"))

    if state.get("clarification_pending"):
        return RouteDecision(
            assigned_tier="T2",
            domain_intent="ambiguous",
            confidence=0.95,
            reasoning="The user is answering a pending clarification.",
            signals=["clarification_pending"],
        )

    support = _contains_any(text, _SUPPORT_SIGNALS)
    if support:
        return RouteDecision(
            assigned_tier="T6",
            domain_intent="support",
            confidence=0.95,
            reasoning="The request contains customer-support or escalation signals.",
            signals=support,
        )

    greetings = _contains_any(text, _GREETING_SIGNALS)
    if greetings:
        return RouteDecision(
            assigned_tier="T0",
            domain_intent="conversation",
            confidence=0.95,
            reasoning="The request is conversational and does not require data.",
            signals=greetings,
        )

    oos = _contains_any(text, _OOS_SIGNALS)
    predictions = _contains_any(text, _PREDICTION_SIGNALS)
    if oos or predictions:
        return RouteDecision(
            assigned_tier="T5",
            domain_intent="out_of_scope",
            confidence=0.9,
            reasoning="The request is outside current historical ERP analytics.",
            signals=oos + predictions,
        )

    followup = _contains_any(text, _FOLLOWUP_SIGNALS)
    token_count = len(text.split())
    if has_context and (followup or token_count < 8):
        return RouteDecision(
            assigned_tier="T2",
            domain_intent="ambiguous",
            confidence=0.85,
            reasoning="The request is short or referential and prior analysis exists.",
            signals=followup or ["short_contextual_turn"],
        )

    ambiguous = _contains_any(text, _AMBIGUOUS_SIGNALS)
    if ambiguous:
        return RouteDecision(
            assigned_tier="T4",
            domain_intent="ambiguous",
            confidence=0.98,
            reasoning="The request is too broad to identify a metric or entity.",
            signals=ambiguous,
            missing_slots=["metric_or_report_type"],
        )

    domain, domain_signals = _infer_domain(text)
    complexity = _contains_any(text, _COMPLEXITY_SIGNALS)
    if domain_signals and complexity:
        return RouteDecision(
            assigned_tier="T3",
            domain_intent=domain,
            confidence=0.9,
            reasoning="The request is analytical and contains complexity signals.",
            signals=domain_signals + complexity,
        )
    if domain_signals:
        return RouteDecision(
            assigned_tier="T1",
            domain_intent=domain,
            confidence=0.9,
            reasoning="The request matches a direct approved ERP query domain.",
            signals=domain_signals,
        )
    return None


def _legacy_params(frame: dict) -> dict:
    params: dict = {}
    if frame.get("date_range"):
        params["date_range"] = frame["date_range"]
    if frame.get("comparison_range"):
        params["comparison"] = True
        params["compare_range"] = frame["comparison_range"]
    for entity in frame.get("entities", []):
        entity_type = entity.get("type")
        value = entity.get("value")
        if entity_type and value:
            params[entity_type] = value
    params.update(frame.get("filters", {}))
    return params


async def route_intent(state: M1State) -> dict:
    query_text = state.get("query", "")
    language = state.get("language", "")
    if not language or language == "auto":
        language = (
            "ar"
            if any("\u0600" <= char <= "\u06ff" for char in query_text)
            else "en"
        )
    heuristic = _heuristic_route(state)
    if heuristic is not None:
        decision = heuristic
    else:
        query = state.get("query", "")
        prior_frame = state.get("prior_analysis_frame", {})
        history = state.get("chat_history", [])[-4:]
        prompt = (
            f"Current date: {date.today().isoformat()}\n"
            f"Current query: {query}\n"
            f"Prior analysis frame: {prior_frame}\n"
            f"Recent turns: {history}\n"
        )
        router = llm_fast.with_structured_output(
            RouteDecision,
            method="function_calling",
        )
        try:
            decision = await router.ainvoke(
                [
                    SystemMessage(content=M1_ROUTER_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
            )
        except Exception as exc:
            logger.warning("m1_router_llm_failed", error=str(exc))
            decision = RouteDecision(
                assigned_tier="T4",
                domain_intent="ambiguous",
                confidence=0.0,
                reasoning="Routing failed safely and requires clarification.",
                signals=["router_error"],
                missing_slots=["request_details"],
            )

    frame = decision.analysis_frame.model_dump(exclude_none=True)
    # Preserve resolved context for referential routes.
    if decision.assigned_tier == "T2" and not any(frame.values()):
        frame = state.get("prior_analysis_frame", {})

    legacy_intent = _DOMAIN_TO_LEGACY_INTENT.get(
        decision.domain_intent,
        "clarification_needed",
    )
    if decision.assigned_tier == "T4":
        legacy_intent = "clarification_needed"

    return {
        "language": language,
        "assigned_tier": decision.assigned_tier,
        "domain_intent": decision.domain_intent,
        "router_confidence": decision.confidence,
        "router_reasoning": decision.reasoning,
        "route_signals": decision.signals,
        "analysis_frame": frame,
        "intent": legacy_intent,
        "intent_confidence": decision.confidence,
        "extracted_params": _legacy_params(frame),
        "clarification_missing_slots": decision.missing_slots,
        "needs_clarification": decision.assigned_tier == "T4",
    }


def route_to_tier(state: M1State) -> str:
    return state.get("assigned_tier", "T4")

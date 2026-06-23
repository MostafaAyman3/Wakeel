"""Resolve T2 requests against structured analytical context."""

from __future__ import annotations

from agents.m1.nodes.intent_router_node import normalize_text
from agents.m1.schemas.m1_state import M1State

_REASON_SIGNALS = ("ليه", "فسر", "اشرح", "why", "explain", "reason")
_DETAIL_SIGNALS = ("تفاصيل", "وريني", "ركز", "details", "show more", "breakdown")
_COMPARE_SIGNALS = ("قارن", "مقارنه", "مقارنة", "compare", "vs", "الفرق")
_SUMMARY_SIGNALS = ("لخص", "ملخص", "summary", "summarize")


def _has(text: str, signals: tuple[str, ...]) -> bool:
    return any(normalize_text(signal) in text for signal in signals)


async def resolve_followup(state: M1State) -> dict:
    text = normalize_text(state.get("query", ""))
    prior = state.get("prior_analysis_frame", {})

    if state.get("clarification_pending"):
        original = state.get("clarification_original_query", "")
        return {
            "query": f"{original}\nClarification answer: {state.get('query', '')}",
            "followup_mode": "refine",
            "analysis_frame": prior,
            "clarification_pending": False,
            "needs_clarification": False,
        }

    if _has(text, _SUMMARY_SIGNALS):
        mode = "summarize"
    elif _has(text, _COMPARE_SIGNALS):
        mode = "compare"
    elif _has(text, _DETAIL_SIGNALS):
        mode = "drill_down"
    elif _has(text, _REASON_SIGNALS):
        mode = "reason_only"
    else:
        mode = "refine"
    result: dict = {"followup_mode": mode, "analysis_frame": prior}
    if mode in {"reason_only", "summarize"}:
        key_metrics = state.get("prior_result_summary", {}).get("key_metrics", {})
        result["raw_data"] = [key_metrics] if key_metrics else []
        result["result_status"] = "complete" if key_metrics else "empty"
        result["result_format_hint"] = "narrative"
    return result


def route_followup(state: M1State) -> str:
    if state.get("followup_mode") in {"reason_only", "summarize"}:
        return "reason"
    return "requery"

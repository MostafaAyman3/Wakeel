"""Resolve T2 requests against structured analytical context.

Uses signal matching as a fast path for obvious cases (reason_only,
summarize) and falls back to an LLM call to understand what the user
wants to change in the analysis frame for refine/drill_down/compare.
"""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import date

import structlog
from langchain_core.messages import HumanMessage, SystemMessage

from agents.m1.nodes.intent_router_node import normalize_text
from agents.m1.schemas.analysis_models import FollowUpResolution
from agents.m1.schemas.m1_state import M1State
from agents.prompts.m1_followup import M1_FOLLOWUP_SYSTEM_PROMPT
from agents.shared.llm_client import llm_fast

logger = structlog.get_logger(__name__)

# ── Fast-path signal lists ──────────────────────────────────────────
_REASON_SIGNALS = ("ليه", "فسر", "اشرح", "why", "explain", "reason")
_SUMMARY_SIGNALS = ("لخص", "ملخص", "summary", "summarize")


def _has(text: str, signals: tuple[str, ...]) -> bool:
    return any(
        re.search(rf"(^|\s){re.escape(normalize_text(signal))}", text)
        for signal in signals
    )


def _merge_resolution_into_frame(
    prior: dict,
    resolution: FollowUpResolution,
) -> dict:
    """Apply the LLM resolution deltas onto a copy of the prior frame."""
    frame = deepcopy(prior) if prior else {}

    # ── Filters ──
    existing_filters = frame.get("filters") or {}
    for key in resolution.remove_filters:
        existing_filters.pop(key, None)
    existing_filters.update(resolution.add_filters)
    frame["filters"] = existing_filters

    # ── Dimensions ──
    existing_dims = list(frame.get("dimensions") or [])
    for dim in resolution.remove_dimensions:
        if dim in existing_dims:
            existing_dims.remove(dim)
    for dim in resolution.add_dimensions:
        if dim not in existing_dims:
            existing_dims.append(dim)
    frame["dimensions"] = existing_dims

    # ── Entities ──
    existing_entities = list(frame.get("entities") or [])
    for entity in resolution.add_entities:
        entity_dict = entity.model_dump() if hasattr(entity, "model_dump") else entity
        existing_entities.append(entity_dict)
    frame["entities"] = existing_entities

    # ── Direct field overrides ──
    for update in resolution.frame_updates:
        field = update.field
        value = update.value
        if field in ("date_range", "comparison_range") and isinstance(value, dict):
            frame[field] = value
        elif field in ("metric", "grain", "analysis_type", "requested_output"):
            frame[field] = value

    return frame


async def _llm_resolve(
    query: str,
    prior_frame: dict,
    prior_summary: dict,
) -> FollowUpResolution:
    """Use the LLM to understand what the user wants to change."""
    prompt = (
        f"Current date: {date.today().isoformat()}\n"
        f"User follow-up message: {query}\n"
        f"Prior analysis frame: {json.dumps(prior_frame, ensure_ascii=False, default=str)}\n"
        f"Prior result summary: {json.dumps(prior_summary, ensure_ascii=False, default=str)}\n"
    )
    resolver = llm_fast.with_structured_output(
        FollowUpResolution,
        method="function_calling",
    )
    try:
        resolution = await resolver.ainvoke(
            [
                SystemMessage(content=M1_FOLLOWUP_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        return resolution
    except Exception as exc:
        logger.warning("followup_llm_failed", error=str(exc))
        # Safe fallback: treat as a refine that needs requery
        return FollowUpResolution(
            mode="refine",
            reasoning=f"LLM resolution failed: {exc}",
        )


async def resolve_followup(state: M1State) -> dict:
    text = normalize_text(state.get("query", ""))
    prior = state.get("prior_analysis_frame", {})
    prior_summary = state.get("prior_result_summary", {})

    # ── Clarification continuation ──
    if state.get("clarification_pending"):
        original = state.get("clarification_original_query", "")
        return {
            "query": f"{original}\nClarification answer: {state.get('query', '')}",
            "followup_mode": "refine",
            "analysis_frame": prior,
            "clarification_pending": False,
            "needs_clarification": False,
        }

    # ── Fast path: reason_only / summarize (no frame change needed) ──
    if _has(text, _REASON_SIGNALS) and not _has(text, ("قارن", "compare")):
        key_metrics = prior_summary.get("key_metrics", {})
        return {
            "followup_mode": "reason_only",
            "analysis_frame": prior,
            "raw_data": [key_metrics] if key_metrics else [],
            "result_status": "complete" if key_metrics else "empty",
            "result_format_hint": "narrative",
        }

    if _has(text, _SUMMARY_SIGNALS):
        key_metrics = prior_summary.get("key_metrics", {})
        return {
            "followup_mode": "summarize",
            "analysis_frame": prior,
            "raw_data": [key_metrics] if key_metrics else [],
            "result_status": "complete" if key_metrics else "empty",
            "result_format_hint": "narrative",
        }

    # ── LLM-powered deep resolution ──
    resolution = await _llm_resolve(
        query=state.get("query", ""),
        prior_frame=prior,
        prior_summary=prior_summary,
    )

    updated_frame = _merge_resolution_into_frame(prior, resolution)

    logger.info(
        "followup_resolved",
        mode=resolution.mode,
        reasoning=resolution.reasoning[:80] if resolution.reasoning else "",
        has_filter_updates=bool(resolution.add_filters),
        has_dimension_updates=bool(resolution.add_dimensions),
        frame_update_count=len(resolution.frame_updates),
    )

    result: dict = {
        "followup_mode": resolution.mode,
        "analysis_frame": updated_frame,
    }

    # Use rewritten query if provided
    if resolution.new_query_text:
        result["query"] = resolution.new_query_text

    # For reason_only/summarize from LLM (rare since fast path catches them)
    if resolution.mode in {"reason_only", "summarize"}:
        key_metrics = prior_summary.get("key_metrics", {})
        result["raw_data"] = [key_metrics] if key_metrics else []
        result["result_status"] = "complete" if key_metrics else "empty"
        result["result_format_hint"] = "narrative"

    return result


def route_followup(state: M1State) -> str:
    if state.get("followup_mode") in {"reason_only", "summarize"}:
        return "reason"
    return "requery"

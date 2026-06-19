"""
NarrativeGeneratorNode — Sprint 5.

Generates bilingual analytical narratives using GPT-4o and assembles
the unified final_response payload.

Blueprint reference: section 2.8 — Narrative Generator
Sprint plan: M1_Sprints.md Sprint 5

Skip condition:
    If ``narrative`` is already populated by an upstream node
    (tax_rag_node, invoice_analysis_tool), the LLM call is skipped
    to avoid double-generation. Only ``final_response`` is assembled.

Trigger condition:
    Generates a new narrative for:
    - db_query_tool results (Sprint 2 — does NOT produce narrative)
    - Any output_format that benefits from analysis (metric_card, chart, alert)
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from agents.m1.schemas.m1_state import M1State
from agents.prompts.narrative_generator import (
    ALERT_NARRATIVE_PROMPT,
    FORMAT_INSTRUCTIONS,
    NARRATIVE_GENERATION_PROMPT,
)
from agents.shared.llm_client import llm_primary

logger = structlog.get_logger(__name__)

_LANGUAGE_NAMES = {"ar": "Arabic", "en": "English"}
_MAX_DATA_ROWS_FOR_PROMPT = 20  # Cap data sent to LLM for token efficiency


async def generate_narrative(state: M1State) -> dict:
    """
    NarrativeGeneratorNode: generate analytical narrative + assemble final_response.

    Skip logic:
        If ``state["narrative"]`` is already a non-empty string AND the intent
        is ``tax_reasoning`` or ``invoice_analysis``, the LLM call is skipped.
        Only ``final_response`` is assembled from existing state.

    Returns:
        Partial M1State dict: { narrative, final_response }
    """
    raw_data: list = state.get("raw_data", [])
    output_format: str = state.get("output_format", "direct_text")
    intent: str = state.get("intent", "")
    language: str = state.get("language", "en")
    query: str = state.get("query", "")
    existing_narrative: str = state.get("narrative", "")
    anomaly_detected: bool = state.get("anomaly_detected", False)
    anomaly_details: dict = state.get("anomaly_details", {})
    chart_config: dict | None = state.get("chart_config")
    existing_response: dict = state.get("final_response", {})

    language_name = _LANGUAGE_NAMES.get(language, "English")

    # ── Skip condition: upstream already produced narrative ─────────────────
    upstream_intents = {"tax_reasoning", "invoice_analysis"}
    if existing_narrative and intent in upstream_intents:
        logger.info(
            "narrative_generator: skipping LLM call — upstream narrative exists",
            intent=intent,
            narrative_length=len(existing_narrative),
        )
        narrative = existing_narrative
    else:
        # ── Generate narrative via LLM ─────────────────────────────────────
        narrative = await _generate_narrative_llm(
            raw_data=raw_data,
            output_format=output_format,
            intent=intent,
            query=query,
            language=language,
            language_name=language_name,
            anomaly_detected=anomaly_detected,
            anomaly_details=anomaly_details,
        )

    # ── Assemble final_response ────────────────────────────────────────────
    # If upstream already built a final_response (tax_rag_node), merge with it
    if existing_response and intent == "tax_reasoning":
        # Preserve tax-specific fields, add format metadata
        final_response = {
            **existing_response,
            "format": output_format,
            "narrative": narrative,
            "chart_config": chart_config,
        }
    else:
        # Build fresh final_response (unified schema from Sprint 5 plan)
        alert_payload = None
        if anomaly_detected and anomaly_details:
            alert_payload = {
                "severity": anomaly_details.get("severity", "warning"),
                "title": anomaly_details.get("title", ""),
                "description": anomaly_details.get("description", ""),
                "recommendation": anomaly_details.get("recommendation", ""),
            }

        final_response = {
            "format": output_format,
            "data": raw_data,
            "chart_config": chart_config,
            "narrative": narrative,
            "alert": alert_payload,
            "disclaimer": None,
        }

    logger.info(
        "narrative_generator: final_response assembled",
        format=output_format,
        narrative_length=len(narrative),
        has_alert=anomaly_detected,
        has_chart=chart_config is not None,
    )

    return {
        "narrative": narrative,
        "final_response": final_response,
    }


async def _generate_narrative_llm(
    raw_data: list,
    output_format: str,
    intent: str,
    query: str,
    language: str,
    language_name: str,
    anomaly_detected: bool,
    anomaly_details: dict,
) -> str:
    """Call GPT-4o to generate an analytical narrative."""

    # ── Special case: alert narrative ──────────────────────────────────────
    if output_format == "alert" and anomaly_detected and anomaly_details:
        return await _generate_alert_narrative(
            anomaly_details, raw_data, language, language_name
        )

    # ── Standard narrative generation ─────────────────────────────────────
    columns = list(raw_data[0].keys()) if raw_data else []
    data_sample = raw_data[:_MAX_DATA_ROWS_FOR_PROMPT]
    data_summary = json.dumps(data_sample, ensure_ascii=False, default=str)

    format_instructions = FORMAT_INSTRUCTIONS.get(
        output_format,
        FORMAT_INSTRUCTIONS["direct_text"],
    )

    prompt = NARRATIVE_GENERATION_PROMPT.format(
        language_name=language_name,
        language_code=language,
        query=query,
        intent=intent,
        output_format=output_format,
        row_count=len(raw_data),
        columns=", ".join(columns),
        data_summary=data_summary,
        format_instructions=format_instructions,
    )

    try:
        response = await llm_primary.ainvoke(prompt)
        narrative = response.content if hasattr(response, "content") else str(response)
        narrative = narrative.strip()

        if not narrative:
            narrative = _fallback_narrative(raw_data, output_format, language)

    except Exception as exc:
        logger.error("narrative_generator: LLM call failed", error=str(exc))
        narrative = _fallback_narrative(raw_data, output_format, language)

    return narrative


async def _generate_alert_narrative(
    anomaly_details: dict,
    raw_data: list,
    language: str,
    language_name: str,
) -> str:
    """Generate a narrative specifically for anomaly alert cards."""
    data_sample = raw_data[:5]
    data_summary = json.dumps(data_sample, ensure_ascii=False, default=str)

    prompt = ALERT_NARRATIVE_PROMPT.format(
        language_name=language_name,
        language_code=language,
        anomaly_type=anomaly_details.get("type", "unknown"),
        severity=anomaly_details.get("severity", "warning"),
        title=anomaly_details.get("title", ""),
        description=anomaly_details.get("description", ""),
        recommendation=anomaly_details.get("recommendation", ""),
        data_summary=data_summary,
    )

    try:
        response = await llm_primary.ainvoke(prompt)
        narrative = response.content if hasattr(response, "content") else str(response)
        return narrative.strip()
    except Exception as exc:
        logger.error("narrative_generator: alert LLM call failed", error=str(exc))
        # Fallback: use the anomaly details directly
        return (
            f"{anomaly_details.get('title', '')}\n"
            f"{anomaly_details.get('description', '')}\n"
            f"{anomaly_details.get('recommendation', '')}"
        )


def _fallback_narrative(
    raw_data: list, output_format: str, language: str
) -> str:
    """Produce a safe fallback narrative when LLM fails."""
    row_count = len(raw_data)
    if language == "ar":
        return f"تم استرجاع {row_count} نتيجة. يُرجى مراجعة البيانات أدناه."
    return f"Retrieved {row_count} results. Please review the data below."

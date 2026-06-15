"""
M1 Intelligence Agent — LangGraph State Schema.

Blueprint reference: section 2.5 — LangGraph State Schema
Sprint 1 implementation.

All fields use total=False so nodes can return partial updates.
The API endpoint initializes all fields with defaults before graph invocation.
"""

from __future__ import annotations

from typing import Literal, TypedDict

IntentType = Literal[
    "financial_query",
    "operational_query",
    "invoice_analysis",
    "tax_reasoning",
    "clarification_needed",
]

OutputType = Literal[
    "direct_text",
    "metric_card",
    "table",
    "bar_chart",
    "line_chart",
    "narrative",
    "alert",
]


class M1State(TypedDict, total=False):
    """
    Complete state schema for the M1 Intelligence Agent LangGraph.

    Fields are grouped by pipeline stage:
    - Input: query, language
    - Classification: intent, intent_confidence, extracted_params
    - Data: raw_data, data_confidence
    - Output: output_format, narrative
    - Context: user_context
    - Final: final_response, error, needs_clarification, clarification_message
    """

    # ── Input ──────────────────────────────────────────────────────
    query: str                    # Original user query (AR or EN)
    language: Literal["ar", "en"] # auto-detect من النص

    # ── Intent Classification (Sprint 1) ──────────────────────────
    intent: IntentType            # financial_query | operational_query | invoice_analysis | tax_reasoning | clarification_needed
    intent_confidence: float      # 0.0 – 1.0 (kept for internal use/metrics)
    extracted_params: dict        # تاريخ، customer_id، فئة...

    # ── Data Retrieval (Sprint 2+) ────────────────────────────────
    raw_data: list                # النتائج الخام من DB أو RAG
    data_confidence: float        # 0.0 → 1.0

    # ── Output Formatting (Sprint 5) ──────────────────────────────
    output_format: OutputType     # direct_text | metric_card | table | bar_chart | line_chart | narrative | alert
    narrative: str                # التحليل اللغوي المُولَّد

    # ── Context ───────────────────────────────────────────────────
    user_context: dict            # اختياري — { user_id, role, permissions } من الـ JWT

    # ── Final Response ────────────────────────────────────────────
    final_response: dict          # { format, data, chart_config, narrative, alert, disclaimer? }
    error: str                    # Error message (empty = no error)
    needs_clarification: bool     # True → clarification flow was triggered
    clarification_message: str    # The clarification question for the user

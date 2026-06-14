"""
M1 Intelligence Agent — LangGraph State Schema.

Blueprint reference: section 2.5 — LangGraph State Schema
Sprint 1 implementation.

All fields use total=False so nodes can return partial updates.
The API endpoint initializes all fields with defaults before graph invocation.
"""

from __future__ import annotations

from typing import TypedDict


class M1State(TypedDict, total=False):
    """
    Complete state schema for the M1 Intelligence Agent LangGraph.

    Fields are grouped by pipeline stage:
    - Input: query, language
    - Classification: intent, intent_confidence, extracted_params
    - Data: raw_data, data_confidence
    - Output: output_format, narrative
    - Final: final_response, error, needs_clarification, clarification_message
    """

    # ── Input ──────────────────────────────────────────────────────
    query: str                    # Original user query (AR or EN)
    language: str                 # Detected or explicit: "ar" | "en"

    # ── Intent Classification (Sprint 1) ──────────────────────────
    intent: str                   # financial_query | operational_query |
                                  # invoice_analysis | tax_reasoning |
                                  # clarification_needed
    intent_confidence: float      # 0.0 – 1.0
    extracted_params: dict        # Dates, IDs, categories, limits, etc.

    # ── Data Retrieval (Sprint 2+) ────────────────────────────────
    raw_data: list                # Rows returned from DB / RAG
    data_confidence: float        # 0.0 – 1.0 completeness score

    # ── Output Formatting (Sprint 5) ──────────────────────────────
    output_format: str            # table | chart | text | metric_card |
                                  # alert_card | narrative | clarification
    narrative: str                # LLM-generated textual analysis

    # ── Final Response ────────────────────────────────────────────
    final_response: dict          # Complete response payload for API
    error: str                    # Error message (empty = no error)
    needs_clarification: bool     # True → clarification flow was triggered
    clarification_message: str    # The clarification question for the user

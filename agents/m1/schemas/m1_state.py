"""
M1 Intelligence Agent — LangGraph State Schema.

Blueprint reference: section 2.5 — LangGraph State Schema
Sprint 1 implementation.

All fields use total=False so nodes can return partial updates.
The API endpoint initializes all fields with defaults before graph invocation.
"""

from __future__ import annotations

from typing import Literal, TypedDict, Optional

from agents.m1.schemas.analysis_models import VisualizationHints

IntentType = Literal[
    "financial_query",
    "operational_query",
    "invoice_analysis",
    "tax_reasoning",
    "clarification_needed",
    "conversation",
    "out_of_scope",
    "support",
]

OutputType = Literal[
    "direct_text",
    "metric_card",
    "formatted_text_list",
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
    - Anomaly: anomaly_detected, anomaly_details
    - Output: output_format, narrative, chart_config
    - Context: user_context
    - Final: final_response, error, needs_clarification, clarification_message
    """

    # ── Input ──────────────────────────────────────────────────────
    query: str                    # Original user query (AR or EN)
    language: Literal["ar", "en"] # auto-detect من النص
    session_id: str               # UUID — يربط المحادثة بجدول conversations
    chat_history: list            # آخر N رسائل: [{role, content}] من conversations

    # ── Intent Classification (Sprint 1) ──────────────────────────
    intent: IntentType            # financial_query | operational_query | invoice_analysis | tax_reasoning | clarification_needed
    intent_confidence: float      # 0.0 – 1.0 (kept for internal use/metrics)
    extracted_params: dict        # تاريخ، customer_id، فئة...

    # ── Data Retrieval (Sprint 2+) ────────────────────────────────
    raw_data: list                # النتائج الخام من DB أو RAG
    data_confidence: float        # 0.0 → 1.0

    # ── Anomaly Detection (Sprint 5) ──────────────────────────────
    anomaly_detected: bool        # True → شذوذ مكتشف في البيانات
    anomaly_details: dict         # { type, severity, title, description, recommendation }

    # ── Output Formatting (Sprint 5) ──────────────────────────────
    output_format: OutputType     # direct_text | metric_card | formatted_text_list | table | bar_chart | line_chart | narrative | alert
    narrative: str                # التحليل اللغوي المُولَّد
    chart_config: Optional[dict]  # ECharts JSON config — None لو مفيش chart
    visualization_hints: Optional[VisualizationHints] # Advisory hints for how the data should be displayed

    # ── Context ───────────────────────────────────────────────────
    user_context: dict            # اختياري — { user_id, role, permissions } من الـ JWT

    # ── Final Response ────────────────────────────────────────────
    final_response: dict          # { format, data, chart_config, narrative, alert, disclaimer? }
    error: str                    # Error message (empty = no error)
    needs_clarification: bool     # True → clarification flow was triggered
    clarification_message: str    # The clarification question for the user

    # ── Stratified routing ────────────────────────────────────────────────
    assigned_tier: Literal["T0", "T1", "T2", "T3", "T4", "T5", "T6"]
    domain_intent: str
    router_confidence: float
    router_reasoning: str
    route_signals: list[str]

    # ── Structured analytical context ────────────────────────────────────
    analysis_frame: dict
    prior_analysis_frame: dict
    conversation_metadata: list[dict]
    context_metadata: dict
    prior_result_summary: dict

    # ── Query execution ──────────────────────────────────────────────────
    query_mode: Literal["template", "nl2sql", "none"]
    matched_template: str
    template_confidence: float
    pending_sql: str
    sql_parameters: dict
    sql_validation: dict
    sql_attempt: int
    db_execution_count: int
    query_artifacts: list[dict]

    # ── Result evaluation ────────────────────────────────────────────────
    result_status: Literal[
        "complete", "partial", "empty", "suspicious", "invalid", "failed"
    ]
    result_coverage: float
    result_evidence: list[str]
    result_gaps: list[str]
    result_needs_requery: bool
    result_format_hint: OutputType

    # ── Follow-up and bounded analytical execution ───────────────────────
    followup_mode: Literal[
        "reason_only", "refine", "drill_down", "compare", "requery", "summarize"
    ]
    react_plan: list[dict]
    react_iteration: int
    react_done: bool
    react_exit_reason: str
    tool_results: list[dict]

    # ── Clarification lifecycle and M3 delegation ────────────────────────
    clarification_pending: bool
    clarification_original_query: str
    clarification_missing_slots: list[str]
    clarification_question: str
    m3_delegation_payload: dict

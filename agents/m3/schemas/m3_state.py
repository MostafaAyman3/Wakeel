"""
M3 Customer Support Agent — LangGraph State Schema.

Blueprint reference: M3_Sprints.md Sprint 1 — LangGraph State Schema
"""

from __future__ import annotations

from typing import Literal, TypedDict

IssueType = Literal[
    "status_inquiry",
    "billing_dispute",
    "shipping_issue",
    "refund_request",
    "general_complaint",
]


class M3State(TypedDict, total=False):
    """Complete state schema for the M3 Customer Support LangGraph.

    Fields are grouped by pipeline stage:
    - Input: customer_identifier, issue_description, language
    - Classification: issue_type
    - Data: fetched_data, data_completeness, missing_fields
    - Response: draft_response, confidence_score
    - Gate: review_required, escalation_needed, rejection_context
    - Final: final_response
    """

    # ── Input ──────────────────────────────────────────────────
    customer_identifier: dict       # { type: order_id|invoice_id|customer_id, value: str }
    issue_description: str          # Free text from customer (AR or EN)
    language: Literal["ar", "en"]   # Auto-detected from input text

    # ── Issue Classification (Sprint 2) ───────────────────────
    issue_type: IssueType           # status_inquiry | billing_dispute | shipping_issue | refund_request | general_complaint
    issue_priority: Literal["High", "Medium", "Low"]  # Priority level
    context: dict                   # Structured LLM context (Sprint 2)

    # ── Data (Sprint 1) ───────────────────────────────────────
    fetched_data: dict              # { invoice, order, shipping, history }
    data_completeness: float        # 0.0 → 1.0
    missing_fields: list[str]       # Fields that couldn't be retrieved

    # ── Response (Sprint 3) ───────────────────────────────────
    draft_response: str             # Generated draft response
    confidence_score: float         # 0.0 → 1.0

    # ── Human Review Gate (Sprint 4) ──────────────────────────
    review_required: bool           # True → must be reviewed by human
    escalation_needed: bool         # True → route to supervisor
    rejection_context: dict | None  # { reason, feedback } for Reject & Regenerate

    # ── Final Output ──────────────────────────────────────────
    final_response: str             # Final approved response

    # ── Error handling ────────────────────────────────────────
    error: str                      # Error message (empty = no error)

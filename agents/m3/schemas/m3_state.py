"""
M3 Customer Support Agent — LangGraph State Schema.

Blueprint reference: section 3.4 — LangGraph State Schema

Design note — TypedDict vs Pydantic:
    The graph state is a ``TypedDict`` (total=False) to match the existing
    M1 graph and LangGraph's partial-update semantics — each node returns a
    plain ``dict`` with only the keys it changed, and LangGraph merges it.
    Pydantic is used at the API boundary instead (see backend api_models),
    which is where request/response validation actually matters.

All fields use total=False so nodes can return partial updates. The API
endpoint initializes every field with a safe default before invoking the graph.
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

IdentifierType = Literal["order_id", "invoice_id", "customer_id"]


class M3State(TypedDict, total=False):
    """Complete state schema for the M3 Customer Support Agent graph.

    Fields are grouped by pipeline stage. Sprint 1 populates the Input,
    Fetch, and Completeness groups; later sprints fill the rest.
    """

    # ── Input (Sprint 1 — InputParserNode) ────────────────────────
    customer_identifier: dict     # { "type": IdentifierType, "value": str }
    issue_description: str         # cleaned, natural-language problem statement
    language: Literal["ar", "en"]  # auto-detected from the customer's text

    # ── Classification (Sprint 2 — IssueClassifierNode) ───────────
    issue_type: IssueType | None   # None until Sprint 2
    issue_priority: Literal["High", "Medium", "Low"]  # Priority level
    context: dict                  # Structured LLM context (Sprint 2)

    # ── Data Retrieval (Sprint 1 — DataFetcherNode) ───────────────
    fetched_data: dict             # { invoice, order, shipping, history }
    data_completeness: float       # 0.0 -> 1.0
    missing_fields: list[str]      # source names that returned no data

    # ── Confidence (Sprint 1 = data_completeness; refined in Sprint 3) ─
    confidence_score: float        # 0.0 -> 1.0

    # ── Response Generation (Sprint 3 — ResponseGeneratorNode) ────
    draft_response: str            # empty until Sprint 3

    # ── Review & Escalation (Sprint 4 — HumanReviewGateNode) ──────
    review_required: bool          # gate logic lands in Sprint 4
    escalation_needed: bool        # set True here when no data is found
    rejection_context: dict | None # { reason, feedback } for Reject & Regenerate
    final_response: str            # empty until Sprint 4

    # ── Internal error channel (never raised to the client) ───────
    error: str


def build_initial_state(
    query: str,
    identifier: dict | None = None,
    language: str = "auto",
) -> M3State:
    """Create a fully-initialized M3State with safe defaults.

    Used by both the API endpoint and the integration tests so there is a
    single place that defines defaults.

    Args:
        query: Raw customer message (free-form, AR or EN).
        identifier: Optional pre-supplied ``{type, value}``. When provided it
            seeds the InputParser; when ``None`` the parser extracts it.
        language: ``"ar"``, ``"en"``, or ``"auto"`` (detected by the parser).

    Returns:
        A ready-to-invoke M3State.
    """
    return {
        "customer_identifier": identifier or {},
        "issue_description": query,
        "language": language,
        "issue_type": None,
        "issue_priority": "Medium",
        "context": {},
        "fetched_data": {},
        "data_completeness": 0.0,
        "missing_fields": [],
        "confidence_score": 0.0,
        "draft_response": "",
        "review_required": False,
        "escalation_needed": False,
        "rejection_context": None,
        "final_response": "",
        "error": "",
    }

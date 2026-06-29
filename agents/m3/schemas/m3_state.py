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

from typing import Literal, Optional, TypedDict

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

    # ── Intent Router (Unified Support — IntentRouterNode) ───────
    route: Literal["greeting", "general_knowledge", "customer_issue", "hybrid"]
    route_confidence: float         # 0.0 -> 1.0
    rag_collection: Literal["support_kb", "tax", "none"]  # which Mini-RAG collection

    # ── RAG (Unified Support — RagNode) ──────────────────────────
    rag_context: str                # answer text returned by Mini-RAG
    rag_sources: list[str]          # source document names from Mini-RAG

    # ── Conversation memory (Fix 3 — passed to the router for follow-ups) ─
    chat_history: list              # [{role, content}] prior turns (when session_id)

    # ── Input (Sprint 1 — InputParserNode) ────────────────────────
    customer_identifier: dict     # { "type": IdentifierType, "value": str }
    issue_description: str         # cleaned, natural-language problem statement
    language: Literal["ar", "en", "auto"]  # "auto" is the initial default before detection

    # ── Clarification (Feature 004 — ClarificationNode) ───────────
    clarification_needed: bool          # input_parser: a needed reference is missing
    clarification_pending: bool         # node: this turn is a follow-up QUESTION (not a final answer)
    missing_slot: Optional[str]         # "identifier" | "ambiguous_type" | None
    pending_value: Optional[str]        # raw value awaiting a type (ambiguous_type)
    clarification_attempts: int         # asks already made this conversation (from chat_history)

    # ── Invalid-ID Retry (Feature 006 — InvalidIdNode) ────────────
    invalid_id_attempts: int            # consecutive not-found count (derived from chat_history)
    invalid_id_pending: bool            # this turn is a retry message or escalation menu
    invalid_id_menu_shown: bool         # this turn is the 3-choice escalation menu
    alt_lookup_choice: Optional[str]    # phone/email value the customer provides for alt lookup

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
    escalation_summary: dict       # { identifier, issue_type, data_summary, escalation_reason }

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
        # Intent router defaults
        "route": "customer_issue",
        "route_confidence": 0.0,
        "rag_collection": "none",
        "rag_context": "",
        "rag_sources": [],
        # Input
        "customer_identifier": identifier or {},
        "issue_description": query,
        "language": language,
        # Clarification (Feature 004)
        "clarification_needed": False,
        "clarification_pending": False,
        "missing_slot": None,
        "pending_value": None,
        "clarification_attempts": 0,
        # Invalid-ID Retry (Feature 006)
        "invalid_id_attempts": 0,
        "invalid_id_pending": False,
        "invalid_id_menu_shown": False,
        "alt_lookup_choice": None,
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
        "escalation_summary": {},
        "error": "",
    }

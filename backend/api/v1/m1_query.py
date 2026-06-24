"""
M1 Intelligence Agent API router.

Endpoint: POST /api/v1/query
Accepts:  { query: str, language: "ar" | "en" | "auto", session_id?: str }
Returns:  QueryResponse — always JSON, never HTTP exceptions for agent errors.

Wired to ``m1_graph`` (LangGraph StateGraph) since Sprint 1.
Multi-turn context (Sprint 6+): uses the ``conversations`` table to persist
and retrieve conversation history per session.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.core.auth import UserContext, get_current_user
from backend.core.logging import get_logger

router = APIRouter(prefix="/query", tags=["M1 Intelligence"])
logger = get_logger(__name__)


# ── Request / Response schemas ───────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    language: str = Field(
        default="auto",
        pattern="^(ar|en|auto)$",
        description=(
            "Response language. 'auto' triggers auto-detection from "
            "the query text (Arabic Unicode range check)."
        ),
    )
    session_id: str | None = Field(
        default=None,
        description=(
            "Optional UUID to link this query to an ongoing conversation. "
            "If omitted, a new session is created automatically."
        ),
    )


class QueryResponse(BaseModel):
    format: str
    data: dict | list | str | None = None
    chart_config: dict | None = None
    narrative: str | None = None
    alert: dict | None = None
    disclaimer: str | None = None
    metadata: dict | None = None
    session_id: str | None = None  # Echo back so the frontend can persist it


# ── Endpoint ─────────────────────────────────────────────────────

@router.post("", response_model=QueryResponse)
async def handle_query(
    request: QueryRequest,
    user: UserContext = Depends(get_current_user),
) -> QueryResponse:
    """Process a natural language ERP query through the M1 agent graph.

    Multi-turn flow:
        1. Resolve (or create) a session_id.
        2. Load recent conversation history from ``conversations`` table.
        3. Invoke m1_graph with history injected into state.
        4. Save user message + agent response to ``conversations`` table.

    Error strategy (per user spec): agent errors are returned as
    ``QueryResponse(format="error", narrative="…")`` — never as HTTP
    exceptions. This keeps the frontend contract stable.
    """
    # ── Resolve session ───────────────────────────────────────────
    session_id: str = request.session_id or str(uuid.uuid4())

    logger.info(
        "query_received",
        user_id=user.user_id,
        language=request.language,
        query_length=len(request.query),
        session_id=session_id,
    )

    try:
        # Lazy imports — avoids circular imports and heavy LLM init at module-load time
        from agents.m1.graphs.m1_graph import m1_graph
        from backend.services.conversation_service import get_recent_messages, save_message

        # ── 1. Load conversation history ──────────────────────────
        chat_history = await get_recent_messages(session_id, limit=6)

        # ── 2. Build initial state ────────────────────────────────
        initial_state: dict = {
            "query": request.query,
            "language": request.language,          # "auto" → classifier detects
            "session_id": session_id,
            "chat_history": chat_history,
            "intent": "",
            "intent_confidence": 0.0,
            "extracted_params": {},
            "raw_data": [],
            "data_confidence": 0.0,
            "narrative": "",
            "final_response": {},
            "error": "",
            "needs_clarification": False,
            "clarification_message": "",
            "assigned_tier": "",
            "domain_intent": "",
            "router_confidence": 0.0,
            "router_reasoning": "",
            "route_signals": [],
            "analysis_frame": {},
            "prior_analysis_frame": {},
            "conversation_metadata": [],
            "context_metadata": {},
            "prior_result_summary": {},
            "query_mode": "none",
            "matched_template": "",
            "template_confidence": 0.0,
            "pending_sql": "",
            "sql_parameters": {},
            "sql_validation": {},
            "sql_attempt": 0,
            "db_execution_count": 0,
            "query_artifacts": [],
            "result_coverage": 0.0,
            "result_evidence": [],
            "result_gaps": [],
            "result_needs_requery": False,
            "react_plan": [],
            "react_iteration": 0,
            "react_done": False,
            "react_exit_reason": "",
            "tool_results": [],
            "clarification_pending": False,
            "clarification_original_query": "",
            "clarification_missing_slots": [],
            "clarification_question": "",
            "m3_delegation_payload": {},
            "user_context": {
                "user_id": user.user_id,
                "role": user.role,
                "permissions": user.permissions,
            },
        }

        # ── 3. Run the graph (with LangSmith tracing config) ────────
        result: dict = await m1_graph.ainvoke(
            initial_state,
            config={
                "run_name": "wakeel-m1-query",
                "metadata": {
                    "user_id": user.user_id,
                    "language": request.language,
                    "session_id": session_id,
                    "query_preview": request.query[:120],
                },
                "tags": ["m1", "query", request.language],
            },
        )

        # ── 4. Extract final response ─────────────────────────────
        final_response: dict = result.get("final_response", {})
        narrative: str = final_response.get("narrative", "")

        logger.info(
            "query_completed",
            user_id=user.user_id,
            intent=result.get("intent", "unknown"),
            confidence=result.get("intent_confidence", 0.0),
            response_format=final_response.get("format", "unknown"),
            session_id=session_id,
        )

        # ── 5. Persist conversation turns ─────────────────────────
        # Save user message
        await save_message(
            session_id=session_id,
            role="user",
            content=request.query,
            metadata={"language": request.language},
        )
        # Save agent response (save the narrative as the content for future context)
        assistant_metadata = {
            **result.get("context_metadata", {}),
            "intent": result.get("intent", ""),
            "format": final_response.get("format", ""),
        }
        await save_message(
            session_id=session_id,
            role="assistant",
            content=narrative,
            metadata=assistant_metadata,
        )

        # Extract alert_data_format for frontend rendering
        extracted_params = result.get("extracted_params", {})
        alert_data_format = extracted_params.get("alert_data_format")

        response_metadata: dict = {
            **(final_response.get("metadata") or {}),
            "assigned_tier": result.get("assigned_tier"),
            "domain_intent": result.get("domain_intent"),
            "result_status": result.get("result_status"),
        }
        if alert_data_format:
            response_metadata["alert_data_format"] = alert_data_format

        return QueryResponse(
            format=final_response.get("format", "direct_text"),
            data=final_response.get("data"),
            chart_config=final_response.get("chart_config"),
            narrative=narrative,
            alert=final_response.get("alert"),
            disclaimer=final_response.get("disclaimer"),
            metadata=response_metadata,
            session_id=session_id,
        )

    except Exception as exc:
        logger.error("query_failed", user_id=user.user_id, error=str(exc))

        # Determine language for error message
        lang = request.language
        if lang == "auto":
            lang = (
                "ar"
                if any("\u0600" <= c <= "\u06FF" for c in request.query)
                else "en"
            )

        error_narrative = (
            f"حدث خطأ أثناء معالجة الاستعلام: {exc}"
            if lang == "ar"
            else f"An error occurred while processing your query: {exc}"
        )

        return QueryResponse(
            format="error",
            narrative=error_narrative,
            session_id=session_id,
        )

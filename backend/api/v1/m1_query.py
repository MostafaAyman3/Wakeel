"""
M1 Intelligence Agent API router.

Endpoint: POST /api/v1/query
Accepts:  { query: str, language: "ar" | "en" | "auto" }
Returns:  QueryResponse — always JSON, never HTTP exceptions for agent errors.

Wired to ``m1_graph`` (LangGraph StateGraph) since Sprint 1.
"""

from __future__ import annotations

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


class QueryResponse(BaseModel):
    format: str
    data: dict | list | str | None = None
    chart_config: dict | None = None
    narrative: str | None = None
    alert: dict | None = None
    disclaimer: str | None = None
    metadata: dict | None = None


# ── Endpoint ─────────────────────────────────────────────────────

@router.post("", response_model=QueryResponse)
async def handle_query(
    request: QueryRequest,
    user: UserContext = Depends(get_current_user),
) -> QueryResponse:
    """Process a natural language ERP query through the M1 agent graph.

    Error strategy (per user spec): agent errors are returned as
    ``QueryResponse(format="error", narrative="…")`` — never as HTTP
    exceptions. This keeps the frontend contract stable.
    """
    logger.info(
        "query_received",
        user_id=user.user_id,
        language=request.language,
        query_length=len(request.query),
    )

    try:
        # Lazy import — avoids circular imports and heavy LLM init
        # at module-load time.
        from agents.m1.graphs.m1_graph import m1_graph

        # ── Build initial state with all defaults ─────────────
        initial_state: dict = {
            "query": request.query,
            "language": request.language,          # "auto" → classifier detects
            "intent": "",
            "intent_confidence": 0.0,
            "extracted_params": {},
            "raw_data": [],
            "data_confidence": 0.0,
            "output_format": "text",
            "narrative": "",
            "final_response": {},
            "error": "",
            "needs_clarification": False,
            "clarification_message": "",
        }

        # ── Run the graph ─────────────────────────────────────
        result: dict = await m1_graph.ainvoke(initial_state)

        # ── Extract final response ────────────────────────────
        final_response: dict = result.get("final_response", {})

        logger.info(
            "query_completed",
            user_id=user.user_id,
            intent=result.get("intent", "unknown"),
            confidence=result.get("intent_confidence", 0.0),
            response_format=final_response.get("format", "unknown"),
        )

        return QueryResponse(
            format=final_response.get("format", "text"),
            data=final_response.get("data"),
            chart_config=final_response.get("chart_config"),
            narrative=final_response.get("narrative"),
            alert=final_response.get("alert"),
            disclaimer=final_response.get("disclaimer"),
            metadata=final_response.get("metadata"),
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

        return QueryResponse(format="error", narrative=error_narrative)

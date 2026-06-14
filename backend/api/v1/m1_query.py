"""
M1 Intelligence Agent API router.

Endpoint: POST /api/v1/query
Accepts:  { query: str, language: "ar" | "en" }
Returns:  { format, data, chart_config, narrative, alert, disclaimer }

Sprint 1 will wire this to m1_graph.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.core.auth import UserContext, get_current_user
from backend.core.logging import get_logger

router = APIRouter(prefix="/query", tags=["M1 Intelligence"])
logger = get_logger(__name__)


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=2000)
    language: str = Field(default="ar", pattern="^(ar|en)$")


class QueryResponse(BaseModel):
    format: str
    data: dict | list | str | None = None
    chart_config: dict | None = None
    narrative: str | None = None
    alert: dict | None = None
    disclaimer: str | None = None


@router.post("", response_model=QueryResponse)
async def handle_query(
    request: QueryRequest,
    user: UserContext = Depends(get_current_user),
) -> QueryResponse:
    """
    Process a natural language ERP query.

    Sprint 1: Intent Classifier + Router
    Sprint 2: DB Query Tool (10 templates)
    Sprint 3: Invoice Analysis
    Sprint 4: Tax RAG
    Sprint 5: Output Selector + Narrative Generator
    """
    logger.info(
        "query_received",
        user_id=user.user_id,
        language=request.language,
        query_length=len(request.query),
    )

    # Placeholder until Sprint 1 wires m1_graph
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="M1 agent graph not yet wired. Implement Sprint 1.",
    )

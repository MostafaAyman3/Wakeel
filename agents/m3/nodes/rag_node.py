"""
RagNode — fetches knowledge-base context from the Mini-RAG microservice.

Picks the collection from state.rag_collection (set by IntentRouterNode),
calls rag_client.rag_answer, and writes rag_context + rag_sources.
Never raises — returns empty strings on failure so the graph continues.
"""

from __future__ import annotations

from agents.m3.schemas.m3_state import M3State
from backend.core.config import get_settings
from backend.services.rag_client import rag_answer
from backend.core.logging import get_logger

logger = get_logger(__name__)

_COLLECTION_TO_PROJECT_ID: dict[str, int] = {}


def _get_collection_map() -> dict[str, int]:
    if not _COLLECTION_TO_PROJECT_ID:
        s = get_settings()
        _COLLECTION_TO_PROJECT_ID["support_kb"] = s.rag_support_kb_project_id
        _COLLECTION_TO_PROJECT_ID["tax"] = s.rag_tax_project_id
    return _COLLECTION_TO_PROJECT_ID


async def run_rag(state: M3State) -> dict:
    """Query Mini-RAG and populate rag_context + rag_sources."""
    collection: str = state.get("rag_collection", "none") or "none"
    query: str = state.get("issue_description", "") or ""
    chat_history: list[dict] | None = state.get("chat_history")  # type: ignore[assignment]

    col_map = _get_collection_map()
    project_id: int | None = col_map.get(collection)

    if not project_id or not query:
        logger.info("rag_node_skipped", collection=collection, has_query=bool(query))
        return {"rag_context": "", "rag_sources": []}

    result = await rag_answer(
        query=query,
        project_id=project_id,
        chat_history=list(chat_history) if chat_history else None,
    )

    logger.info(
        "rag_node_done",
        collection=collection,
        project_id=project_id,
        ok=result["ok"],
        answer_length=len(result["answer"]),
    )

    return {
        "rag_context": result["answer"],
        "rag_sources": result["sources"],
    }

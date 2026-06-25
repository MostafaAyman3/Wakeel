"""
HTTP client for the Mini-RAG-APP-V1 microservice.

Calls POST {MINI_RAG_BASE_URL}/api/v1/nlp/index/answer/{project_id}
and normalises the response into { answer, sources, ok }.
"""

from __future__ import annotations

import httpx

from backend.core.config import get_settings
from backend.core.logging import get_logger

logger = get_logger(__name__)

_TIMEOUT_SECONDS = 30.0


async def rag_answer(
    query: str,
    project_id: int,
    chat_history: list[dict] | None = None,
) -> dict:
    """Call Mini-RAG /answer endpoint and return a normalised result.

    Returns:
        { "answer": str, "sources": list[str], "ok": bool }
        Never raises — on failure returns ok=False with an empty answer.
    """
    settings = get_settings()
    base_url = settings.mini_rag_base_url.rstrip("/")
    url = f"{base_url}/api/v1/nlp/index/answer/{project_id}"

    payload: dict = {"text": query}
    if chat_history:
        payload["chat_history"] = chat_history

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

        answer: str = data.get("answer", "") or ""
        raw_sources = data.get("sources", []) or []
        sources: list[str] = [
            s if isinstance(s, str) else str(s.get("document_name", s))
            for s in raw_sources
        ]

        logger.info(
            "rag_answer_ok",
            project_id=project_id,
            answer_length=len(answer),
            sources_count=len(sources),
        )
        return {"answer": answer, "sources": sources, "ok": True}

    except httpx.HTTPStatusError as exc:
        logger.warning(
            "rag_answer_http_error",
            project_id=project_id,
            status_code=exc.response.status_code,
        )
    except Exception as exc:
        logger.warning("rag_answer_failed", project_id=project_id, error=str(exc))

    return {"answer": "", "sources": [], "ok": False}

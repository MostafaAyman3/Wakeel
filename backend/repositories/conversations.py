"""
Conversation repository — load and persist multi-turn chat history.

Uses the existing `conversations` table (Migration 001).
Each turn is stored as two rows: role=user + role=assistant.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from backend.core.database import get_db_session
from backend.models.conversation import Conversation
from backend.core.logging import get_logger

logger = get_logger(__name__)

_MAX_HISTORY_TURNS = 10  # load at most the last N user+assistant pairs


async def load_conversation_history(session_id: str) -> list[dict]:
    """Return prior turns as [{"role": "user"|"assistant", "content": str}, ...].

    Memory isolation guarantee (Feature 005 FR-003 / SC-002): the query filters
    strictly on ``session_id``, so a fact stated in one conversation is never
    visible to another. Memory is scoped to a single session id.

    Returns an empty list on any error so callers are never blocked.
    """
    try:
        sid = uuid.UUID(session_id)
    except (ValueError, AttributeError):
        return []

    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(Conversation)
                .where(Conversation.session_id == sid)
                .order_by(Conversation.created_at.desc())
                .limit(_MAX_HISTORY_TURNS * 2)
            )
            rows = list(reversed(result.scalars().all()))

        return [
            {"role": r.role, "content": r.content, "metadata": r.metadata_ or {}}
            for r in rows
        ]

    except Exception as exc:
        logger.warning("load_conversation_history_failed", session_id=session_id, error=str(exc))
        return []


async def append_conversation_turn(
    session_id: str,
    user_message: str,
    assistant_message: str,
    assistant_metadata: dict | None = None,
) -> None:
    """Persist one user+assistant turn.  Silently swallows errors.

    ``assistant_metadata`` tags the assistant row (e.g. ``{"clarification": True}``)
    so later turns can count how many times the agent has asked for a reference
    (Feature 004 attempt limit).
    """
    try:
        sid = uuid.UUID(session_id)
    except (ValueError, AttributeError):
        return

    try:
        async with get_db_session() as db:
            db.add(Conversation(session_id=sid, role="user", content=user_message))
            db.add(Conversation(
                session_id=sid,
                role="assistant",
                content=assistant_message,
                metadata_=assistant_metadata or {},
            ))
            await db.flush()
    except Exception as exc:
        logger.warning("append_conversation_turn_failed", session_id=session_id, error=str(exc))

"""
ConversationService — read/write to the `conversations` table.

Used by m1_query.py to:
  1. Load recent messages before invoking the LangGraph graph
     (so the Intent Classifier has conversation context).
  2. Save the user message + agent response after graph execution.

Table schema (from db_schema_reference.md):
  conversations (
      id         uuid  PK  default gen_random_uuid()
      session_id uuid  NOT NULL
      role       varchar(20)  NOT NULL   -- 'user' | 'assistant'
      content    text         NOT NULL
      metadata   jsonb        default '{}'
      created_at timestamptz  default now()
  )

Indexes:
  idx_conversations_session  (session_id)
  idx_conversations_created  (session_id, created_at)
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from sqlalchemy import text

from backend.core.database import get_db_session

logger = structlog.get_logger(__name__)

# Maximum number of recent messages to load per request (3 Q&A pairs)
HISTORY_LIMIT = 6


async def get_recent_messages(session_id: str, limit: int = HISTORY_LIMIT) -> list[dict]:
    """Fetch the most recent messages for a session, ordered oldest-first.

    Returns a list of dicts: [{role, content}, ...] ready to be
    injected into the Intent Classifier's message history.

    Args:
        session_id: UUID string identifying the conversation session.
        limit:      Max number of messages to return (default 6).

    Returns:
        List of message dicts ordered chronologically (oldest first).
        Returns [] on error or if session is new.
    """
    try:
        async with get_db_session() as db:
            # Fetch the most recent `limit` rows for this session,
            # then reverse to chronological order for the LLM.
            result = await db.execute(
                text("""
                    SELECT role, content, metadata
                    FROM conversations
                    WHERE session_id = :session_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"session_id": session_id, "limit": limit},
            )
            rows = result.fetchall()

        # Reverse so oldest message is first (natural conversation order)
        messages = [
            {
                "role": row.role,
                "content": row.content,
                "metadata": row.metadata if isinstance(row.metadata, dict) else {},
            }
            for row in reversed(rows)
        ]
        logger.info(
            "conversation_service: loaded history",
            session_id=session_id,
            message_count=len(messages),
        )
        return messages

    except Exception as exc:
        logger.warning(
            "conversation_service: failed to load history — proceeding without context",
            session_id=session_id,
            error=str(exc),
        )
        return []


async def save_message(
    session_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Insert a single message into the conversations table.

    Args:
        session_id: UUID string identifying the conversation session.
        role:       'user' | 'assistant'
        content:    Text content of the message.
        metadata:   Optional dict stored as JSONB (e.g., intent, format).
    """
    if not content or not content.strip():
        return  # Don't save empty messages

    meta_json = json.dumps(metadata or {}, ensure_ascii=False, default=str)

    try:
        async with get_db_session() as db:
            await db.execute(
                text("""
                    INSERT INTO conversations (session_id, role, content, metadata)
                    VALUES (:session_id, :role, :content, CAST(:metadata AS jsonb))
                """),
                {
                    "session_id": session_id,
                    "role": role,
                    "content": content.strip(),
                    "metadata": meta_json,
                },
            )


        logger.info(
            "conversation_service: message saved",
            session_id=session_id,
            role=role,
            content_length=len(content),
        )

    except Exception as exc:
        # Non-fatal — saving history failure should not break the user response
        logger.error(
            "conversation_service: failed to save message",
            session_id=session_id,
            role=role,
            error=str(exc),
        )

"""
Singleton AsyncPostgresSaver for M2 LangGraph checkpoint persistence.

Uses psycopg3 (psycopg) + psycopg_pool — separate from the asyncpg pool used
by SQLAlchemy, because LangGraph's PostgresSaver is built on psycopg.

If psycopg is not installed, falls back to MemorySaver with a warning.
Install for production:
    pip install "psycopg[binary,pool]" langgraph-checkpoint-postgres

Connection URL: strips '+asyncpg' dialect prefix from settings.database_url.
Adds prepare_threshold=0 for Supabase pgBouncer transaction-mode compatibility.
"""

import logging
import re
from typing import Optional

from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_pool = None
_checkpointer = None


def _psycopg_conn_str() -> str:
    """Convert postgresql+asyncpg://... to postgresql://... for psycopg."""
    return re.sub(r"\+asyncpg", "", settings.database_url)


async def get_m2_checkpointer():
    """
    Return the singleton AsyncPostgresSaver, creating it on first call.

    Falls back to MemorySaver if psycopg / langgraph-checkpoint-postgres
    are not installed (development convenience — state won't survive restarts).
    """
    global _pool, _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    try:
        from psycopg_pool import AsyncConnectionPool
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        conn_str = _psycopg_conn_str()
        _pool = AsyncConnectionPool(
            conninfo=conn_str,
            kwargs={"prepare_threshold": 0},  # pgBouncer transaction-mode
            max_size=5,
            open=False,
        )
        await _pool.open()

        _checkpointer = AsyncPostgresSaver(_pool)
        await _checkpointer.setup()  # creates langgraph_checkpoints tables

        logger.info("m2_pg_checkpointer_ready")
        return _checkpointer

    except ImportError:
        logger.warning(
            "m2_checkpointer_fallback_to_memory",
            extra={"reason": "psycopg / langgraph-checkpoint-postgres not installed"},
        )
        from langgraph.checkpoint.memory import MemorySaver
        _checkpointer = MemorySaver()
        return _checkpointer


async def close_m2_checkpointer() -> None:
    """Close the psycopg pool on application shutdown."""
    global _pool, _checkpointer
    if _pool is not None:
        await _pool.close()
        logger.info("m2_checkpointer_pool_closed")
    _pool = None
    _checkpointer = None

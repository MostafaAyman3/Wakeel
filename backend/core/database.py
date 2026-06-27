"""
SQLAlchemy async connection pool for PostgreSQL (Supabase).

Two engines are exposed:
- engine        : read-write, used by backend services and M3 agent
- readonly_engine: SELECT-only user (erp_readonly), used exclusively by M1 agent

Usage:
    async with get_db_session() as session:
        result = await session.execute(...)

    async with get_readonly_session() as session:
        result = await session.execute(...)
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.core.config import get_settings

settings = get_settings()

# asyncpg connection args — statement_cache_size=0 required for Supabase pgBouncer
# (transaction mode doesn't support named prepared statements)
_CONNECT_ARGS = {"statement_cache_size": 0, "command_timeout": 60}

# Read-write engine — used by backend services and M3
engine = create_async_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.app_env == "development",
    connect_args=_CONNECT_ARGS,
)

# Read-only engine — used exclusively by M1 agent queries
readonly_engine = create_async_engine(
    settings.readonly_db_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,
    connect_args=_CONNECT_ARGS,
)

AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

ReadonlyAsyncSessionFactory = async_sessionmaker(
    bind=readonly_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Read-write session context manager — use with `async with get_db_session() as session`."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_readonly_session() -> AsyncGenerator[AsyncSession, None]:
    """Read-only session context manager — M1 agent MUST use this exclusively."""
    async with ReadonlyAsyncSessionFactory() as session:
        yield session


async def get_db_session_dep() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Depends()-compatible read-write session.

    Use ONLY in FastAPI endpoint signatures:
        async def my_endpoint(session: AsyncSession = Depends(get_db_session_dep))

    For all other code (agent nodes, services, scripts) use the context manager:
        async with get_db_session() as session: ...

    The @asynccontextmanager version above cannot be used with Depends() because
    Depends() needs a plain async generator, not a context manager object.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_readonly_session_dep() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Depends()-compatible read-only session (M1 agent endpoints)."""
    async with ReadonlyAsyncSessionFactory() as session:
        yield session

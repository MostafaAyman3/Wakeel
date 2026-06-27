"""
Shared pytest configuration for all test suites.

The core problem this file solves:
  SQLAlchemy's async connection pool holds connections bound to event loop A.
  When anyio closes loop A after the first test and opens loop B for the second,
  pool_pre_ping tries to reuse those connections — but they're attached to the
  closed loop, causing "RuntimeError: Event loop is closed".

Fix: replace the SQLAlchemy engines with NullPool engines before the app is
imported.  NullPool creates a fresh connection for each use and closes it
immediately — no pooling, no cross-loop reuse, no pre-ping needed.

LangSmith tracing is disabled for tests to prevent background threads from
writing to pytest's already-closed log streams (ValueError: I/O on closed file).
"""

import os

# Disable LangSmith before any LangChain/LangGraph import.
# This stops background tracing threads that cause "I/O on closed file" at exit.
os.environ["LANGCHAIN_TRACING_V2"] = "false"

import pytest
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from backend.core.config import get_settings

settings = get_settings()

_CONNECT_ARGS = {"statement_cache_size": 0, "command_timeout": 60}

# NullPool engines — created once, shared for the whole test session.
# NullPool = no pooling: each checkout opens a new connection and each
# checkin closes it, so there are never stale connections across event loops.
_test_engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool,
    echo=False,
    connect_args=_CONNECT_ARGS,
)

_test_readonly_engine = create_async_engine(
    settings.readonly_db_url,
    poolclass=NullPool,
    echo=False,
    connect_args=_CONNECT_ARGS,
)

_TestSessionFactory = async_sessionmaker(
    bind=_test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

_TestReadonlySessionFactory = async_sessionmaker(
    bind=_test_readonly_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ── Patch the live engines for the entire test session ─────────────
# This runs before any test module is collected, ensuring all imports
# of `backend.core.database` see the NullPool engines.

@pytest.fixture(autouse=True, scope="session")
def patch_db_engines():
    """Replace SQLAlchemy pooled engines with NullPool versions for all tests."""
    import backend.core.database as db_module

    with (
        patch.object(db_module, "engine", _test_engine),
        patch.object(db_module, "readonly_engine", _test_readonly_engine),
        patch.object(db_module, "AsyncSessionFactory", _TestSessionFactory),
        patch.object(db_module, "ReadonlyAsyncSessionFactory", _TestReadonlySessionFactory),
    ):
        yield


# ── anyio backend ──────────────────────────────────────────────────
@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio for all anyio-marked async tests."""
    return "asyncio"

"""
AERIE FastAPI application entry point.

Wires together:
- Error handling middleware
- Structured logging
- API routers (M1, M3)
- Health check endpoint

All shared services (DB pool, LLM client) are imported lazily
on first use — no heavy initialization at import time.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import get_settings
from backend.core.database import engine, readonly_engine
from backend.core.logging import configure_logging, get_logger
from backend.middleware.error_handler import error_handler_middleware
from backend.api.v1.m1_query import router as m1_router
from backend.api.v1.m2_inventory import router as m2_inventory_router
from backend.api.v1.m2_analyze import router as m2_analyze_router
from backend.api.v1.m3_support import router as m3_router

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle."""
    logger.info(
        "application_starting",
        name=settings.app_name,
        version=settings.app_version,
        env=settings.app_env,
    )

    # ── Log LangSmith tracing status ─────────────────────────────
    import os
    tracing_on = os.environ.get("LANGCHAIN_TRACING_V2", "").lower() == "true"
    ls_project = os.environ.get("LANGCHAIN_PROJECT", "default")
    ls_key_set = bool(os.environ.get("LANGCHAIN_API_KEY", ""))
    if tracing_on and ls_key_set:
        logger.info(
            "langsmith_tracing_enabled",
            project=ls_project,
            endpoint=os.environ.get("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"),
        )
    else:
        logger.warning(
            "langsmith_tracing_disabled",
            tracing_v2=tracing_on,
            api_key_set=ls_key_set,
        )

    yield
    # Gracefully close all DB pool connections on shutdown
    await engine.dispose()
    await readonly_engine.dispose()
    logger.info("application_shutdown_complete")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="ERP Agentic AI Platform — M1 Intelligence + M3 Customer Support",
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url="/redoc" if settings.app_env == "development" else None,
    lifespan=lifespan,
)

# Error handling middleware — must be added first (outermost layer)
app.middleware("http")(error_handler_middleware)

# CORS — restrict to frontend origin in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_base_url],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

# API routers
app.include_router(m1_router, prefix="/api/v1")
app.include_router(m2_inventory_router, prefix="/api/v1")
app.include_router(m2_analyze_router, prefix="/api/v1")
app.include_router(m3_router, prefix="/api/v1")


@app.get("/health", tags=["Infrastructure"])
async def health_check() -> dict[str, str]:
    """Liveness probe endpoint."""
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "env": settings.app_env,
    }

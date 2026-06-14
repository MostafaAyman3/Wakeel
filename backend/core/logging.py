"""
Structured logging configuration using structlog.

All agent nodes, LLM calls, tool executions, and user actions
are logged through this module. Import `get_logger` everywhere.

Usage:
    from backend.core.logging import get_logger

    logger = get_logger(__name__)
    logger.info("intent_classified", intent="financial_query", query_id="abc123")
    logger.error("db_query_failed", error=str(e), table="invoices")
"""

import logging
import sys

import structlog
from structlog.types import EventDict, WrappedLogger

from backend.core.config import get_settings

settings = get_settings()


def _add_app_context(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Inject app name and environment into every log record."""
    event_dict["app"] = settings.app_name
    event_dict["env"] = settings.app_env
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog and stdlib logging.
    Call once at application startup from main.py.
    """
    log_level = logging.DEBUG if settings.app_env == "development" else logging.INFO

    # Configure stdlib logging (used by SQLAlchemy, uvicorn, etc.)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Shared processors for both development and production
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_app_context,
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.app_env == "development":
        # Human-readable colored output for local development
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # JSON output for production log aggregation
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    # Suppress noisy third-party loggers in production
    if settings.app_env != "development":
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for the given module name."""
    return structlog.get_logger(name)

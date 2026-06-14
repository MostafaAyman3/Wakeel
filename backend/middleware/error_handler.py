"""
Global error handling middleware for FastAPI.

Converts all unhandled exceptions into structured JSON responses
with a user-friendly message and a unique request_id for tracing.

Error format:
    {
        "error": "short_error_code",
        "message": "Human-readable description.",
        "request_id": "uuid"
    }
"""

import uuid
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.core.logging import get_logger

logger = get_logger(__name__)


def _error_response(
    status_code: int,
    error: str,
    message: str,
    request_id: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "message": message,
            "request_id": request_id,
        },
    )


async def error_handler_middleware(request: Request, call_next: Callable) -> Response:
    """
    Catch-all middleware — must be added first in main.py so it wraps
    all other middleware and route handlers.

    Handles:
    - SQLAlchemy database errors
    - ValueError / TypeError (bad input from agent nodes)
    - Generic unhandled exceptions
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    try:
        response = await call_next(request)
        return response

    except SQLAlchemyError as exc:
        logger.error(
            "database_error",
            request_id=request_id,
            path=request.url.path,
            error=str(exc),
        )
        return _error_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error="database_error",
            message="A database error occurred. Please try again later.",
            request_id=request_id,
        )

    except ValueError as exc:
        logger.warning(
            "validation_error",
            request_id=request_id,
            path=request.url.path,
            error=str(exc),
        )
        return _error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error="validation_error",
            message=str(exc),
            request_id=request_id,
        )

    except Exception as exc:
        logger.exception(
            "unhandled_error",
            request_id=request_id,
            path=request.url.path,
            error=str(exc),
        )
        return _error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="internal_error",
            message="An unexpected error occurred. Our team has been notified.",
            request_id=request_id,
        )

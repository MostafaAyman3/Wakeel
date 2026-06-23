"""Central, validated, read-only SQL execution gateway for M1."""

from __future__ import annotations

import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

import structlog
from sqlalchemy import text

from agents.m1.config.constants import (
    CONTEXT_RESULT_SAMPLE_ROWS,
    QUERY_HARD_LIMIT,
    QUERY_TIMEOUT_MS,
)
from agents.m1.schemas.analysis_models import QueryArtifact
from agents.m1.tools.sql_policy import (
    SQLPolicyOptions,
    classify_database_error,
    validate_sql,
)
from backend.core.config import get_settings
from backend.core.database import get_readonly_session

logger = structlog.get_logger(__name__)
settings = get_settings()


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _serialize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {key: _serialize_value(value) for key, value in row.items()}
        for row in rows
    ]


def _bounded_sql(sql: str, limit: int) -> str:
    cleaned = sql.strip().rstrip(";")
    return f"SELECT * FROM ({cleaned}) AS _wakeel_query LIMIT {limit}"


async def execute_readonly_query(
    *,
    sql: str,
    parameters: dict[str, Any] | None = None,
    source: Literal["template", "nl2sql"],
    purpose: str,
    allow_star: bool = False,
    hard_limit: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate and execute SQL, returning rows and a serializable artifact."""
    validation = validate_sql(
        sql,
        options=SQLPolicyOptions(allow_star=allow_star),
    )
    params = parameters or {}
    limit = min(
        max(1, hard_limit or settings.m1_query_hard_limit or QUERY_HARD_LIMIT),
        QUERY_HARD_LIMIT,
    )

    if not validation.is_valid:
        artifact = QueryArtifact(
            source=source,
            purpose=purpose,
            sql_fingerprint=validation.sql_fingerprint,
            parameters=params,
            referenced_tables=validation.tables,
            referenced_columns=validation.columns,
            validation=validation.model_dump(),
            execution_status="blocked",
            error_category=validation.error_category,
            error_message=validation.message,
        )
        return [], artifact.model_dump()

    started = time.perf_counter()
    try:
        timeout_ms = min(
            max(1000, settings.m1_query_timeout_ms or QUERY_TIMEOUT_MS),
            QUERY_TIMEOUT_MS,
        )
        async with get_readonly_session() as session:
            await session.execute(text(f"SET LOCAL statement_timeout = {timeout_ms}"))
            result = await session.execute(
                # Execute the original SQL so SQLAlchemy ``:name`` bind
                # parameters are preserved. The normalized SQL is for tracing.
                text(_bounded_sql(sql, limit)),
                params,
            )
            raw_rows = [dict(row) for row in result.mappings().fetchall()]
        rows = _serialize_rows(raw_rows)
        duration_ms = (time.perf_counter() - started) * 1000
        artifact = QueryArtifact(
            source=source,
            purpose=purpose,
            sql_fingerprint=validation.sql_fingerprint,
            parameters=params,
            referenced_tables=validation.tables,
            referenced_columns=validation.columns,
            validation=validation.model_dump(),
            execution_status="success",
            row_count=len(rows),
            duration_ms=round(duration_ms, 2),
            result_sample=rows[:CONTEXT_RESULT_SAMPLE_ROWS],
        )
        logger.info(
            "m1_query_gateway_success",
            source=source,
            purpose=purpose,
            fingerprint=validation.sql_fingerprint,
            tables=validation.tables,
            row_count=len(rows),
            duration_ms=round(duration_ms, 2),
        )
        return rows, artifact.model_dump()
    except Exception as exc:
        duration_ms = (time.perf_counter() - started) * 1000
        category, message = classify_database_error(exc)
        artifact = QueryArtifact(
            source=source,
            purpose=purpose,
            sql_fingerprint=validation.sql_fingerprint,
            parameters=params,
            referenced_tables=validation.tables,
            referenced_columns=validation.columns,
            validation=validation.model_dump(),
            execution_status="failed",
            duration_ms=round(duration_ms, 2),
            error_category=category,
            error_message=message,
        )
        logger.warning(
            "m1_query_gateway_failed",
            source=source,
            purpose=purpose,
            fingerprint=validation.sql_fingerprint,
            category=category,
            duration_ms=round(duration_ms, 2),
        )
        return [], artifact.model_dump()

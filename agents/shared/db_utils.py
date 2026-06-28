"""
Shared database helpers used by agent tools.

Currently exposes ``jsonify_row`` — converts a SQLAlchemy RowMapping (or any
dict-like row from asyncpg) into a pure, JSON-serializable ``dict`` by
normalizing non-JSON-native types (datetime, date, Decimal, UUID).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Mapping
from uuid import UUID


def _coerce(value: Any) -> Any:
    """Convert a single DB value into a JSON-serializable primitive."""
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    return value


def jsonify_row(row: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Return a JSON-safe ``dict`` for a single DB row, or ``None``.

    Args:
        row: A SQLAlchemy ``RowMapping`` / dict-like row, or ``None``.

    Returns:
        A plain dict with serializable values, or ``None`` if ``row`` is None.
    """
    if row is None:
        return None
    return {key: _coerce(val) for key, val in dict(row).items()}


def jsonify_rows(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return a list of JSON-safe dicts for multiple DB rows."""
    return [jsonify_row(r) for r in rows if r is not None]  # type: ignore[misc]

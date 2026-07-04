"""Numeric coercion and visualization-hint normalization shared by M1 nodes.

LLM-generated SQL and LLM-formatted payloads produce values in inconsistent
shapes: Decimal from DB drivers, formatted strings ("1,783,555"), plain
numbers, or non-numeric labels ("Q1"). Every node that needs "is this a
number?" must go through to_float so the answer is consistent pipeline-wide.
"""

from __future__ import annotations

from typing import Any

from agents.m1.schemas.analysis_models import VisualizationHints


def to_float(val: Any) -> float | None:
    """Best-effort numeric conversion.

    Handles int/float/Decimal and formatted numeric strings ("1,783,555").
    Returns None for anything non-numeric ("Q1", None, bool) instead of raising.
    """
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.replace(",", "").replace("٬", "").strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    try:
        return float(val)  # Decimal from DB drivers
    except (TypeError, ValueError):
        return None


def is_numeric_column(rows: list[dict], column: str) -> bool:
    """A column is numeric only if every non-null value coerces to a number."""
    non_null = [row.get(column) for row in rows if row.get(column) is not None]
    return bool(non_null) and all(to_float(v) is not None for v in non_null)


def coerce_hints(value: Any) -> VisualizationHints | None:
    """Normalize state['visualization_hints'] — nodes may store a pydantic
    model, a dict (after checkpoint round-trip), or None."""
    if value is None:
        return None
    if isinstance(value, VisualizationHints):
        return value
    if isinstance(value, dict):
        try:
            return VisualizationHints(**value)
        except Exception:
            return None
    return None

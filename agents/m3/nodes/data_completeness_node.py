"""
DataCompletenessCheckNode — scores data completeness and sets escalation flags.

Rules:
  - All 4 data sources found → data_completeness = 1.0
  - Some found             → data_completeness = 0.5 + flag missing_fields
  - None found             → escalation_needed = True

Blueprint reference: M3_Sprints.md Sprint 1 — DataCompletenessCheckNode
"""

from __future__ import annotations

import structlog

from agents.m3.schemas.m3_state import M3State

logger = structlog.get_logger(__name__)

# The 4 expected data source keys in fetched_data
DATA_SOURCES = ["invoice", "order", "shipping", "history"]


async def check_data_completeness(state: M3State) -> dict:
    """Evaluate completeness of fetched data and set flags."""
    fetched_data: dict = state.get("fetched_data", {})
    missing_fields: list[str] = []

    for source in DATA_SOURCES:
        value = fetched_data.get(source)
        if value is None or (isinstance(value, list) and len(value) == 0):
            missing_fields.append(source)

    total = len(DATA_SOURCES)
    found = total - len(missing_fields)

    if found == total:
        data_completeness = 1.0
        escalation_needed = False
    elif found == 0:
        data_completeness = 0.0
        escalation_needed = True
    else:
        data_completeness = round(found / total, 1)
        escalation_needed = False

    return {
        "data_completeness": data_completeness,
        "missing_fields": missing_fields,
        "escalation_needed": escalation_needed,
    }

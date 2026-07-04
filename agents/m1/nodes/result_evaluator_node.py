"""Evaluate whether retrieved data actually answers the analytical request."""

from __future__ import annotations

from numbers import Number
from typing import Any

from agents.m1.schemas.analysis_models import ResultEvaluation
from agents.m1.schemas.m1_state import M1State

_COMPARISON_SIGNALS = (
    "compare", "comparison", "vs", "growth", "change",
    "قارن", "مقارنة", "مقارنه", "الفرق", "نمو", "نسبة التغير",
)


def _format_hint(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "narrative"
    columns = list(rows[0])
    if len(rows) == 1 and len(columns) == 1:
        return "metric_card"
    time_columns = {
        "date", "period", "month", "quarter", "year", "week",
        "invoice_date", "order_date", "transaction_date",
    }
    if len(rows) == 2 and len(columns) >= 2:
        # A two-row result is a pairwise comparison — bars, not a 2-point line
        return "bar_chart"
    if len(rows) >= 3 and any(column.lower() in time_columns for column in columns):
        return "line_chart"
    if len(rows) <= 12 and len(columns) == 2:
        return "bar_chart"
    if len(rows) <= 5 and len(columns) <= 3:
        return "formatted_text_list"
    return "table"


def evaluate_result(state: M1State) -> ResultEvaluation:
    rows = state.get("raw_data", [])
    if state.get("error") and not rows:
        return ResultEvaluation(
            status="failed",
            coverage=0.0,
            gaps=[state["error"]],
            format_hint="narrative",
        )
    if not rows:
        return ResultEvaluation(
            status="empty",
            coverage=0.0,
            gaps=["No rows matched the resolved filters."],
            format_hint="narrative",
        )

    columns = set(rows[0])
    evidence = [
        f"Retrieved {len(rows)} row(s).",
        f"Columns: {', '.join(sorted(columns))}.",
    ]
    gaps: list[str] = []
    query = state.get("query", "").lower()
    frame = state.get("analysis_frame", {})

    comparison_requested = bool(frame.get("comparison_range")) or any(
        signal in query for signal in _COMPARISON_SIGNALS
    )
    if comparison_requested:
        comparison_columns = [
            key
            for key in ("period", "comparison_period", "month", "quarter", "year")
            if key in columns
        ]
        distinct_groups = {
            tuple(str(row.get(key)) for key in comparison_columns)
            for row in rows
        }
        if not comparison_columns or len(distinct_groups) < 2:
            gaps.append("The comparison does not contain two distinguishable groups.")

    expected_dimensions = set(frame.get("dimensions", []))
    missing_dimensions = {
        dimension for dimension in expected_dimensions if dimension not in columns
    }
    if missing_dimensions:
        gaps.append(
            "Missing requested dimensions: "
            + ", ".join(sorted(missing_dimensions))
        )

    numeric_values = [
        value
        for row in rows
        for value in row.values()
        if isinstance(value, Number) and not isinstance(value, bool)
    ]
    if numeric_values and all(value == 0 for value in numeric_values):
        return ResultEvaluation(
            status="suspicious",
            coverage=0.4,
            evidence=evidence,
            gaps=["All returned numeric values are zero."],
            format_hint="narrative",
        )

    if gaps:
        return ResultEvaluation(
            status="partial",
            coverage=0.6,
            evidence=evidence,
            gaps=gaps,
            needs_requery=True,
            format_hint=_format_hint(rows),
        )

    return ResultEvaluation(
        status="complete",
        coverage=1.0,
        evidence=evidence,
        format_hint=_format_hint(rows),
    )


async def result_evaluator_node(state: M1State) -> dict:
    evaluation = evaluate_result(state)
    return {
        "result_status": evaluation.status,
        "result_coverage": evaluation.coverage,
        "result_evidence": evaluation.evidence,
        "result_gaps": evaluation.gaps,
        "result_needs_requery": evaluation.needs_requery,
        "result_format_hint": evaluation.format_hint,
    }

"""
OutputSelectorNode — Sprint 5.

Determines the best output format based on TWO factors:
    1. User intent (from intent classifier)
    2. Actual data shape (from the tool node)

Blueprint reference: section 2.8 — Adaptive Output Selector
Sprint plan: M1_Sprints.md Sprint 5

8 output types:
    direct_text         — single scalar value (1 row, 1 col)
    metric_card         — KPI number with comparison context
    formatted_text_list — small list (1-5 rows, ≤ 3 cols)
    table               — large dataset (> 5 rows or > 12 categorical items)
    bar_chart           — categorical comparison (≤ 12 items)
    line_chart          — time series data
    narrative           — explanation / analysis / tax reasoning
    alert               — anomaly detected → colored alert card
"""

from __future__ import annotations


import structlog

from agents.m1.schemas.m1_state import M1State

logger = structlog.get_logger(__name__)

# ── Template-specific output hints ────────────────────────────────────────────
# These override the generic heuristic when matched.
_TEMPLATE_OUTPUT_HINTS: dict[str, str] = {
    "T2":  "line_chart",       # sales_time_series
    "T3":  "metric_card",      # executive_summary
    "T6":  "alert",            # expense_anomaly
    "T8":  "bar_chart",        # category_revenue
}

# Column name patterns that indicate a time dimension
_TIME_COLUMN_PATTERNS: frozenset[str] = frozenset({
    "date", "period", "month", "year", "quarter", "week", "day",
    "invoice_date", "order_date", "transaction_date", "payment_date",
    "shipped_date", "delivered_date", "created_at",
})


def _has_time_column(columns: list[str]) -> bool:
    """Check if any column name matches a known time pattern."""
    return any(
        col.lower() in _TIME_COLUMN_PATTERNS
        or col.lower().endswith("_date")
        or col.lower().endswith("_at")
        for col in columns
    )


def _is_categorical(columns: list[str], raw_data: list[dict]) -> bool:
    """
    Determine if the data is categorical (suitable for Bar Chart).

    Categorical means:
        - Exactly 2 columns (label + value)
        - No time column present
        - First column values are strings (category labels)
    """
    if len(columns) != 2:
        return False

    if _has_time_column(columns):
        return False

    # Check that the first column (label) contains string values
    if raw_data:
        first_col = columns[0]
        sample_value = raw_data[0].get(first_col)
        if not isinstance(sample_value, str):
            return False

    return True


def _build_chart_config(
    output_format: str,
    columns: list[str],
    raw_data: list[dict],
    language: str,
) -> dict | None:
    """
    Build a framework-agnostic chart configuration.

    Sprint 6 will convert this to ECharts-specific options.
    Returns None for non-chart output types.
    """
    if output_format not in ("bar_chart", "line_chart"):
        return None

    if not columns or len(columns) < 2:
        return None

    x_field = columns[0]
    y_field = columns[1]

    # If there are more than 2 columns, try to find a numeric value column
    if len(columns) > 2:
        for col in columns[1:]:
            sample_val = raw_data[0].get(col) if raw_data else None
            if isinstance(sample_val, (int, float)):
                y_field = col
                break

    chart_type = "line" if output_format == "line_chart" else "bar"

    # Build series from data
    series_data = []
    for row in raw_data:
        series_data.append({
            "x": row.get(x_field),
            "y": row.get(y_field),
        })

    config = {
        "chart_type": chart_type,
        "x_axis": {
            "field": x_field,
            "label": x_field.replace("_", " ").title(),
        },
        "y_axis": {
            "field": y_field,
            "label": y_field.replace("_", " ").title(),
        },
        "title": "",  # Will be filled by narrative_generator
        "series": [{
            "name": y_field.replace("_", " ").title(),
            "data": series_data,
        }],
    }

    return config


async def select_output(state: M1State) -> dict:
    """
    OutputSelectorNode: determine the best output format for the response.

    Guard Clause: If output_format was already set by an upstream node
    (e.g. tax_rag_node sets "narrative", invoice_analysis_tool may set a format),
    preserve that decision and only build chart_config if needed.

    Args:
        state: Current M1State with raw_data, intent, extracted_params, etc.

    Returns:
        Partial M1State dict: { output_format, chart_config }
    """
    # ── Guard Clause: preserve upstream output_format ──────────────────────
    existing_format = state.get("output_format")
    if existing_format:
        logger.info(
            "output_selector: preserving upstream output_format",
            format=existing_format,
        )
        # Still build chart_config if needed for preserved chart formats
        raw_data = state.get("raw_data", [])
        columns = list(raw_data[0].keys()) if raw_data else []
        language = state.get("language", "en")
        chart_config = _build_chart_config(existing_format, columns, raw_data, language)
        return {
            "output_format": existing_format,
            "chart_config": chart_config,
        }

    # ── Main selection logic ──────────────────────────────────────────────
    raw_data: list = state.get("raw_data", [])
    intent: str = state.get("intent", "")
    language: str = state.get("language", "en")
    extracted_params: dict = state.get("extracted_params", {})
    anomaly_detected: bool = state.get("anomaly_detected", False)
    evaluator_hint: str = state.get("result_format_hint", "")

    row_count = len(raw_data)
    columns = list(raw_data[0].keys()) if raw_data else []
    col_count = len(columns)
    has_time = _has_time_column(columns)
    categorical = _is_categorical(columns, raw_data)

    # Check template-specific hints first
    template_id = extracted_params.get("applied_template", "")
    hint = _TEMPLATE_OUTPUT_HINTS.get(template_id)

    # ── Decision tree (Blueprint 2.8 — 8 scenarios) ──────────────────────

    # 1. Alert Card — anomaly detected (highest priority)
    if anomaly_detected:
        selected = "alert"

    # 2. Template-specific hint (if available and not overridden by anomaly)
    elif hint:
        selected = hint

    elif evaluator_hint:
        selected = evaluator_hint

    # 3. Narrative — tax or explanation intent (no chart needed)
    elif intent == "tax_reasoning":
        selected = "narrative"

    # 4. Empty data — fallback to direct_text
    elif row_count == 0:
        selected = "direct_text"

    # 5. Direct Text — single scalar value (1 row, 1 col)
    elif row_count == 1 and col_count == 1:
        selected = "direct_text"

    # 6. Metric Card — single row with context (1 row, ≤ 3 cols)
    elif row_count == 1 and col_count <= 3:
        selected = "metric_card"

    # 7. Line Chart — time series data
    elif has_time and row_count > 1:
        selected = "line_chart"

    # 8. Bar Chart — categorical comparison (≤ 12 items)
    elif categorical and row_count <= 12:
        selected = "bar_chart"

    # 9. Formatted Text List — small list (1-5 rows, ≤ 3 cols)
    elif 1 <= row_count <= 5 and col_count <= 3:
        selected = "formatted_text_list"

    # 10. Sortable Table — large dataset (> 5 rows) or non-categorical > 12
    elif row_count > 5:
        selected = "table"

    # 11. Narrative — analysis/explanation intent
    elif intent == "invoice_analysis":
        selected = "narrative"

    # 12. Fallback
    else:
        selected = "direct_text"

    # ── Build chart_config for chart types ─────────────────────────────────
    chart_config = _build_chart_config(selected, columns, raw_data, language)

    logger.info(
        "output_selector: format selected",
        format=selected,
        row_count=row_count,
        col_count=col_count,
        has_time=has_time,
        categorical=categorical,
        template_hint=hint,
        anomaly=anomaly_detected,
    )

    return {
        "output_format": selected,
        "chart_config": chart_config,
    }

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
from agents.m1.schemas.analysis_models import VisualizationHints

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
    hints: VisualizationHints | None = None,
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

    # Priority 1: Validated Agentic Override
    if hints:
        if hints.x_axis and hints.x_axis in columns:
            x_field = hints.x_axis
        if hints.y_axis and hints.y_axis in columns:
            y_field = hints.y_axis

    # Priority 2: Smart Heuristics Fallback (only if not overridden)
    if not hints or not hints.x_axis or hints.x_axis not in columns:
        if output_format == "line_chart":
            time_cols = [c for c in columns if c.lower() in _TIME_COLUMN_PATTERNS or c.lower().endswith(("_date", "_at"))]
            if time_cols:
                x_field = time_cols[0]
        elif output_format == "bar_chart":
            # Exclude UUIDs
            valid_cats = [c for c in columns if c.lower() not in ("id", "uuid") and not c.lower().endswith("_id")]
            if valid_cats:
                # Find first string column
                str_cols = []
                if raw_data:
                    str_cols = [c for c in valid_cats if isinstance(raw_data[0].get(c), str)]
                x_field = str_cols[0] if str_cols else valid_cats[0]

    # For y_field fallback, if not overridden, pick first numeric column after x_field
    if not hints or not hints.y_axis or hints.y_axis not in columns:
        if len(columns) > 2:
            for col in columns:
                if col == x_field:
                    continue
                sample_val = raw_data[0].get(col) if raw_data else None
                if isinstance(sample_val, (int, float)):
                    y_field = col
                    break
        elif len(columns) == 2:
            y_field = columns[1] if columns[0] == x_field else columns[0]

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
    hints = state.get("visualization_hints")
    if isinstance(hints, dict):
        hints = VisualizationHints(**hints)

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
        chart_config = _build_chart_config(existing_format, columns, raw_data, language, hints)
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

    # Determine the best data visualization format regardless of anomaly
    data_format = ""
    if hints and hints.chart_type:
        data_format = hints.chart_type
    elif hint and hint != "alert":
        data_format = hint
    elif evaluator_hint:
        data_format = evaluator_hint
    elif intent == "tax_reasoning":
        data_format = "narrative"
    elif row_count == 0:
        data_format = "direct_text"
    elif row_count == 1 and col_count == 1:
        data_format = "direct_text"
    elif row_count == 1 and col_count <= 3:
        data_format = "metric_card"
    elif has_time and row_count > 1:
        data_format = "line_chart"
    elif categorical and row_count <= 12:
        data_format = "bar_chart"
    elif 1 <= row_count <= 5 and col_count <= 3:
        data_format = "formatted_text_list"
    elif row_count > 5:
        data_format = "table"
    elif intent == "invoice_analysis":
        data_format = "narrative"
    else:
        data_format = "direct_text"

    # 1. Alert Card — anomaly detected (highest priority, but keep data viz)
    if anomaly_detected:
        selected = "alert"
    # 2. Template-specific hint
    elif hint:
        selected = hint
    elif evaluator_hint:
        selected = evaluator_hint
    else:
        selected = data_format

    # ── Build chart_config for chart types ─────────────────────────────────
    # When format is alert, build chart_config for the secondary data format
    chart_format = data_format if selected == "alert" else selected
    chart_config = _build_chart_config(chart_format, columns, raw_data, language, hints)

    logger.info(
        "output_selector: format selected",
        format=selected,
        data_format=data_format,
        row_count=row_count,
        col_count=col_count,
        has_time=has_time,
        categorical=categorical,
        template_hint=hint,
        anomaly=anomaly_detected,
    )

    result: dict = {
        "output_format": selected,
        "chart_config": chart_config,
    }
    # When alert is selected, pass the data format so the renderer
    # can show both the alert AND the data visualization.
    if selected == "alert" and data_format and data_format != "direct_text":
        result["extracted_params"] = {
            **state.get("extracted_params", {}),
            "alert_data_format": data_format,
        }

    return result


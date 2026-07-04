"""
OutputSelectorNode — Sprint 5.

Determines the best output format based on TWO factors:
    1. User intent (from intent classifier)
    2. Actual data shape (from the tool node)

Blueprint reference: section 2.8 — Adaptive Output Selector
Sprint plan: M1_Sprints.md Sprint 5

Division of labor (post chart-flow unification):
    This node decides WHAT to render (output_format) and honors agent
    visualization_hints for that choice. The downstream chart_config node
    is the single builder of the final chart_config and may downgrade the
    format when the data cannot support it.

8 output types:
    direct_text         — single scalar value (1 row, 1 col)
    metric_card         — KPI number with comparison context
    formatted_text_list — small list (1-5 rows, ≤ 3 cols)
    table               — large dataset (> 5 rows or > 12 categorical items)
    bar_chart           — categorical comparison (≤ 12 items)
    line_chart          — time series data (3+ points)
    narrative           — explanation / analysis / tax reasoning
    alert               — anomaly detected → colored alert card
"""

from __future__ import annotations


import structlog

from agents.m1.schemas.m1_state import M1State
from agents.m1.utils.numeric import coerce_hints

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

_VALID_FORMATS: frozenset[str] = frozenset({
    "direct_text", "metric_card", "formatted_text_list", "table",
    "bar_chart", "line_chart", "narrative", "alert",
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


async def select_output(state: M1State) -> dict:
    """
    OutputSelectorNode: determine the best output format for the response.

    Guard Clause: If output_format was already set by an upstream node
    (e.g. tax_rag_node sets "narrative"), preserve that decision. The
    downstream chart_config node builds chart_config for whichever format
    survives.

    Args:
        state: Current M1State with raw_data, intent, extracted_params, etc.

    Returns:
        Partial M1State dict: { output_format }
    """
    hints = coerce_hints(state.get("visualization_hints"))

    # ── Guard Clause: preserve upstream output_format ──────────────────────
    existing_format = state.get("output_format")
    if existing_format:
        logger.info(
            "output_selector: preserving upstream output_format",
            format=existing_format,
        )
        return {"output_format": existing_format}

    # ── Main selection logic ──────────────────────────────────────────────
    raw_data: list = state.get("raw_data", [])
    intent: str = state.get("intent", "")
    extracted_params: dict = state.get("extracted_params", {})
    anomaly_detected: bool = state.get("anomaly_detected", False)
    evaluator_hint: str = state.get("result_format_hint", "")
    if evaluator_hint not in _VALID_FORMATS:
        evaluator_hint = ""

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
    elif row_count == 2 and col_count >= 2:
        # Two rows = a pairwise comparison (Q1 vs Q2) — bars, never a 2-point line
        data_format = "bar_chart"
    elif has_time and row_count >= 3:
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
    # 2. Agent visualization hint — outranks all shape heuristics
    elif hints and hints.chart_type:
        selected = hints.chart_type
    # 3. Template-specific hint
    elif hint:
        selected = hint
    elif evaluator_hint:
        selected = evaluator_hint
    else:
        selected = data_format

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

    result: dict = {"output_format": selected}
    # When alert is selected, pass the data format so the renderer
    # can show both the alert AND the data visualization.
    if selected == "alert" and data_format and data_format != "direct_text":
        result["extracted_params"] = {
            **state.get("extracted_params", {}),
            "alert_data_format": data_format,
        }

    return result

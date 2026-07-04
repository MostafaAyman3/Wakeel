"""ChartConfigNode — the single authoritative builder of the final chart config.

Runs AFTER output_selector in both graphs. output_selector decides WHAT to
show (output_format); this node decides HOW to draw it and is the only node
allowed to write the final ``chart_config``.

Contract with output_selector:
    - Never contradict a non-chart format (narrative, table, metric_card...):
      those get chart_config = None.
    - For chart formats it honors visualization_hints (x_axis, y_axis,
      sort_by) when the referenced columns exist, then falls back to
      heuristics.
    - If the data cannot support the requested chart it DOWNGRADES the
      output_format (1 row → metric_card, no numeric column → table,
      2-point line → bar) instead of emitting a config the frontend
      cannot render.

Emitted config is ECharts-shaped and keeps both ``type`` and ``chart_type``
keys plus x_axis/y_axis label objects for frontend compatibility.
"""

from __future__ import annotations

import re

import structlog

from agents.m1.schemas.m1_state import M1State
from agents.m1.utils.numeric import coerce_hints, is_numeric_column, to_float

logger = structlog.get_logger(__name__)

_CHART_FORMATS = {"bar_chart", "line_chart"}

_TIME_TOKENS = ("date", "period", "month", "year", "quarter", "week", "day")


def _is_time_column(name: str) -> bool:
    lowered = name.lower()
    return (
        lowered in _TIME_TOKENS
        or lowered.endswith(("_date", "_at"))
        or any(token == part for token in _TIME_TOKENS for part in lowered.split("_"))
    )


def _is_id_column(name: str) -> bool:
    lowered = name.lower()
    return lowered in ("id", "uuid") or lowered.endswith("_id")


def filter_empty_rows(rows: list[dict]) -> list[dict]:
    return [
        row for row in rows
        if any(v not in (None, "", "—", "-") for v in row.values())
    ]


def _visible_columns(rows: list[dict]) -> list[str]:
    """Columns worth charting — drops internal (_-prefixed) fields."""
    return [c for c in rows[0].keys() if not c.startswith("_")]


def _unique_per_row(rows: list[dict], col: str) -> bool:
    values = [str(row.get(col)) for row in rows]
    return len(set(values)) == len(values)


def _pick_x_column(columns: list[str], rows: list[dict], hint_x: str | None) -> str:
    # Priority 1: validated agent hint — but a hint whose values repeat
    # (Q1,Q1,Q1...) is not an axis; fall through to heuristics instead.
    if hint_x and hint_x in columns and _unique_per_row(rows, hint_x):
        return hint_x
    # Priority 2: explicit period-label columns beat generic time columns —
    # comparison results carry both (month + quarter); the label is the axis.
    # Only when unique per row: a repeated label (Q1,Q1,Q1...) is not an axis.
    for col in columns:
        if col.lower() in ("period", "quarter") and _unique_per_row(rows, col):
            return col
    # Priority 3: time column
    for col in columns:
        if _is_time_column(col):
            return col
    # Priority 3: first non-id string (categorical) column
    for col in columns:
        if _is_id_column(col):
            continue
        sample = next((r.get(col) for r in rows if r.get(col) is not None), None)
        if isinstance(sample, str) and to_float(sample) is None:
            return col
    return columns[0]


def _pick_y_columns(
    columns: list[str], rows: list[dict], x_col: str, hint_y: str | None
) -> list[str]:
    # Priority 1: validated agent hint (must actually hold numbers)
    if hint_y and hint_y in columns and hint_y != x_col and is_numeric_column(rows, hint_y):
        return [hint_y]
    # Priority 2: every numeric non-id column → multi-series support
    # (this is what makes the T3 pivoted data with Arabic legend columns work)
    return [
        col for col in columns
        if col != x_col and not _is_id_column(col) and is_numeric_column(rows, col)
    ]


def _sort_rows(rows: list[dict], x_col: str, sort_by: str | None) -> list[dict]:
    if sort_by and rows and sort_by in rows[0]:
        if is_numeric_column(rows, sort_by):
            return sorted(rows, key=lambda r: to_float(r.get(sort_by)) or 0.0, reverse=True)
        return sorted(rows, key=lambda r: str(r.get(sort_by, "")))
    if _is_time_column(x_col):
        # Chronological order for time axes (ISO dates/periods sort correctly as strings)
        return sorted(rows, key=lambda r: str(r.get(x_col, "")))
    return rows


# Arabic display names for the columns our templates and NL2SQL commonly emit.
# The UI is Arabic-first; English axis labels on an Arabic narrative break
# the one-system feel. Unmapped columns fall back to Title Case.
_AR_LABELS: dict[str, str] = {
    "period": "الفترة",
    "month": "الشهر",
    "quarter": "الربع",
    "year": "السنة",
    "week": "الأسبوع",
    "day": "اليوم",
    "revenue": "الإيراد",
    "total_revenue": "إجمالي الإيراد",
    "total_amount": "إجمالي المبلغ",
    "total_sales": "إجمالي المبيعات",
    "total_purchases": "إجمالي المشتريات",
    "net_income": "صافي الدخل",
    "amount": "المبلغ",
    "avg_amount": "متوسط المبلغ",
    "category": "الفئة",
    "category_revenue": "إيراد الفئة",
    "name": "الاسم",
    "customer_name": "العميل",
    "vendor_name": "المورد",
    "total_vat": "إجمالي الضريبة",
    "total_units": "الوحدات المباعة",
    "total_overdue": "إجمالي المتأخرات",
    "total_cost": "إجمالي التكلفة",
    "invoice_date": "تاريخ الفاتورة",
    "payment_status": "حالة السداد",
}


def _label(name: str, language: str = "en") -> str:
    if language == "ar":
        arabic = _AR_LABELS.get(name.lower())
        if arabic:
            return arabic
    return name.replace("_", " ").strip().title() if name.isascii() else name


_ISO_DATE_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})([T ]|$)")


def _humanize_x_value(value, x_col: str) -> str:
    """Turn raw axis values into readable labels.

    "2026-01-01T00:00:00+00:00" → "2026-01" · quarter 2.0 → "Q2" · 5.0 → "5"
    """
    if value is None:
        return "—"

    lowered = x_col.lower()
    num = to_float(value)
    if num is not None and num.is_integer():
        n = int(num)
        if "quarter" in lowered and 1 <= n <= 4:
            return f"Q{n}"
        return str(n)

    raw = str(value)
    match = _ISO_DATE_RE.match(raw)
    if match:
        year, month, day = match.group(1), match.group(2), match.group(3)
        return f"{year}-{month}" if day == "01" else f"{year}-{month}-{day}"
    return raw


_ISO_DAY_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})")

_QUARTER_BY_START_MONTH = {1: "Q1", 4: "Q2", 7: "Q3", 10: "Q4"}


def _iso_day(value) -> str | None:
    """Normalize a value to YYYY-MM-DD, or None if it isn't a date."""
    match = _ISO_DAY_RE.match(str(value)) if value is not None else None
    return match.group(0) if match else None


def _period_label(rng: dict) -> str:
    """Human label for a {start, end} range: Q2-2024, M5-2024."""
    day = _iso_day(rng.get("start")) or ""
    year, month = day[:4], int(day[5:7] or 0)
    quarter = _QUARTER_BY_START_MONTH.get(month)
    return f"{quarter}-{year}" if quarter else f"M{month}-{year}"


def _build_comparison_overlay(
    rows: list[dict], frame: dict, language: str
) -> dict | None:
    """Aligned overlay for period comparisons — one series per period.

    Fires only when the analysis frame carries BOTH date_range and
    comparison_range and the rows are a parseable time series with ≥2 rows
    falling inside EACH range. Two near-equal aggregate bars hide the story;
    aligning the periods side by side shows level AND shape at once.
    """
    base_rng = frame.get("date_range") or {}
    comp_rng = frame.get("comparison_range") or {}
    bounds = []
    for rng in (base_rng, comp_rng):
        start = _iso_day(rng.get("start")) if isinstance(rng, dict) else None
        end = _iso_day(rng.get("end")) if isinstance(rng, dict) else None
        if not (start and end):
            return None
        bounds.append((start, end))

    columns = _visible_columns(rows) if rows else []
    time_col = next(
        (
            c for c in columns
            if _is_time_column(c)
            and all(_iso_day(r.get(c)) for r in rows if r.get(c) is not None)
        ),
        None,
    )
    if not time_col:
        return None
    y_col = next(
        (
            c for c in columns
            if c != time_col and not _is_id_column(c) and is_numeric_column(rows, c)
        ),
        None,
    )
    if not y_col:
        return None

    buckets: list[list[dict]] = [[], []]
    for row in rows:
        day = _iso_day(row.get(time_col))
        if not day:
            continue
        for idx, (start, end) in enumerate(bounds):
            if start <= day <= end:
                buckets[idx].append(row)
                break
    if any(len(bucket) < 2 for bucket in buckets):
        return None  # 1-row-per-period comparisons render as plain bars

    for bucket in buckets:
        bucket.sort(key=lambda r: _iso_day(r.get(time_col)) or "")

    length = max(len(b) for b in buckets)
    slot = "شهر" if language == "ar" else "Month"
    x_data = [f"{slot} {i + 1}" for i in range(length)]

    series = []
    for rng, bucket in zip((base_rng, comp_rng), buckets):
        data = [to_float(row.get(y_col)) for row in bucket]
        data += [None] * (length - len(data))
        series.append(
            {
                "name": _period_label(rng),
                "type": "bar",
                "data": data,
                "smooth": False,
            }
        )

    return {
        "type": "bar",
        "chart_type": "bar",
        "xAxis": {"data": x_data},
        "series": series,
        "x_axis": {"field": time_col, "label": _label(time_col, language)},
        "y_axis": {"field": y_col, "label": _label(y_col, language)},
        "title": "",
    }


def build_chart_config(
    chart_format: str,
    rows: list[dict],
    hints,
    language: str = "en",
) -> tuple[dict | None, str]:
    """Build the ECharts config for a requested chart format.

    Returns (config, effective_format). effective_format may downgrade the
    requested one when the data cannot support it.
    """
    rows = filter_empty_rows(rows)
    if not rows:
        return None, chart_format

    columns = _visible_columns(rows)
    if not columns:
        return None, chart_format

    # A single row cannot be a comparison — it is a KPI.
    if len(rows) == 1:
        return None, "metric_card"

    hint_x = hints.x_axis if hints else None
    hint_y = hints.y_axis if hints else None
    sort_by = hints.sort_by if hints else None

    x_col = _pick_x_column(columns, rows, hint_x)
    y_cols = _pick_y_columns(columns, rows, x_col, hint_y)

    if not y_cols:
        # Nothing measurable to plot — a table shows the data honestly.
        return None, "table"

    rows = _sort_rows(rows, x_col, sort_by)

    x_data = [_humanize_x_value(row.get(x_col), x_col) for row in rows]

    chart_type = "line" if chart_format == "line_chart" else "bar"
    # A 2-point "trend" is a comparison, not a trend — bars read better.
    if chart_type == "line" and len(set(x_data)) < 3:
        chart_type = "bar"

    series = [
        {
            "name": _label(y_col, language),
            "type": chart_type,
            "data": [to_float(row.get(y_col)) for row in rows],
            "smooth": chart_type == "line",
        }
        for y_col in y_cols
    ]

    config = {
        "type": chart_type,
        "chart_type": chart_type,
        "xAxis": {"data": x_data},
        "series": series,
        "x_axis": {"field": x_col, "label": _label(x_col, language)},
        "y_axis": {"field": y_cols[0], "label": _label(y_cols[0], language)},
        "title": "",
    }
    effective_format = "line_chart" if chart_type == "line" else "bar_chart"
    return config, effective_format


def chart_config_node(state: M1State) -> dict:
    output_format: str = state.get("output_format", "direct_text")
    raw_data: list = state.get("raw_data", []) or []
    hints = coerce_hints(state.get("visualization_hints"))
    extracted_params: dict = state.get("extracted_params", {}) or {}

    result: dict = {}

    # Keep the table/list views clean too — drop fully-empty rows once, here.
    filtered = filter_empty_rows(raw_data)
    if len(filtered) != len(raw_data):
        result["raw_data"] = filtered

    # For alerts the chart accompanies the alert card; the format to draw
    # comes from alert_data_format set by output_selector.
    chart_format = output_format
    is_alert = output_format == "alert"
    if is_alert:
        chart_format = extracted_params.get("alert_data_format", "")

    if chart_format not in _CHART_FORMATS:
        result["chart_config"] = None
        return result

    language = state.get("language", "en")

    # Comparison intent reaches the presentation layer here: when the frame
    # carries both periods and the data spans them, render an aligned overlay
    # instead of an undifferentiated timeline.
    overlay = _build_comparison_overlay(
        filtered, state.get("analysis_frame", {}) or {}, language
    )
    if overlay:
        logger.info(
            "chart_config: comparison overlay rendered",
            series=[s["name"] for s in overlay["series"]],
            points=len(overlay["xAxis"]["data"]),
        )
        result["chart_config"] = overlay
        if is_alert:
            if extracted_params.get("alert_data_format") != "bar_chart":
                result["extracted_params"] = {
                    **extracted_params,
                    "alert_data_format": "bar_chart",
                }
        elif output_format != "bar_chart":
            result["output_format"] = "bar_chart"
        return result

    config, effective_format = build_chart_config(
        chart_format, filtered, hints, language=language
    )
    result["chart_config"] = config

    if is_alert:
        # The primary format stays "alert"; sync the secondary format only.
        if effective_format != chart_format:
            result["extracted_params"] = {
                **extracted_params,
                "alert_data_format": effective_format,
            }
    elif effective_format != output_format:
        logger.info(
            "chart_config: downgraded format",
            requested=output_format,
            effective=effective_format,
            rows=len(filtered),
        )
        result["output_format"] = effective_format

    return result

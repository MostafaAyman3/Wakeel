from typing import Optional
from agents.m1.schemas.m1_state import M1State


CHART_RULES = {
    "none": 0,
    "metric_card": 1,
    "bar": 2,         # نقطتان أو فئات
    "line": 3,        # time series 3+
}


def decide_chart_type(query_result: dict) -> str:
    rows = query_result.get("rows", [])
    data_points = len(rows)
    is_time_series = query_result.get("is_time_series", False)

    if data_points == 0:
        return "none"
    if data_points == 1:
        return "metric_card"
    if data_points == 2:
        return "bar"
    if data_points >= 3 and is_time_series:
        return "line"
    return "bar"


def build_echarts_config(chart_type: str, query_result: dict) -> Optional[dict]:
    rows = query_result.get("rows", [])
    if not rows:
        return None

    label_key = query_result.get("label_key", "label")
    value_key = query_result.get("value_key", "value")

    if chart_type == "none":
        return None

    if chart_type == "metric_card":
        return {
            "type": "metric_card",
            "value": rows[0].get(value_key),
            "label": rows[0].get(label_key),
        }

    keys = list(rows[0].keys())
    x_col = keys[0]
    
    y_cols = []
    for k in keys[1:]:
        sample_val = next((r.get(k) for r in rows if r.get(k) is not None), None)
        if isinstance(sample_val, (int, float)):
            y_cols.append(k)
    
    if not y_cols and len(keys) > 1:
        y_cols = keys[1:]

    if chart_type in ("bar", "line"):
        x_data = [row.get(x_col) for row in rows]
        series_list = []
        for y_col in y_cols:
            series_list.append({
                "name": str(y_col).replace("_", " ").title(),
                "type": chart_type,
                "data": [row.get(y_col) for row in rows],
                "smooth": chart_type == "line"
            })
            
        return {
            "type": chart_type,
            "xAxis": {"data": x_data},
            "series": series_list,
        }

    return None


def filter_empty_rows(rows: list[dict]) -> list[dict]:
    return [
        row for row in rows
        if any(v not in (None, "", "—", "-") for v in row.values())
    ]


def chart_config_node(state: M1State) -> M1State:
    query_result = state.get("query_result", {})
    
    # محول (Adapter) لتحويل raw_data إلى الشكل المتوقع إذا لم تكن query_result موجودة
    if not query_result:
        raw_data = state.get("raw_data", [])
        if raw_data:
            # نستبعد الأعمدة الداخلية زي _analysis_step
            columns = [c for c in raw_data[0].keys() if not c.startswith("_")]
            
            # محاولة ذكية لاختيار عمود الـ label (نصوص أو تواريخ) وعمود الـ value (أرقام)
            label_col = next((c for c in columns if isinstance(raw_data[0][c], str)), columns[0] if len(columns) > 0 else "label")
            val_col = next((c for c in columns if isinstance(raw_data[0][c], (int, float))), columns[-1] if len(columns) > 1 else "value")

            is_time_col = (
                any(k in label_col.lower() for k in {"date", "period", "month", "year", "quarter"})
                or label_col.lower().endswith("_date")
            )

            query_result = {
                "rows": raw_data,
                "label_key": label_col,
                "value_key": val_col,
                "is_time_series": is_time_col
            }

    # فلتر الصفوف الفارغة أولاً
    if "rows" in query_result:
        query_result["rows"] = filter_empty_rows(query_result["rows"])

    chart_type = decide_chart_type(query_result)
    chart_config = build_echarts_config(chart_type, query_result)

    # تحديث raw_data بالبيانات المفلترة لكي ينعكس على الجدول في الـ Frontend
    if "rows" in query_result and "raw_data" in state:
        state["raw_data"] = query_result["rows"]

    return {**state, "chart_config": chart_config}

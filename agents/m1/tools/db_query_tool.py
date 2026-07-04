"""
Dynamic Query Builder Tool (Sprint 2)
Matches user queries to 10 predefined SQL templates, extracts parameters,
validates the SQL, and executes on the read-only database.
"""
from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import text
from pydantic import BaseModel, Field
import structlog

from agents.shared.llm_client import llm_fast
from agents.m1.schemas.m1_state import M1State
from agents.m1.tools.query_gateway import execute_readonly_query
from agents.m1.utils.numeric import is_numeric_column, to_float

logger = structlog.get_logger(__name__)

class TemplateSelection(BaseModel):
    """Structured output for selecting the right template and formatting its parameters."""
    template_id: str = Field(
        description="Must be exactly one of: T1, T2, T3, T4, T5, T6, T7, T8, T9, T10"
    )
    start_date: str | None = Field(default=None, description="YYYY-MM-DD or None")
    end_date: str | None = Field(default=None, description="YYYY-MM-DD or None")
    as_of_date: str | None = Field(default=None, description="YYYY-MM-DD or None")
    vendor_id: str | None = Field(default=None, description="Vendor ID (UUID or text string) or None")
    payment_status: str | None = Field(default=None, description="Paid, Unpaid, Partial, Overdue, or None")
    n: int = Field(default=5, description="Limit for top N queries")
    order: str = Field(default="DESC", description="ASC or DESC")
    multiplier: float = Field(default=2.0, description="Multiplier for anomaly detection")


TEMPLATE_PROMPT = """\
You are a SQL Template Selector for an ERP Intelligence Agent.
Match the user's query to exactly ONE of the 10 predefined templates below.

T1 (revenue_by_period): Sum of revenue between start and end dates.
T2 (sales_time_series): Daily/Monthly sales aggregation for Line Charts.
T3 (executive_summary): High-level summary of sales, purchases, and net income.
T4 (aging_buckets): Accounts receivable aging buckets (0-30, 30-60, 60-90, 90+ days). Needs as_of_date.
T5 (vat_summary): VAT tax totals within a specific period.
T6 (expense_anomaly): Flags expenses exceeding historical average by a multiplier (default 2.0).
T7 (top_n_customers): Orders customers by revenue. Needs limit 'n' and 'order'.
T8 (category_revenue): Revenue broken down by product categories.
T9 (vendor_invoices): Retrieves vendor invoices filtered by vendor_id and payment_status.
T10 (top_n_products): Top N products by units sold or revenue. Needs limit 'n' and 'order'.

Current Date: {current_date}
User Query: {query}
Extracted Params (from intent classifier): {params}

Return the matching template ID (e.g., "T1") and map the parameters.
If a parameter is not mentioned, return None. For dates, use the format YYYY-MM-DD.

Date rules (critical):
- If the user names a year (e.g. "2024"), use that FULL year:
  start_date=YYYY-01-01, end_date=YYYY-12-31. NEVER substitute the current
  year for a year the user explicitly named.
- If no period is mentioned at all, default to the current year.

Template preference:
- "أداء المبيعات" / "sales performance" / trend over a period longer than one
  month → prefer T2 (time series) so the user sees the evolution, not T1's
  single total. Months without data simply won't appear in the result — that
  is correct behavior, do not widen the range to compensate.
"""

TEMPLATES = {
    "T1": text("""
        SELECT SUM(total_amount) as total_revenue
        FROM invoices
        WHERE type ILIKE 'sales'
          AND invoice_date >= :start_date
          AND invoice_date <= :end_date
    """),
    
    "T2": text("""
        SELECT DATE_TRUNC('month', invoice_date) as period, SUM(total_amount) as revenue
        FROM invoices
        WHERE type ILIKE 'sales'
          AND invoice_date >= :start_date
          AND invoice_date <= :end_date
        GROUP BY period
        ORDER BY period ASC
    """),
    
    "T3": text("""
        SELECT 
            (SELECT COALESCE(SUM(total_amount), 0) FROM invoices WHERE type ILIKE 'sales' AND invoice_date BETWEEN :start_date AND :end_date) as total_sales,
            (SELECT COALESCE(SUM(total_amount), 0) FROM invoices WHERE type ILIKE 'purchase' AND invoice_date BETWEEN :start_date AND :end_date) as total_purchases,
            ((SELECT COALESCE(SUM(total_amount), 0) FROM invoices WHERE type ILIKE 'sales' AND invoice_date BETWEEN :start_date AND :end_date) - 
             (SELECT COALESCE(SUM(total_amount), 0) FROM invoices WHERE type ILIKE 'purchase' AND invoice_date BETWEEN :start_date AND :end_date)) as net_income
    """),

    "T4": text("""
        SELECT 
            c.name as customer_name,
            SUM(CASE WHEN i.due_date >= CAST(:as_of_date AS timestamp) - INTERVAL '30 days' THEN i.total_amount ELSE 0 END) as "0_30_days",
            SUM(CASE WHEN i.due_date >= CAST(:as_of_date AS timestamp) - INTERVAL '60 days' AND i.due_date < CAST(:as_of_date AS timestamp) - INTERVAL '30 days' THEN i.total_amount ELSE 0 END) as "30_60_days",
            SUM(CASE WHEN i.due_date >= CAST(:as_of_date AS timestamp) - INTERVAL '90 days' AND i.due_date < CAST(:as_of_date AS timestamp) - INTERVAL '60 days' THEN i.total_amount ELSE 0 END) as "60_90_days",
            SUM(CASE WHEN i.due_date < CAST(:as_of_date AS timestamp) - INTERVAL '90 days' THEN i.total_amount ELSE 0 END) as "90_plus_days",
            SUM(i.total_amount) as total_overdue
        FROM invoices i
        JOIN customers c ON i.customer_id = c.id
        WHERE i.type ILIKE 'sales' 
          AND i.payment_status ILIKE ANY (ARRAY['unpaid', 'overdue', 'partial'])
          AND i.due_date < CAST(:as_of_date AS timestamp)
        GROUP BY c.id, c.name
        HAVING SUM(i.total_amount) > 0
        ORDER BY total_overdue DESC
    """),

    "T5": text("""
        SELECT SUM(tax_amount) as total_vat
        FROM invoices
        WHERE invoice_date BETWEEN :start_date AND :end_date
    """),

    "T6": text("""
        WITH historical_avg AS (
            SELECT category, AVG(amount) as avg_amount
            FROM transactions
            WHERE type ILIKE 'expense'
            GROUP BY category
        )
        SELECT t.id, t.category, t.amount, t.transaction_date, h.avg_amount
        FROM transactions t
        JOIN historical_avg h ON t.category = h.category
        WHERE t.type ILIKE 'expense'
          AND t.amount > (h.avg_amount * :multiplier)
        ORDER BY t.amount DESC
    """),

    "T7": text("""
        SELECT c.name, SUM(i.total_amount) as total_revenue
        FROM invoices i
        JOIN customers c ON i.customer_id = c.id
        WHERE i.type ILIKE 'sales'
        GROUP BY c.id, c.name
        ORDER BY total_revenue {order}
        LIMIT :n
    """),

    "T8": text("""
        SELECT p.category, SUM(ii.total_price) as category_revenue
        FROM invoice_items ii
        JOIN invoices i ON ii.invoice_id = i.id
        JOIN products p ON ii.product_id = p.id
        WHERE i.type ILIKE 'sales'
          AND i.invoice_date BETWEEN :start_date AND :end_date
        GROUP BY p.category
        ORDER BY category_revenue DESC
    """),

    "T9": text("""
        SELECT i.display_id, i.invoice_date, i.total_amount, i.payment_status, v.name as vendor_name
        FROM invoices i
        JOIN vendors v ON i.vendor_id = v.id
        WHERE i.type ILIKE 'purchase'
          AND (v.display_id = :vendor_id OR v.name ILIKE '%' || :vendor_id || '%' OR :vendor_id IS NULL)
          AND (i.payment_status ILIKE :payment_status OR :payment_status IS NULL)
          AND (i.invoice_date BETWEEN :start_date AND :end_date)
        ORDER BY i.invoice_date DESC
    """),

    "T10": text("""
        SELECT
            p.name, p.category,
            SUM(ii.quantity)    AS total_units,
            SUM(ii.total_price) AS total_revenue
        FROM invoice_items ii
        JOIN invoices inv ON inv.id = ii.invoice_id
        JOIN products  p  ON p.id  = ii.product_id
        WHERE inv.type ILIKE 'sales'
          AND inv.invoice_date BETWEEN :start_date AND :end_date
        GROUP BY p.id, p.name, p.category
        ORDER BY total_revenue {order}
        LIMIT :n
    """)
}

# ── Per-template visualization hints ──────────────────────────────────────────
# Templates have a known result shape, so the ideal rendering is known upfront.
# Stored as plain dicts (checkpoint-serializable); coerced downstream.
TEMPLATE_VIZ_HINTS: dict[str, dict] = {
    "T1":  {"chart_type": "metric_card"},
    "T2":  {"chart_type": "line_chart", "x_axis": "period", "y_axis": "revenue"},
    "T3":  {"chart_type": "metric_card"},
    "T4":  {"chart_type": "table"},
    "T5":  {"chart_type": "metric_card"},
    "T6":  {"chart_type": "table"},   # data view shown under the anomaly alert
    "T7":  {"chart_type": "bar_chart", "x_axis": "name", "y_axis": "total_revenue", "sort_by": "total_revenue"},
    "T8":  {"chart_type": "bar_chart", "x_axis": "category", "y_axis": "category_revenue", "sort_by": "category_revenue"},
    "T9":  {"chart_type": "table"},
    "T10": {"chart_type": "bar_chart", "x_axis": "name", "y_axis": "total_revenue", "sort_by": "total_revenue"},
}

# When the same template runs twice (base vs comparison period), the merged
# result is a pairwise comparison — bars over the period label, always.
COMPARISON_VIZ_HINTS: dict = {"chart_type": "bar_chart", "x_axis": "period"}


def _one_row_per_period(rows: list[dict], label: str) -> list[dict]:
    """Collapse a template result to a single labeled row for comparison mode.

    Templates like T2 return one row PER MONTH — stamping every row with the
    same period label would produce duplicate x-axis categories, so multi-row
    results are aggregated (SUM of numeric columns) into one row per period.
    """
    if not rows:
        return []
    if len(rows) == 1:
        return [{**rows[0], "period": label}]
    aggregated: dict = {"period": label}
    for col in rows[0]:
        if col != "period" and is_numeric_column(rows, col):
            aggregated[col] = sum(to_float(r.get(col)) or 0.0 for r in rows)
    return [aggregated]


async def db_query_tool(state: M1State) -> dict:
    """Executes the exact requested dynamic SQL template on the read-only DB.

    Comparison support (Sprint 6+):
        When extracted_params contains ``comparison: true`` and
        ``compare_range: {start, end}``, the same template is executed twice
        (once for the base date_range, once for compare_range) and the results
        are merged with a ``period`` label for downstream bar_chart rendering.
    """
    query = state.get("query", "")
    extracted_params = state.get("extracted_params", {})
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = TEMPLATE_PROMPT.format(
        current_date=current_date, 
        query=query, 
        params=json.dumps(extracted_params, ensure_ascii=False)
    )
    
    # Use LLM to classify template and format parameters
    selector = llm_fast.with_structured_output(TemplateSelection, method="function_calling")
    try:
        selection: TemplateSelection = await selector.ainvoke(prompt)
    except Exception as e:
        logger.error("LLM template selection failed", error=str(e))
        return {"error": "Failed to map query to a valid template."}
        
    tid = selection.template_id if selection.template_id in TEMPLATES else "T1"
    
    # Defaulting dates safely and parsing to datetime objects for asyncpg
    start_dt_str = selection.start_date or "2000-01-01"
    end_dt_str = selection.end_date or "2100-01-01"
    as_of_str = selection.as_of_date or current_date
    
    def parse_date(d_str: str):
        try:
            return datetime.strptime(d_str, "%Y-%m-%d").date()
        except ValueError:
            return datetime.now().date()
            
    start_dt = parse_date(start_dt_str)
    end_dt = parse_date(end_dt_str)
    as_of = parse_date(as_of_str)
    
    # Secure dynamic injection for order
    order_clause = "ASC" if selection.order.upper() == "ASC" else "DESC"
    
    sql_text = TEMPLATES[tid]
    rendered_sql_str = sql_text.text.format(order=order_clause)
    
    params = {
        "start_date": start_dt,
        "end_date": end_dt,
        "as_of_date": as_of,
        "vendor_id": selection.vendor_id,
        "payment_status": selection.payment_status,
        "n": selection.n,
        "multiplier": selection.multiplier
    }

    # ── Comparison mode ───────────────────────────────────────────
    # If the intent classifier extracted comparison: true + compare_range,
    # run the query twice and merge results with period labels.
    is_comparison = extracted_params.get("comparison", False)
    compare_range = extracted_params.get("compare_range")

    if is_comparison and compare_range and isinstance(compare_range, dict):
        compare_start = parse_date(compare_range.get("start", "2000-01-01"))
        compare_end = parse_date(compare_range.get("end", "2100-01-01"))

        # Helper to label a date range as "Q1-2024" or "Jan-Mar 2024"
        def label_period(s, e):
            q_map = {1: "Q1", 4: "Q2", 7: "Q3", 10: "Q4"}
            q = q_map.get(s.month, f"M{s.month}")
            return f"{q}-{s.year}"

        base_label = label_period(start_dt, end_dt)
        compare_label = label_period(compare_start, compare_end)

        compare_params = {
            **params,
            "start_date": compare_start,
            "end_date": compare_end,
        }
        rows1, artifact1 = await execute_readonly_query(
            sql=rendered_sql_str,
            parameters=params,
            source="template",
            purpose=f"{tid}:base_comparison_period",
        )
        rows2, artifact2 = await execute_readonly_query(
            sql=rendered_sql_str,
            parameters=compare_params,
            source="template",
            purpose=f"{tid}:comparison_period",
        )
        artifacts = [artifact1, artifact2]

        if any(a.get("execution_status") != "success" for a in artifacts):
            failed = next(
                a for a in artifacts if a.get("execution_status") != "success"
            )
            return {
                "error": failed.get("error_message", "Query execution failed."),
                "raw_data": [],
                "query_artifacts": state.get("query_artifacts", []) + artifacts,
                "result_status": "failed",
            }

        # Merge results — one aggregated, labeled row per period.
        results = _one_row_per_period(rows1, base_label) + _one_row_per_period(
            rows2, compare_label
        )

        try:
            logger.info(
                "db_query_tool: comparison query executed",
                template=tid,
                base_period=base_label,
                compare_period=compare_label,
                base_rows=len(rows1),
                compare_rows=len(rows2),
            )

        except Exception:
            logger.exception("db_query_tool: comparison logging failed", template=tid)

        return {
            "raw_data": results,
            "query_mode": "template",
            "matched_template": tid,
            "visualization_hints": COMPARISON_VIZ_HINTS,
            "query_artifacts": state.get("query_artifacts", []) + artifacts,
            "extracted_params": {
                **extracted_params,
                "applied_template": tid,
                "db_params": params,
                "compare_params": compare_params,
            }
        }

    # ── Standard (non-comparison) mode ────────────────────────────
    results, artifact = await execute_readonly_query(
        sql=rendered_sql_str,
        parameters=params,
        source="template",
        purpose=tid,
    )
    if artifact.get("execution_status") != "success":
        return {
            "error": artifact.get("error_message", "Query execution failed."),
            "raw_data": [],
            "query_mode": "template",
            "matched_template": tid,
            "query_artifacts": state.get("query_artifacts", []) + [artifact],
            "result_status": "failed",
        }

    return {
        "raw_data": results,
        "query_mode": "template",
        "matched_template": tid,
        "visualization_hints": TEMPLATE_VIZ_HINTS.get(tid),
        "query_artifacts": state.get("query_artifacts", []) + [artifact],
        "extracted_params": {
            **extracted_params,
            "applied_template": tid,
            "db_params": params
        }
    }


def _format_dates(row: dict) -> None:
    """Convert datetime/date objects in a row dict to ISO strings for JSON."""
    for k, v in row.items():
        if isinstance(v, datetime):
            row[k] = v.isoformat()
        elif hasattr(v, "isoformat"):
            row[k] = v.isoformat()


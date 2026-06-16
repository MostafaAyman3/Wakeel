"""
Invoice SQL Templates — Sprint 3.

8 pre-defined, parameterized templates covering all invoice_analysis subtypes.
All queries:
  - Target only: invoices, invoice_items, vendors (whitelist enforced in node)
  - Use SQLAlchemy bindparam (never string interpolation) to prevent injection
  - Are SELECT-only (AST validation re-used from Sprint 2)
  - Cap results at LIMIT 500

Vendor name matching uses LOWER(v.name) LIKE LOWER(:vendor_name)
with the caller passing  "%name%"  to enable partial matching.
"""

from __future__ import annotations

from sqlalchemy import text

# ─── Template registry ──────────────────────────────────────────────────────

INVOICE_TEMPLATES: dict[str, text] = {

    # T-INV-1 ─ Full detail for a single invoice (by display_id)
    "SINGLE_INVOICE_DETAIL": text("""
        SELECT
            i.display_id,
            i.invoice_date,
            i.due_date,
            i.total_amount,
            i.tax_amount,
            i.payment_status,
            v.name        AS vendor_name,
            v.display_id  AS vendor_display_id,
            ii.description,
            ii.quantity,
            ii.unit_price,
            ii.total_price,
            ii.tax_amount AS item_tax
        FROM invoices i
        LEFT JOIN vendors       v  ON i.vendor_id  = v.id
        LEFT JOIN invoice_items ii ON ii.invoice_id = i.id
        WHERE i.display_id ILIKE :invoice_display_id
        LIMIT 500
    """),

    # T-INV-2 ─ Totals summary for a date range
    "INVOICE_TOTALS_BY_DATE": text("""
        SELECT
            COUNT(*)                    AS invoice_count,
            SUM(i.total_amount)         AS total_amount,
            SUM(i.tax_amount)           AS total_vat,
            SUM(i.total_amount - i.tax_amount) AS total_net,
            AVG(i.total_amount)         AS avg_invoice_amount,
            MIN(i.invoice_date)         AS period_start,
            MAX(i.invoice_date)         AS period_end
        FROM invoices i
        WHERE i.type ILIKE 'purchase'
          AND i.invoice_date BETWEEN :start_date AND :end_date
    """),

    # T-INV-3 ─ VAT summary by period
    "INVOICE_VAT_SUMMARY": text("""
        SELECT
            DATE_TRUNC('month', i.invoice_date)  AS month,
            COUNT(*)                              AS invoice_count,
            SUM(i.tax_amount)                     AS total_vat,
            SUM(i.total_amount)                   AS total_gross,
            ROUND(
                100.0 * SUM(i.tax_amount) / NULLIF(SUM(i.total_amount), 0),
                2
            )                                     AS effective_vat_rate_pct
        FROM invoices i
        WHERE i.invoice_date BETWEEN :start_date AND :end_date
        GROUP BY DATE_TRUNC('month', i.invoice_date)
        ORDER BY month ASC
        LIMIT 500
    """),

    # T-INV-4 ─ Top N vendors by total cost
    "TOP_VENDORS_BY_COST": text("""
        SELECT
            v.name                 AS vendor_name,
            v.display_id           AS vendor_display_id,
            COUNT(i.id)            AS invoice_count,
            SUM(i.total_amount)    AS total_cost,
            SUM(i.tax_amount)      AS total_vat,
            AVG(i.total_amount)    AS avg_invoice_amount,
            MIN(i.invoice_date)    AS first_invoice,
            MAX(i.invoice_date)    AS last_invoice
        FROM invoices i
        JOIN vendors v ON i.vendor_id = v.id
        WHERE i.type ILIKE 'purchase'
          AND i.invoice_date BETWEEN :start_date AND :end_date
        GROUP BY v.id, v.name, v.display_id
        ORDER BY total_cost DESC
        LIMIT :limit
    """),

    # T-INV-5 ─ Overdue invoices (optionally filtered by vendor)
    "OVERDUE_INVOICES": text("""
        SELECT
            i.display_id,
            i.invoice_date,
            i.due_date,
            i.total_amount,
            i.payment_status,
            v.name           AS vendor_name,
            CAST(:as_of_date AS DATE) - i.due_date::DATE AS days_overdue
        FROM invoices i
        LEFT JOIN vendors v ON i.vendor_id = v.id
        WHERE i.payment_status ILIKE ANY (ARRAY['unpaid','overdue','partial'])
          AND i.due_date < CAST(:as_of_date AS TIMESTAMP)
          AND (
              CAST(:vendor_name AS TEXT) IS NULL
              OR LOWER(v.name) LIKE LOWER(:vendor_name)
          )
        ORDER BY days_overdue DESC
        LIMIT 500
    """),

    # T-INV-6 ─ Vendor cost trend over time (monthly buckets)
    "VENDOR_COST_OVER_TIME": text("""
        SELECT
            DATE_TRUNC('month', i.invoice_date) AS month,
            v.name                              AS vendor_name,
            COUNT(i.id)                         AS invoice_count,
            SUM(i.total_amount)                 AS monthly_cost,
            AVG(i.total_amount)                 AS avg_invoice_amount
        FROM invoices i
        JOIN vendors v ON i.vendor_id = v.id
        WHERE i.type ILIKE 'purchase'
          AND i.invoice_date BETWEEN :start_date AND :end_date
          AND (
              CAST(:vendor_name AS TEXT) IS NULL
              OR LOWER(v.name) LIKE LOWER(:vendor_name)
          )
        GROUP BY DATE_TRUNC('month', i.invoice_date), v.id, v.name
        ORDER BY month ASC, monthly_cost DESC
        LIMIT 500
    """),

    # T-INV-7 ─ Monthly invoice spend trend (all vendors)
    "INVOICE_TREND_ANALYSIS": text("""
        SELECT
            DATE_TRUNC('month', i.invoice_date) AS month,
            COUNT(i.id)                         AS invoice_count,
            SUM(i.total_amount)                 AS total_spend,
            SUM(i.tax_amount)                   AS total_vat,
            AVG(i.total_amount)                 AS avg_invoice_amount
        FROM invoices i
        WHERE i.type ILIKE 'purchase'
          AND i.invoice_date BETWEEN :start_date AND :end_date
        GROUP BY DATE_TRUNC('month', i.invoice_date)
        ORDER BY month ASC
        LIMIT 500
    """),

    # T-INV-8 ─ Recurring expense analysis (vendor invoices that repeat)
    "RECURRING_EXPENSE_ANALYSIS": text("""
        SELECT
            v.name                              AS vendor_name,
            COUNT(i.id)                         AS occurrence_count,
            SUM(i.total_amount)                 AS total_spend,
            AVG(i.total_amount)                 AS avg_invoice_amount,
            STDDEV(i.total_amount)              AS amount_stddev,
            MIN(i.invoice_date)                 AS first_seen,
            MAX(i.invoice_date)                 AS last_seen
        FROM invoices i
        JOIN vendors v ON i.vendor_id = v.id
        WHERE i.type ILIKE 'purchase'
          AND i.invoice_date BETWEEN :start_date AND :end_date
          AND (
              CAST(:vendor_name AS TEXT) IS NULL
              OR LOWER(v.name) LIKE LOWER(:vendor_name)
          )
        GROUP BY v.id, v.name
        HAVING COUNT(i.id) >= 2
        ORDER BY occurrence_count DESC, total_spend DESC
        LIMIT 500
    """),
}


def get_template(name: str) -> text | None:
    """Return the SQLAlchemy text object for a given template name, or None."""
    return INVOICE_TEMPLATES.get(name)


SUBTYPE_TO_TEMPLATE: dict[str, str] = {
    "single_invoice":     "SINGLE_INVOICE_DETAIL",
    "totals":             "INVOICE_TOTALS_BY_DATE",
    "vat_summary":        "INVOICE_VAT_SUMMARY",
    "top_vendors":        "TOP_VENDORS_BY_COST",
    "overdue":            "OVERDUE_INVOICES",
    "vendor_comparison":  "VENDOR_COST_OVER_TIME",
    "trend":              "INVOICE_TREND_ANALYSIS",
    "recurring":          "RECURRING_EXPENSE_ANALYSIS",
}

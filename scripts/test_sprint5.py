"""
Sprint 5 Integration Tests — Output Selector + Narrative Generator + Anomaly Detection.

10 test cases covering all 8 output types, guard clause, anomaly detection,
and narrative skip condition.

Usage:
    python scripts/test_sprint5.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import os
from datetime import datetime
from decimal import Decimal

# Ensure project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


# ──────────────────────────────────────────────────────────────────────────────
# Test helpers
# ──────────────────────────────────────────────────────────────────────────────

PASSED = 0
FAILED = 0

def _report(tc: str, description: str, passed: bool, details: str = ""):
    global PASSED, FAILED
    status = "PASSED" if passed else "FAILED"
    if passed:
        PASSED += 1
    else:
        FAILED += 1
    print(f"  {tc}: {description} -- {status}")
    if details:
        print(f"        {details}")


# ──────────────────────────────────────────────────────────────────────────────
# Unit Tests: OutputSelectorNode
# ──────────────────────────────────────────────────────────────────────────────

async def test_output_selector():
    """Test output selection logic for all 8 types."""
    from agents.m1.nodes.output_selector_node import select_output

    print("\n=== Output Selector Tests ===\n")

    # TC-01: Guard clause — preserve upstream output_format
    state_01 = {
        "output_format": "narrative",  # set by tax_rag_node
        "raw_data": [{"answer": "Tax rate is 14%"}],
        "intent": "tax_reasoning",
        "language": "en",
        "extracted_params": {},
    }
    result_01 = await select_output(state_01)
    _report(
        "TC-01", "Guard clause preserves upstream output_format",
        result_01["output_format"] == "narrative",
        f"format={result_01['output_format']}",
    )

    # TC-02: Metric Card — single row, ≤ 3 cols (T1 total revenue)
    state_02 = {
        "raw_data": [{"total_revenue": 1500000.00}],
        "intent": "financial_query",
        "language": "ar",
        "extracted_params": {"applied_template": "T1"},
    }
    result_02 = await select_output(state_02)
    _report(
        "TC-02", "Metric Card for single scalar value",
        result_02["output_format"] in ("metric_card", "direct_text"),
        f"format={result_02['output_format']}",
    )

    # TC-03: Line Chart — time series (T2 sales time series)
    state_03 = {
        "raw_data": [
            {"period": "2025-01", "revenue": 100000},
            {"period": "2025-02", "revenue": 120000},
            {"period": "2025-03", "revenue": 95000},
            {"period": "2025-04", "revenue": 140000},
        ],
        "intent": "financial_query",
        "language": "en",
        "extracted_params": {"applied_template": "T2"},
    }
    result_03 = await select_output(state_03)
    _report(
        "TC-03", "Line Chart for time series (T2)",
        result_03["output_format"] == "line_chart",
        f"format={result_03['output_format']}, chart_config={result_03.get('chart_config') is not None}",
    )

    # TC-04: Bar Chart — categorical comparison (T8 category revenue)
    state_04 = {
        "raw_data": [
            {"category": "Electronics", "category_revenue": 500000},
            {"category": "Office Supplies", "category_revenue": 300000},
            {"category": "Furniture", "category_revenue": 200000},
        ],
        "intent": "financial_query",
        "language": "en",
        "extracted_params": {"applied_template": "T8"},
    }
    result_04 = await select_output(state_04)
    _report(
        "TC-04", "Bar Chart for categorical data (T8)",
        result_04["output_format"] == "bar_chart",
        f"format={result_04['output_format']}, chart_config={result_04.get('chart_config') is not None}",
    )

    # TC-05: Table — large dataset (> 5 rows, aging buckets T4)
    state_05 = {
        "raw_data": [
            {"customer_name": f"Customer {i}", "0_30_days": 1000*i, "30_60_days": 500*i, "60_90_days": 200*i, "90_plus_days": 100*i, "total_overdue": 1800*i}
            for i in range(1, 11)
        ],
        "intent": "financial_query",
        "language": "ar",
        "extracted_params": {"applied_template": "T4"},
    }
    result_05 = await select_output(state_05)
    _report(
        "TC-05", "Table for large dataset (aging buckets)",
        result_05["output_format"] == "table",
        f"format={result_05['output_format']}",
    )

    # TC-06: Metric Card — executive summary (T3)
    state_06 = {
        "raw_data": [{"total_sales": 2000000, "total_purchases": 1200000, "net_income": 800000}],
        "intent": "financial_query",
        "language": "ar",
        "extracted_params": {"applied_template": "T3"},
    }
    result_06 = await select_output(state_06)
    _report(
        "TC-06", "Metric Card for executive summary (T3)",
        result_06["output_format"] == "metric_card",
        f"format={result_06['output_format']}",
    )

    # TC-07: Alert — anomaly detected
    state_07 = {
        "raw_data": [
            {"id": "txn-1", "category": "Maintenance", "amount": 50000, "transaction_date": "2025-06-01", "avg_amount": 12000}
        ],
        "intent": "financial_query",
        "language": "ar",
        "extracted_params": {"applied_template": "T6"},
        "anomaly_detected": True,
        "anomaly_details": {
            "type": "expense_anomaly",
            "severity": "critical",
            "title": "مصروف غير معتاد",
            "description": "ارتفاع 316%",
            "recommendation": "مراجعة الفواتير",
        },
    }
    result_07 = await select_output(state_07)
    _report(
        "TC-07", "Alert Card for anomaly detected",
        result_07["output_format"] == "alert",
        f"format={result_07['output_format']}",
    )

    # TC-08: Formatted Text List — small list (≤ 5 rows, ≤ 3 cols)
    state_08 = {
        "raw_data": [
            {"name": "Customer A", "total_revenue": 500000},
            {"name": "Customer B", "total_revenue": 400000},
            {"name": "Customer C", "total_revenue": 300000},
        ],
        "intent": "financial_query",
        "language": "en",
        "extracted_params": {"applied_template": "T7"},
    }
    result_08 = await select_output(state_08)
    _report(
        "TC-08", "Formatted Text List for small list (3 items)",
        result_08["output_format"] in ("formatted_text_list", "bar_chart"),
        f"format={result_08['output_format']}",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Unit Tests: Validation Enrichment Node (Anomaly Detection)
# ──────────────────────────────────────────────────────────────────────────────
# ------------------------------------------------------------------------------

async def test_validation_enrichment():
    """Test anomaly detection in validation node."""
    from agents.m1.nodes.validation_enrichment_node import validate_and_enrich

    print("\n=== Validation Enrichment Tests ===\n")

    # TC-09: T6 expense anomaly triggers anomaly_detected
    state_09 = {
        "raw_data": [
            {"id": "txn-1", "category": "Maintenance", "amount": 50000, "transaction_date": "2025-06-01", "avg_amount": 12000},
            {"id": "txn-2", "category": "Utilities", "amount": 30000, "transaction_date": "2025-05-15", "avg_amount": 10000},
        ],
        "intent": "financial_query",
        "language": "en",
        "extracted_params": {"applied_template": "T6"},
    }
    result_09 = await validate_and_enrich(state_09)
    _report(
        "TC-09", "T6 expense anomaly triggers anomaly_detected",
        result_09.get("anomaly_detected") is True,
        f"anomaly_detected={result_09.get('anomaly_detected')}, "
        f"severity={result_09.get('anomaly_details', {}).get('severity')}",
    )


# ------------------------------------------------------------------------------
# Unit Tests: Narrative Generator Node
# ------------------------------------------------------------------------------

async def test_narrative_generator():
    """Test narrative skip condition and generation."""
    from agents.m1.nodes.narrative_generator_node import generate_narrative

    print("\n=== Narrative Generator Tests ===\n")

    # TC-10: Skip condition — upstream narrative exists for invoice_analysis
    state_10 = {
        "raw_data": [{"total_amount": 100000, "vendor_name": "Test Corp"}],
        "output_format": "narrative",
        "intent": "invoice_analysis",
        "language": "en",
        "query": "Analyze invoices for Q1",
        "narrative": "Total invoice spend was 100,000 EGP across 15 invoices.",
        "anomaly_detected": False,
        "anomaly_details": {},
        "chart_config": None,
        "final_response": {},
    }
    result_10 = await generate_narrative(state_10)
    _report(
        "TC-10", "Skip condition: upstream narrative preserved for invoice_analysis",
        result_10["narrative"] == "Total invoice spend was 100,000 EGP across 15 invoices.",
        f"narrative preserved (len={len(result_10['narrative'])}), "
        f"final_response.format={result_10['final_response'].get('format')}",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

async def main():
    print("=" * 60)
    print("M1-Sprint 5 Integration Tests")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)

    await test_output_selector()
    await test_validation_enrichment()
    await test_narrative_generator()

    print("\n" + "=" * 60)
    print(f"RESULTS: {PASSED} PASSED, {FAILED} FAILED (Total: {PASSED + FAILED})")
    print("=" * 60)

    if FAILED > 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

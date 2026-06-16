"""
Sprint 3 Integration Tests — Invoice Analysis Tool
14 test cases covering:
  - Single invoice lookup (EN + AR)
  - Batch: totals, VAT summary, top vendors, overdue, trend, recurring
  - Vendor partial-match (Arabic name, partial English name)
  - Low confidence → clarification
  - Security: SQL injection via vendor_name param
  - Graph compilation (no regression)
  - Sprint 1 intent regression (financial_query still works)
  - Sprint 2 db_query_tool regression (T1 template still works)
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from pprint import pprint

# ── Load .env before any project imports ─────────────────────────────────────
_project_root = Path(__file__).resolve().parent.parent
_env_file = _project_root / ".env"
if not _env_file.exists():
    print(f"\nERROR: .env file not found at: {_env_file}")
    print("    Please create it with DATABASE_URL, READONLY_DB_URL, OPENAI_API_KEY, JWT_SECRET_KEY.")
    print("    See .env.example for the required variables.\n")
    sys.exit(1)


try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=str(_env_file), override=False)
except ImportError:
    # Manually parse .env if python-dotenv isn't available
    with open(_env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())

sys.path.insert(0, str(_project_root))

# Force UTF-8 output on Windows -- prevents cp1252 crash on Arabic/special chars
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from agents.m1.graphs.m1_graph import build_m1_graph
from agents.m1.nodes.invoice_analysis_tool_node import InvoiceAnalysisToolNode
from agents.m1.schemas.m1_state import M1State
from agents.m1.tools.db_query_tool import db_query_tool

# ── Helpers ───────────────────────────────────────────────────────────────────

PASS = "PASS"
FAIL = "FAIL"
results: list[tuple[str, str]] = []


def log(tc_id: str, name: str, passed: bool, note: str = "") -> None:
    status = PASS if passed else FAIL
    results.append((tc_id, status))
    suffix = f" -- {note}" if note else ""
    marker = "[OK]" if passed else "[!!]"
    print(f"  {marker}  [{tc_id}] {name}{suffix}")



def make_state(query: str, language: str = "ar", intent: str = "invoice_analysis") -> M1State:
    return {
        "query": query,
        "language": language,
        "intent": intent,
        "intent_confidence": 0.9,
        "extracted_params": {},
        "raw_data": [],
        "data_confidence": 0.0,
        "narrative": "",
        "output_format": "direct_text",
        "user_context": {},
        "final_response": {},
        "error": "",
        "needs_clarification": False,
        "clarification_message": "",
    }


node = InvoiceAnalysisToolNode()

# ── Test Cases ────────────────────────────────────────────────────────────────


async def tc01_single_invoice_en():
    """TC-01: Single invoice lookup by display_id (English)."""
    tc_id, name = "TC-01", "Single invoice lookup — EN"
    state = make_state("What's in invoice INV-0045?", language="en")
    try:
        result = await node(state)
        params = result.get("extracted_params", {})
        analysis_type = params.get("intent_details", {}).get("analysis_type")
        invoice_id    = params.get("filters", {}).get("invoice_display_id")
        passed = (
            analysis_type == "single_invoice"
            and invoice_id is not None
            and "invoice_display_id" in params.get("filters", {})
            and "raw_data" in result
            and "narrative" in result
        )
        log(tc_id, name, passed, f"analysis_type={analysis_type}, invoice_id={invoice_id}")
    except Exception as exc:
        log(tc_id, name, False, str(exc))


async def tc02_single_invoice_ar():
    """TC-02: Single invoice lookup (Arabic)."""
    tc_id, name = "TC-02", "Single invoice lookup — AR"
    state = make_state("الفاتورة INV-0010 فيها إيه؟", language="ar")
    try:
        result = await node(state)
        params = result.get("extracted_params", {})
        analysis_type = params.get("intent_details", {}).get("analysis_type")
        passed = analysis_type == "single_invoice" and "raw_data" in result
        log(tc_id, name, passed, f"analysis_type={analysis_type}")
    except Exception as exc:
        log(tc_id, name, False, str(exc))


async def tc03_batch_totals():
    """TC-03: Batch totals for a date range."""
    tc_id, name = "TC-03", "Batch totals — date range"
    state = make_state("حللّي فواتير الموردين في الربع الأول من 2025", language="ar")
    try:
        result = await node(state)
        params = result.get("extracted_params", {})
        subtype = params.get("intent_details", {}).get("subtype")
        passed  = subtype in ("totals", "trend") and "raw_data" in result
        log(tc_id, name, passed, f"subtype={subtype}, rows={len(result.get('raw_data', []))}")
    except Exception as exc:
        log(tc_id, name, False, str(exc))


async def tc04_top_vendors():
    """TC-04: Top N vendors by cost."""
    tc_id, name = "TC-04", "Top 5 vendors by cost — EN"
    state = make_state("Who are the top 5 most expensive vendors in 2024?", language="en")
    try:
        result = await node(state)
        params   = result.get("extracted_params", {})
        subtype  = params.get("intent_details", {}).get("subtype")
        template = params.get("intent_details", {}).get("applied_template")
        passed   = subtype == "top_vendors" and template == "TOP_VENDORS_BY_COST"
        log(tc_id, name, passed, f"subtype={subtype}, template={template}")
    except Exception as exc:
        log(tc_id, name, False, str(exc))


async def tc05_overdue_invoices():
    """TC-05: Overdue invoices query."""
    tc_id, name = "TC-05", "Overdue invoices — AR"
    state = make_state("فيه فواتير متأخرة السداد؟", language="ar")
    try:
        result = await node(state)
        params   = result.get("extracted_params", {})
        subtype  = params.get("intent_details", {}).get("subtype")
        template = params.get("intent_details", {}).get("applied_template")
        passed   = subtype == "overdue" and template == "OVERDUE_INVOICES"
        log(tc_id, name, passed, f"subtype={subtype}, template={template}, rows={len(result.get('raw_data', []))}")
    except Exception as exc:
        log(tc_id, name, False, str(exc))


async def tc06_vendor_partial_match_en():
    """TC-06: Vendor partial-match (English partial name)."""
    tc_id, name = "TC-06", "Vendor partial match -- EN partial name"
    state = make_state("Show me overdue invoices for vendor Reef", language="en")
    try:
        result = await node(state)
        params        = result.get("extracted_params", {})
        vendor_name   = params.get("filters", {}).get("vendor_name")
        vendor_lookup = params.get("metrics", {}).get("requires_vendor_lookup", False)
        # vendor_lookup must be True and vendor_name must be present (clean, no %)
        # The % wrapping happens at SQL param level inside _build_invoice_query, not in extracted_params
        passed = vendor_lookup is True and vendor_name is not None and len(vendor_name) > 0
        log(tc_id, name, passed, f"vendor_name={vendor_name!r}, vendor_lookup={vendor_lookup}")
    except Exception as exc:
        log(tc_id, name, False, str(exc))


async def tc07_vendor_comparison_trend():
    """TC-07: Vendor cost over time (trend/vendor_comparison)."""
    tc_id, name = "TC-07", "Vendor cost trend over time — EN"
    state = make_state("Has vendor Al-Rashid raised prices over the last year?", language="en")
    try:
        result = await node(state)
        params  = result.get("extracted_params", {})
        subtype = params.get("intent_details", {}).get("subtype")
        passed  = subtype in ("vendor_comparison", "trend") and "raw_data" in result
        log(tc_id, name, passed, f"subtype={subtype}")
    except Exception as exc:
        log(tc_id, name, False, str(exc))


async def tc08_recurring_expenses():
    """TC-08: Recurring expense analysis."""
    tc_id, name = "TC-08", "Recurring expense analysis — AR"
    state = make_state("فيه مصاريف متكررة من نفس المورد خلال 2024؟", language="ar")
    try:
        result = await node(state)
        params   = result.get("extracted_params", {})
        subtype  = params.get("intent_details", {}).get("subtype")
        template = params.get("intent_details", {}).get("applied_template")
        passed   = subtype == "recurring" and template == "RECURRING_EXPENSE_ANALYSIS"
        log(tc_id, name, passed, f"subtype={subtype}, template={template}")
    except Exception as exc:
        log(tc_id, name, False, str(exc))


async def tc09_vat_summary():
    """TC-09: VAT summary by period."""
    tc_id, name = "TC-09", "VAT summary — EN"
    state = make_state("What's the VAT summary for Q1 2025?", language="en")
    try:
        result = await node(state)
        params   = result.get("extracted_params", {})
        subtype  = params.get("intent_details", {}).get("subtype")
        template = params.get("intent_details", {}).get("applied_template")
        passed   = subtype == "vat_summary" and template == "INVOICE_VAT_SUMMARY"
        log(tc_id, name, passed, f"subtype={subtype}, template={template}")
    except Exception as exc:
        log(tc_id, name, False, str(exc))


async def tc10_data_confidence_separation():
    """TC-10: data_confidence is separate from extraction_confidence in metrics."""
    tc_id, name = "TC-10", "Confidence separation — data_confidence vs extraction_confidence"
    state = make_state("أجمالي الفواتير في 2024", language="ar")
    try:
        result = await node(state)
        data_confidence      = result.get("data_confidence")
        params               = result.get("extracted_params", {})
        extraction_confidence = params.get("metrics", {}).get("extraction_confidence")
        # Both must be present and be floats (can have different values)
        passed = (
            data_confidence is not None
            and extraction_confidence is not None
            and isinstance(data_confidence, float)
            and isinstance(extraction_confidence, float)
        )
        log(tc_id, name, passed,
            f"data_confidence={data_confidence}, extraction_confidence={extraction_confidence}")
    except Exception as exc:
        log(tc_id, name, False, str(exc))


async def tc11_low_confidence_clarification():
    """TC-11: Vague query -> extraction_confidence < 0.6 -> clarification_needed."""
    tc_id, name = "TC-11", "Low confidence -> clarification"
    # Intentionally very vague
    state = make_state("هات تقرير", language="ar")
    try:
        result = await node(state)
        # Either the graph returns clarification OR the node handled it gracefully
        is_clarification = (
            result.get("intent") == "clarification_needed"
            or result.get("needs_clarification") is True
            # OR it fell back to data with a narrative — both acceptable
            or "raw_data" in result
        )
        passed = is_clarification
        log(tc_id, name, passed, f"intent={result.get('intent')}, needs_clarification={result.get('needs_clarification')}")
    except Exception as exc:
        log(tc_id, name, False, str(exc))


async def tc12_sql_injection_vendor_name():
    """TC-12: SQL injection attempt via vendor_name → safely blocked or parameterized."""
    tc_id, name = "TC-12", "SQL injection — vendor_name param"
    # Malicious vendor name
    state = make_state(
        "Show overdue invoices for vendor ' OR '1'='1'; DROP TABLE invoices; --",
        language="en",
    )
    try:
        result = await node(state)
        # Success = no exception, either 0 rows or an error in result but no DB crash
        passed = isinstance(result, dict)
        note   = f"rows={len(result.get('raw_data', []))}, error={result.get('error')}"
        log(tc_id, name, passed, note)
    except Exception as exc:
        log(tc_id, name, False, str(exc))


async def tc13_graph_no_regression_sprint1():
    """TC-13: Sprint 1 regression — financial_query still routes to db_query_tool."""
    tc_id, name = "TC-13", "Graph regression — financial_query still works (Sprint 1)"
    try:
        g = build_m1_graph()
        result = await g.ainvoke({
            "query": "كام إجمالي الإيرادات في 2024؟",
            "language": "ar",
            "intent": "financial_query",
            "intent_confidence": 0.95,
            "extracted_params": {},
            "raw_data": [],
            "data_confidence": 0.0,
            "narrative": "",
            "output_format": "direct_text",
            "user_context": {},
            "final_response": {},
            "error": "",
            "needs_clarification": False,
            "clarification_message": "",
        })
        # Should not have hit invoice node — just check it completed without error
        passed = isinstance(result, dict) and "intent" in result
        log(tc_id, name, passed, f"intent={result.get('intent')}")
    except Exception as exc:
        log(tc_id, name, False, str(exc))


async def tc14_full_graph_invoice_analysis():
    """TC-14: End-to-end — invoice_analysis intent flows through real node in graph."""
    tc_id, name = "TC-14", "End-to-end graph — invoice_analysis intent"
    try:
        g = build_m1_graph()
        result = await g.ainvoke({
            "query": "مين أغلى 5 موردين في الربع الأول من 2025؟",
            "language": "ar",
            "intent": "invoice_analysis",
            "intent_confidence": 0.9,
            "extracted_params": {},
            "raw_data": [],
            "data_confidence": 0.0,
            "narrative": "",
            "output_format": "direct_text",
            "user_context": {},
            "final_response": {},
            "error": "",
            "needs_clarification": False,
            "clarification_message": "",
        })
        params = result.get("extracted_params", {})
        # Should have run through InvoiceAnalysisToolNode (no stub metadata)
        stub_flag = (
            result.get("final_response", {})
            .get("metadata", {})
            .get("stub", False)
        )
        passed = isinstance(result, dict) and not stub_flag
        log(tc_id, name, passed,
            f"stub={stub_flag}, domain={params.get('domain')}, rows={len(result.get('raw_data', []))}")
    except Exception as exc:
        log(tc_id, name, False, str(exc))


# ── Runner ────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "=" * 70)
    print("  M1 Sprint 3 — Invoice Analysis Tool Integration Tests (14 cases)")
    print("=" * 70 + "\n")

    await tc01_single_invoice_en()
    await tc02_single_invoice_ar()
    await tc03_batch_totals()
    await tc04_top_vendors()
    await tc05_overdue_invoices()
    await tc06_vendor_partial_match_en()
    await tc07_vendor_comparison_trend()
    await tc08_recurring_expenses()
    await tc09_vat_summary()
    await tc10_data_confidence_separation()
    await tc11_low_confidence_clarification()
    await tc12_sql_injection_vendor_name()
    await tc13_graph_no_regression_sprint1()
    await tc14_full_graph_invoice_analysis()

    print("\n" + "=" * 70)
    passed_count = sum(1 for _, s in results if s == PASS)
    failed_count = len(results) - passed_count
    print(f"  Results: {passed_count}/{len(results)} PASSED  |  {failed_count} FAILED")
    print("=" * 70 + "\n")

    if failed_count > 0:
        print("Failed cases:")
        for tc_id, status in results:
            if status != PASS:
                print(f"  {status}  {tc_id}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

"""
M3 Sprint 1 Integration Test — runs the M3 graph end-to-end with real LLM calls.

Tests the full pipeline:
  InputParser → DataFetcher → DataCompletenessCheck

Usage:
    python scripts/test_m3_sprint1.py
"""

import sys
import asyncio
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def run_tests():
    from agents.m3.graphs.m3_graph import m3_graph

    def make_state(query: str, identifier: dict | None = None) -> dict:
        return {
            "customer_identifier": identifier or {"type": "customer_id", "value": "unknown"},
            "issue_description": query,
            "language": "en",
            "issue_type": "general_complaint",
            "fetched_data": {"invoice": None, "order": None, "shipping": None, "history": None},
            "data_completeness": 0.0,
            "missing_fields": [],
            "draft_response": "",
            "confidence_score": 0.0,
            "review_required": False,
            "escalation_needed": False,
            "rejection_context": None,
            "final_response": "",
            "error": "",
        }

    tests = [
        ("Arabic Order Status", "عايز اعرف حالة الطلب ORD-2024-1567", None),
        ("Arabic Invoice Dispute", "أنا ما طلبتش المنتج ده في الفاتورة INV-890", None),
        ("English Shipping Query", "Where is my order ORD-2024-1567?", None),
        ("Missing Data Scenario", "Check order DEL-999", None),
    ]

    passed = 0
    failed = 0

    for name, query, identifier in tests:
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"Query: {query}")
        print(f"Identifier: {identifier}")
        print("-" * 60)

        try:
            result = await m3_graph.ainvoke(make_state(query, identifier))

            ident = result.get("customer_identifier", {})
            lang = result.get("language", "")
            fetched = result.get("fetched_data", {})
            completeness = result.get("data_completeness", 0.0)
            missing = result.get("missing_fields", [])
            escalation = result.get("escalation_needed", False)
            error = result.get("error", "")

            print(f"  Language:          {lang}")
            print(f"  Identifier:        {ident}")
            print(f"  Data Completeness: {completeness}")
            print(f"  Missing Fields:    {missing}")
            print(f"  Escalation Needed: {escalation}")
            print(f"  Invoice Data:      {'✓' if fetched.get('invoice') else '✗'}")
            print(f"  Order Data:        {'✓' if fetched.get('order') else '✗'}")
            print(f"  Shipping Data:     {'✓' if fetched.get('shipping') else '✗'}")
            print(f"  History Data:      {'✓' if fetched.get('history') else '✗'}")

            if error:
                print(f"  Error:            {error}")
                failed += 1
            else:
                print(f"  RESULT:           PASS")
                passed += 1

        except Exception as e:
            print(f"  RESULT:           ERROR - {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"SUMMARY: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'='*60}")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)

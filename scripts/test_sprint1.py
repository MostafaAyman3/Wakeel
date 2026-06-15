"""
Sprint 1 Integration Test — runs the M1 graph end-to-end with real LLM calls.

Usage:
    python scripts/test_sprint1.py
"""

import sys
import asyncio
import json

sys.path.insert(0, ".")


async def run_tests():
    from agents.m1.graphs.m1_graph import m1_graph

    def make_state(query: str, language: str = "auto") -> dict:
        return {
            "query": query,
            "language": language,
            "intent": "",
            "intent_confidence": 0.0,
            "extracted_params": {},
            "raw_data": [],
            "data_confidence": 0.0,
            "output_format": "direct_text",
            "narrative": "",
            "final_response": {},
            "error": "",
            "needs_clarification": False,
            "clarification_message": "",
            "user_context": {
                "user_id": "test-user-123",
                "role": "user",
                "permissions": ["read"],
            },
        }

    tests = [
        ("Arabic Financial Query", "كام إجمالي المبيعات الشهر ده؟", "financial_query"),
        ("English Invoice Query", "Analyze vendor invoices for Q1 2025", "invoice_analysis"),
        ("Arabic Tax Query", "فاتورتي بـ 50,000 جنيه، القيمة المضافة إيه؟", "tax_reasoning"),
        ("English Operational Query", "How many orders were delivered this month?", "operational_query"),
        ("Ambiguous Arabic Query", "عايز تقرير", "clarification_needed"),
        ("Ambiguous English Query", "Show me something", "clarification_needed"),
    ]

    passed = 0
    failed = 0

    for name, query, expected_intent in tests:
        print(f"\n{'='*60}")
        print(f"TEST: {name}")
        print(f"Query: {query}")
        print(f"Expected intent: {expected_intent}")
        print("-" * 60)

        try:
            result = await m1_graph.ainvoke(make_state(query))

            actual_intent = result.get("intent", "")
            confidence = result.get("intent_confidence", 0.0)
            language = result.get("language", "")
            params = result.get("extracted_params", {})
            needs_clarification = result.get("needs_clarification", False)
            final_response = result.get("final_response", {})
            is_stub = final_response.get("metadata", {}).get("stub", False)
            error = result.get("error", "")

            print(f"  Language:    {language}")
            print(f"  Intent:      {actual_intent}")
            print(f"  Confidence:  {confidence}")
            print(f"  Params:      {json.dumps(params, ensure_ascii=False, indent=2)}")
            print(f"  Stub:        {is_stub}")
            print(f"  Clarification: {needs_clarification}")
            if needs_clarification:
                msg = result.get("clarification_message", "")
                print(f"  Message:     {msg[:150]}...")
            if error:
                print(f"  Error:       {error}")

            if actual_intent == expected_intent:
                print(f"  RESULT:      PASS")
                passed += 1
            else:
                print(f"  RESULT:      FAIL (expected {expected_intent}, got {actual_intent})")
                failed += 1

        except Exception as e:
            print(f"  RESULT:      ERROR - {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"SUMMARY: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'='*60}")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)

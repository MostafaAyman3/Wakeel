"""
M3 Sprint 1 Integration Test — runs the support graph end-to-end.

Exercises: InputParser → DataFetcher (real Supabase) → DataCompletenessCheck.
Makes real LLM calls (GPT-4o-mini) and real DB queries.

Usage:
    python scripts/test_m3_sprint1.py

Note: the demo identifiers below must exist in the seeded DB. Adjust the
values to match real display_ids if your seed differs (see
docs/architecture/db_schema_reference.md). The "missing data" case is
intentionally a non-existent reference.
"""

import sys
import asyncio
import json

sys.path.insert(0, ".")

# Windows consoles default to cp1252, which cannot encode Arabic output.
# Force UTF-8 so the bilingual test output prints correctly.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001 — older/odd stdout objects
    pass


async def run_tests() -> bool:
    from agents.m3.graphs.m3_graph import support_graph
    from agents.m3.schemas.m3_state import build_initial_state
    from agents.m3.nodes.data_completeness_node import get_confidence_label

    # (name, query, identifier|None, expectation)
    #   expectation: "found" → at least one source; "none" → escalate.
    tests = [
        (
            "AR order status — identifier in text",
            "فين الأوردر بتاعي ORD-2024-1567؟",
            None,
            "found",
        ),
        (
            "EN invoice dispute — explicit identifier",
            "I did not order this, the invoice is wrong",
            {"type": "invoice_id", "value": "INV-0001"},
            "found",
        ),
        (
            "AR repeat issue — customer history",
            "أنا عميل قديم وعندي مشكلة متكررة في التوصيل",
            {"type": "customer_id", "value": "CUST-001"},
            "found",
        ),
        (
            "Missing data — non-existent reference (graceful degradation)",
            "مشكلة في التوصيلة رقم DEL-999",
            None,
            "none",
        ),
        (
            "No identifier at all — must escalate",
            "عايز أعرف حالة طلبي من فضلك",
            None,
            "none",
        ),
    ]

    passed = failed = 0

    for name, query, identifier, expectation in tests:
        print(f"\n{'=' * 64}\nTEST: {name}\nQuery: {query}\nIdentifier: {identifier}")
        print("-" * 64)
        try:
            state = build_initial_state(query=query, identifier=identifier)
            result = await support_graph.ainvoke(state)

            fetched = result.get("fetched_data") or {}
            found = [k for k, v in fetched.items() if v]
            completeness = result.get("data_completeness", 0.0)
            confidence = result.get("confidence_score", 0.0)
            escalation = result.get("escalation_needed", False)

            print(f"  Language:        {result.get('language')}")
            print(f"  Identifier:      {result.get('customer_identifier')}")
            print(f"  Issue desc:      {result.get('issue_description')}")
            print(f"  Sources found:   {found}")
            print(f"  Missing fields:  {result.get('missing_fields')}")
            print(f"  Completeness:    {completeness}")
            print(f"  Confidence:      {confidence} ({get_confidence_label(confidence)})")
            print(f"  Escalation:      {escalation}")
            if fetched.get("invoice"):
                print(f"  Invoice sample:  {json.dumps(fetched['invoice'], ensure_ascii=False)}")

            if expectation == "found":
                ok = len(found) > 0
            else:  # "none"
                ok = escalation is True and len(found) == 0

            if ok:
                print("  RESULT:          PASS")
                passed += 1
            else:
                print(f"  RESULT:          FAIL (expected {expectation})")
                failed += 1

        except Exception as exc:  # noqa: BLE001
            print(f"  RESULT:          ERROR - {exc}")
            failed += 1

    print(f"\n{'=' * 64}\nSUMMARY: {passed} passed, {failed} failed, {len(tests)} total\n{'=' * 64}")
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)

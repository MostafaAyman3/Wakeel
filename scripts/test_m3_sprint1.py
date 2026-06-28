"""
M3 Sprint 1 Integration Test — runs the support graph end-to-end.

Exercises: InputParser -> DataFetcher (real Supabase) -> DataCompletenessCheck.
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

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


async def run_tests() -> bool:
    from agents.m3.graphs.m3_graph import support_graph
    from agents.m3.schemas.m3_state import build_initial_state
    from agents.m3.nodes.data_completeness_node import get_confidence_label

    tests = [
        (
            "AR order status — identifier in text",
            "\u0641\u064a\u0646 \u0627\u0644\u0623\u0648\u0631\u062f\u0631 "
            "\u0628\u062a\u0627\u0639\u064a ORD-2024-1567\u061f",
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
            "\u0623\u0646\u0627 \u0639\u0645\u064a\u0644 \u0642\u062f\u064a\u0645 "
            "\u0648\u0639\u0646\u062f\u064a \u0645\u0634\u0643\u0644\u0629 "
            "\u0645\u062a\u0643\u0631\u0631\u0629 \u0641\u064a \u0627\u0644\u062a\u0648\u0635\u064a\u0644",
            {"type": "customer_id", "value": "CUST-001"},
            "found",
        ),
        (
            "Missing data — non-existent reference (graceful degradation)",
            "\u0645\u0634\u0643\u0644\u0629 \u0641\u064a \u0627\u0644\u062a\u0648\u0635\u064a\u0644\u0629 "
            "\u0631\u0642\u0645 DEL-999",
            None,
            "none",
        ),
        (
            "Non-existent reference -- must escalate",
            "what is the status of DEL-999?",
            {"type": "order_id", "value": "DEL-999"},
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
            # Sprint 2 outputs
            print(f"  Issue type:      {result.get('issue_type')}")
            print(f"  Issue priority:  {result.get('issue_priority')}")
            print(f"  Context exists:  {bool(result.get('context'))}")
            if result.get("context"):
                ctx = result["context"]
                print(f"  Context keys:    {list(ctx.keys())}")
            if fetched.get("invoice"):
                print(f"  Invoice sample:  {json.dumps(fetched['invoice'], ensure_ascii=False)}")

            if expectation == "found":
                ok = len(found) > 0
                # Sprint 2: classifier and context should have run
                if ok:
                    ok = result.get("issue_type") is not None
                    ok = ok and result.get("issue_priority") in ("High", "Medium", "Low")
                    ok = ok and bool(result.get("context"))
            else:
                ok = escalation is True and len(found) == 0
                # Sprint 2: classifier/context skipped when escalated
                if ok:
                    ok = result.get("issue_type") is None
                    ok = ok and result.get("context") == {}

            if ok:
                print("  RESULT:          PASS")
                passed += 1
            else:
                print(f"  RESULT:          FAIL (expected {expectation})")
                failed += 1

        except Exception as exc:
            print(f"  RESULT:          ERROR - {exc}")
            failed += 1

    print(f"\n{'=' * 64}\nSUMMARY: {passed} passed, {failed} failed, {len(tests)} total\n{'=' * 64}")
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)

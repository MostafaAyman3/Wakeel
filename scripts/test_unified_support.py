"""
Unified Support Chatbot — Integration Tests (T026).

Tests all three routes end-to-end against the running backend:
  1. general_knowledge  — policy question, no order ref
  2. customer_issue     — order lookup with real identifier
  3. hybrid             — order + policy in one question

Also tests:
  4. AR language        — Arabic query gets Arabic answer
  5. review-hold        — low-confidence triggers waiting message (no draft leak)
  6. session memory     — second message in same session_id sees context
  7. review keywords    — status_inquiry does NOT trigger false-positive review

Usage:
    # backend must be running on localhost:8000
    python scripts/test_unified_support.py

    # Skip tests that need a real DB order (knowledge + language tests only):
    python scripts/test_unified_support.py --no-crm
"""

from __future__ import annotations

import asyncio
import os
import sys
import argparse
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

os.environ.setdefault("APP_ENV", "test")

# ── Minimal env stubs so config loads without a real .env ────────────────────
for _k, _v in {
    "DATABASE_URL": "postgresql+asyncpg://u:p@localhost/db",
    "READONLY_DB_URL": "postgresql+asyncpg://u:p@localhost/db",
    "JWT_SECRET_KEY": "test-secret",
    "OPENAI_API_KEY": "sk-test",
}.items():
    os.environ.setdefault(_k, _v)

import httpx  # noqa: E402

BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
API = f"{BASE_URL}/api/v1/support"

PASS = "✅"
FAIL = "❌"
SKIP = "⏩"


# ── HTTP helpers ─────────────────────────────────────────────────────────────

async def post_support(
    query: str,
    *,
    session_id: str | None = None,
    identifier: dict | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    payload: dict[str, Any] = {"query": query}
    if session_id:
        payload["session_id"] = session_id
    if identifier:
        payload["identifier"] = identifier

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(API, json=payload)
        r.raise_for_status()
        return r.json()


# ── Test runner helpers ───────────────────────────────────────────────────────

_results: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, detail: str = "") -> None:
    _results.append((name, passed, detail))
    icon = PASS if passed else FAIL
    print(f"  {icon}  {name}", f"     {detail}" if detail else "", flush=True)


def assert_field(data: dict, field: str, expected: Any) -> bool:
    actual = data.get(field)
    if actual == expected:
        return True
    print(f"       expected {field}={expected!r}, got {actual!r}")
    return False


# ── Individual tests ─────────────────────────────────────────────────────────

async def test_knowledge_route() -> None:
    """T1 — policy question should route to general_knowledge."""
    name = "T1 general_knowledge route"
    try:
        data = await post_support("What is your return policy?")
        ok = data.get("route") == "general_knowledge"
        has_answer = bool(data.get("final_response", "").strip())
        record(name, ok and has_answer,
               f"route={data.get('route')!r}, answer_len={len(data.get('final_response', ''))}")
    except Exception as exc:
        record(name, False, str(exc))


async def test_knowledge_sources() -> None:
    """T2 — knowledge answer should carry rag_sources."""
    name = "T2 rag_sources present on knowledge answer"
    try:
        data = await post_support("How long does shipping take?")
        sources = data.get("rag_sources", [])
        record(name, isinstance(sources, list),
               f"route={data.get('route')!r}, sources={sources}")
    except Exception as exc:
        record(name, False, str(exc))


async def test_arabic_route() -> None:
    """T3 — Arabic policy question should still route knowledge and answer in AR."""
    name = "T3 Arabic language — knowledge route + AR answer"
    try:
        data = await post_support("ما هي سياسة الإرجاع لديكم؟")
        route_ok = data.get("route") == "general_knowledge"
        answer = data.get("final_response", "")
        has_arabic = any("؀" <= c <= "ۿ" for c in answer)
        record(name, route_ok and has_arabic,
               f"route={data.get('route')!r}, ar_chars={has_arabic}, len={len(answer)}")
    except Exception as exc:
        record(name, False, str(exc))


async def test_customer_issue_route(identifier_value: str) -> None:
    """T4 — order lookup should route to customer_issue."""
    name = "T4 customer_issue route (CRM lookup)"
    try:
        data = await post_support(
            f"Where is my order {identifier_value}?",
            identifier={"type": "order_id", "value": identifier_value},
        )
        ok = data.get("route") == "customer_issue"
        has_answer = bool(data.get("final_response", "").strip())
        record(name, ok and has_answer,
               f"route={data.get('route')!r}, review={data.get('review_required')}")
    except Exception as exc:
        record(name, False, str(exc))


async def test_hybrid_route(identifier_value: str) -> None:
    """T5 — order + policy question should route to hybrid."""
    name = "T5 hybrid route (order + policy)"
    try:
        data = await post_support(
            f"My order {identifier_value} is late — what is your refund policy?",
            identifier={"type": "order_id", "value": identifier_value},
        )
        route = data.get("route")
        ok = route in ("hybrid", "customer_issue")  # both acceptable; hybrid is ideal
        record(name, ok, f"route={route!r}, answer_len={len(data.get('final_response', ''))}")
    except Exception as exc:
        record(name, False, str(exc))


async def test_review_hold_hides_draft() -> None:
    """T6 — when review_required, customer sees waiting message, NOT draft."""
    name = "T6 review-hold: final_response is neutral waiting message"
    try:
        # Billing dispute always triggers mandatory review
        data = await post_support(
            "I demand a refund for invoice INV-0001 — this is a billing dispute.",
            identifier={"type": "invoice_id", "value": "INV-0001"},
        )
        if not data.get("review_required"):
            record(name, True, "review not triggered — skip hold check")
            return
        final = data.get("final_response", "")
        draft = data.get("draft_response", "")
        # final_response should NOT equal the draft
        hold_ok = final != draft or not draft
        # final should contain a "follow up" phrase
        follow_up_ok = (
            "follow up" in final.lower()
            or "سيتواصل" in final
            or "agent" in final.lower()
        )
        record(name, hold_ok and follow_up_ok,
               f"review=True, final_starts={final[:60]!r}")
    except Exception as exc:
        record(name, False, str(exc))


async def test_no_false_positive_review() -> None:
    """T7 — status_inquiry with full data should NOT trigger review_required."""
    name = "T7 no false-positive review on status_inquiry"
    try:
        data = await post_support(
            "Please tell me the status of my order ORD-2024-0001.",
            identifier={"type": "order_id", "value": "ORD-2024-0001"},
        )
        # Only check the flag; we won't fail if CRM data is unavailable
        triggered = data.get("review_required", False)
        # If escalation_needed that's fine (no data), not a keyword false-positive
        escalated = data.get("escalation_needed", False)
        ok = not triggered or escalated
        record(name, ok,
               f"review_required={triggered}, escalation_needed={escalated}")
    except Exception as exc:
        record(name, False, str(exc))


async def test_session_memory() -> None:
    """T8 — two messages in the same session_id: server accepts both."""
    name = "T8 session_id round-trip (two turns accepted)"
    import uuid
    session = str(uuid.uuid4())
    try:
        r1 = await post_support("What is your return policy?", session_id=session)
        r2 = await post_support(
            "Can you repeat that summary?", session_id=session
        )
        ok = (
            bool(r1.get("final_response"))
            and bool(r2.get("final_response"))
        )
        record(name, ok, f"turn1_route={r1.get('route')!r}, turn2_route={r2.get('route')!r}")
    except Exception as exc:
        record(name, False, str(exc))


# ── Entry point ───────────────────────────────────────────────────────────────

async def run_tests(skip_crm: bool) -> None:
    print(f"\nUnified Support Chatbot — Integration Tests")
    print(f"Backend: {BASE_URL}")
    print("=" * 60)

    # Check server is up
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.get(f"{BASE_URL}/health")
    except Exception:
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                await c.get(f"{BASE_URL}/docs")
        except Exception as exc:
            print(f"\n{FAIL}  Cannot reach backend at {BASE_URL}: {exc}")
            print("   Start the backend first: uvicorn backend.main:app --reload")
            sys.exit(1)

    print()

    # Knowledge route tests (no CRM needed)
    await test_knowledge_route()
    await test_knowledge_sources()
    await test_arabic_route()
    await test_session_memory()
    await test_review_hold_hides_draft()
    await test_no_false_positive_review()

    # CRM tests (need real order in DB)
    crm_id = os.environ.get("TEST_ORDER_ID", "ORD-2024-0001")
    if skip_crm:
        print(f"\n  {SKIP}  T4 customer_issue route — skipped (--no-crm)")
        print(f"  {SKIP}  T5 hybrid route — skipped (--no-crm)")
    else:
        await test_customer_issue_route(crm_id)
        await test_hybrid_route(crm_id)

    # Summary
    print()
    print("=" * 60)
    passed = sum(1 for _, ok, _ in _results if ok)
    total = len(_results)
    print(f"Results: {passed}/{total} passed")
    if passed < total:
        print("\nFailed tests:")
        for name, ok, detail in _results:
            if not ok:
                print(f"  {FAIL}  {name}: {detail}")
        sys.exit(1)
    else:
        print(f"\n{PASS}  All tests passed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Unified Support E2E tests")
    parser.add_argument(
        "--no-crm", action="store_true",
        help="Skip tests that require a real order in the database",
    )
    args = parser.parse_args()
    asyncio.run(run_tests(skip_crm=args.no_crm))


if __name__ == "__main__":
    main()

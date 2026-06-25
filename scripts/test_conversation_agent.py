"""
Conversation Agent (greeting route) — integration tests.

The greeting route needs only the backend + OpenAI (no Mini-RAG, no Postgres),
so greeting assertions run even when the DB/RAG are unavailable. Knowledge/issue
checks are best-effort regression checks (they may need RAG/DB to fully answer,
but the ROUTE classification is what we assert).

Usage:
    # backend must be running on :8000
    python scripts/test_conversation_agent.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import httpx

BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
API = f"{BASE_URL}/api/v1/support"

PASS, FAIL = "[OK]", "[FAIL]"
_results: list[tuple[str, bool, str]] = []


def post(query: str) -> dict:
    with httpx.Client(timeout=90) as c:
        r = c.post(API, json={"query": query})
        r.raise_for_status()
        return r.json()


def record(name: str, ok: bool, detail: str = "") -> None:
    _results.append((name, ok, detail))
    print(f"  {PASS if ok else FAIL}  {name}    {detail}", flush=True)


def has_arabic(text: str) -> bool:
    return any("؀" <= c <= "ۿ" for c in text)


def test_greeting_en() -> None:
    try:
        d = post("Hi")
        ok = (
            d.get("route") == "greeting"
            and bool(d.get("final_response", "").strip())
            and not d.get("review_required")
            and not d.get("escalation_needed")
            and d.get("rag_sources") == []
        )
        record("greeting EN ('Hi')", ok,
               f"route={d.get('route')}, review={d.get('review_required')}")
    except Exception as e:
        record("greeting EN ('Hi')", False, str(e))


def test_greeting_ar() -> None:
    try:
        d = post("السلام عليكم، كيف حالك؟")
        ok = d.get("route") == "greeting" and has_arabic(d.get("final_response", ""))
        record("greeting AR", ok,
               f"route={d.get('route')}, ar_reply={has_arabic(d.get('final_response',''))}")
    except Exception as e:
        record("greeting AR", False, str(e))


def test_thanks() -> None:
    try:
        d = post("thank you so much!")
        record("thanks -> greeting", d.get("route") == "greeting",
               f"route={d.get('route')}")
    except Exception as e:
        record("thanks -> greeting", False, str(e))


def test_knowledge_not_greeting() -> None:
    try:
        d = post("What is your return policy?")
        record("knowledge route (not greeting)",
               d.get("route") == "general_knowledge", f"route={d.get('route')}")
    except Exception as e:
        record("knowledge route (not greeting)", False, str(e))


def test_mixed_greeting_question() -> None:
    try:
        d = post("Hi, what is your return policy?")
        record("mixed greeting+question -> knowledge",
               d.get("route") == "general_knowledge", f"route={d.get('route')}")
    except Exception as e:
        record("mixed greeting+question -> knowledge", False, str(e))


def test_issue_not_greeting() -> None:
    try:
        d = post("Where is my order ORD-2024-0001?")
        record("issue route (not greeting)",
               d.get("route") in ("customer_issue", "hybrid"), f"route={d.get('route')}")
    except Exception as e:
        record("issue route (not greeting)", False, str(e))


def main() -> None:
    print(f"\nConversation Agent tests — backend {BASE_URL}")
    print("=" * 56)
    try:
        httpx.get(f"{BASE_URL}/docs", timeout=5)
    except Exception as exc:
        print(f"{FAIL} backend unreachable: {exc}")
        sys.exit(1)

    test_greeting_en()
    test_greeting_ar()
    test_thanks()
    test_knowledge_not_greeting()
    test_mixed_greeting_question()
    test_issue_not_greeting()

    print("=" * 56)
    passed = sum(1 for _, ok, _ in _results if ok)
    print(f"Results: {passed}/{len(_results)} passed")
    sys.exit(0 if passed == len(_results) else 1)


if __name__ == "__main__":
    main()

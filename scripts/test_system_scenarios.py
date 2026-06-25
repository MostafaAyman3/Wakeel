"""
End-to-end scenario tests for the Wakeel Unified Support Chatbot.

Drives the realistic conversations in docs/testing/user_scenarios.md against the
live backend (POST /api/v1/support) and checks, per turn:
  - route classification
  - reply language (mirrors customer)
  - presence/absence of KB sources
  - review_required (held draft)
  - escalation_needed

Each check is recorded with a severity so the analysis can separate
ROUTE/behaviour correctness (code) from grounding gaps (environment: migration/DB).

Outputs:
  - console report
  - docs/testing/scenario_results.json  (machine-readable, for the analysis)

Usage:
    # backend must be running on :8000 (Mini-RAG :8001 for knowledge grounding)
    python scripts/test_system_scenarios.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import httpx

BASE_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
API = f"{BASE_URL}/api/v1/support"
RESULTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "docs", "testing", "scenario_results.json"
)


def has_arabic(text: str) -> bool:
    return any("؀" <= c <= "ۿ" for c in text or "")


# ── Scenario definitions (mirror docs/testing/user_scenarios.md) ──────────────

def _sess(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4()}"

SCENARIOS = [
    {
        "persona": "Sara (EN shopper)",
        "session": _sess("sara"),
        "turns": [
            {"msg": "Hi",
             "expect": {"route": "greeting", "lang": "en", "sources": False, "review": False, "escalation": False}},
            {"msg": "What is your return policy?",
             "expect": {"route": "general_knowledge", "lang": "en", "sources": True, "review": False, "escalation": False}},
            {"msg": "How long does shipping take?",
             "expect": {"route": "general_knowledge", "lang": "en", "sources": True, "review": False, "escalation": False}},
            {"msg": "Thanks!",
             "expect": {"route": "greeting", "lang": "en", "sources": False, "review": False, "escalation": False}},
        ],
    },
    {
        "persona": "Ahmed (AR shopper)",
        "session": _sess("ahmed"),
        "turns": [
            {"msg": "السلام عليكم",
             "expect": {"route": "greeting", "lang": "ar", "sources": False, "review": False, "escalation": False}},
            {"msg": "كم يستغرق الشحن؟",
             "expect": {"route": "general_knowledge", "lang": "ar", "sources": True, "review": False, "escalation": False}},
            {"msg": "ما هي مدة الضمان؟",
             "expect": {"route": "general_knowledge", "lang": "ar", "sources": True, "review": False, "escalation": False}},
        ],
    },
    {
        "persona": "Mona (EN order status)",
        "session": _sess("mona"),
        "turns": [
            {"msg": "Hi, where is my order ORD-2024-0001?",
             "expect": {"route": "customer_issue", "lang": "en", "sources": False}},
            {"msg": "When will it arrive?",
             "expect": {"route": "customer_issue", "lang": "en"}},
        ],
    },
    {
        "persona": "Khaled (AR refund -> review)",
        "session": _sess("khaled"),
        "turns": [
            {"msg": "مرحبا",
             "expect": {"route": "greeting", "lang": "ar", "review": False, "escalation": False}},
            # Refund against a *valid* invoice (INV-0001) so the high-risk
            # refund path produces a held draft (review). A non-existent
            # identifier would correctly hit the no-data escalation branch instead.
            {"msg": "عايز استرداد فلوس فاتورة INV-0001",
             "expect": {"route": "customer_issue", "lang": "ar", "review": True}},
        ],
    },
    {
        "persona": "Layla (EN hybrid)",
        "session": _sess("layla"),
        "turns": [
            {"msg": "My order ORD-2024-0001 is late — can I get a refund per your policy?",
             "expect": {"route": "hybrid", "lang": "en", "sources": True}},
        ],
    },
    {
        "persona": "Omar (EN memory)",
        "session": _sess("omar"),
        "turns": [
            {"msg": "how are you?",
             "expect": {"route": "greeting", "lang": "en", "sources": False, "review": False, "escalation": False}},
            {"msg": "what's your return policy?",
             "expect": {"route": "general_knowledge", "lang": "en", "sources": True}},
            {"msg": "and how long for shipping?",
             "expect": {"route": "general_knowledge", "lang": "en", "sources": True}},
        ],
    },
    {
        "persona": "Edge cases",
        "session": None,
        "turns": [
            {"msg": "ok",
             "expect": {"route": "greeting"}},
            {"msg": "Hello, I'm really not happy with you",
             "expect": {"route": "customer_issue"}},
            {"msg": "Hi, what is your return policy?",
             "expect": {"route": "general_knowledge"}},
            {"msg": "هل الفاتورة تشمل ضريبة القيمة المضافة؟",
             "expect": {"route": "general_knowledge", "lang": "ar"}},
            {"msg": "asdfghjkl",
             "expect": {"route": "customer_issue"}},
            {"msg": "", "expect": {"http_status": 422}},
        ],
    },
]


# ── Runner ────────────────────────────────────────────────────────────────────

def call(msg: str, session: str | None) -> tuple[int, dict]:
    payload: dict = {"query": msg}
    if session:
        payload["session_id"] = session
    with httpx.Client(timeout=120) as c:
        r = c.post(API, json=payload)
        try:
            body = r.json()
        except Exception:
            body = {}
        return r.status_code, body


def check_turn(expect: dict, status: int, body: dict) -> list[dict]:
    """Return a list of {check, severity, ok, detail}."""
    checks: list[dict] = []

    if "http_status" in expect:
        checks.append({
            "check": "http_status",
            "severity": "high",
            "ok": status == expect["http_status"],
            "detail": f"expected {expect['http_status']}, got {status}",
        })
        return checks

    # any 2xx expected for normal turns
    checks.append({
        "check": "http_ok",
        "severity": "high",
        "ok": status == 200,
        "detail": f"status={status}",
    })
    if status != 200:
        return checks

    route = body.get("route")
    reply = body.get("final_response", "") or ""
    sources = body.get("rag_sources", []) or []
    review = bool(body.get("review_required", False))
    escalation = bool(body.get("escalation_needed", False))

    if "route" in expect:
        checks.append({
            "check": "route",
            "severity": "high",
            "ok": route == expect["route"],
            "detail": f"expected {expect['route']}, got {route}",
        })
    if "lang" in expect:
        want_ar = expect["lang"] == "ar"
        got_ar = has_arabic(reply)
        checks.append({
            "check": "reply_language",
            "severity": "medium",
            "ok": (want_ar == got_ar) and bool(reply.strip()),
            "detail": f"expected {expect['lang']}, reply_has_arabic={got_ar}, len={len(reply)}",
        })
    if "sources" in expect:
        has_src = len(sources) > 0
        checks.append({
            "check": "sources_present" if expect["sources"] else "sources_absent",
            "severity": "medium" if expect["sources"] else "high",
            "ok": has_src == expect["sources"],
            "detail": f"expected sources={expect['sources']}, got {sources}",
        })
    if "review" in expect:
        checks.append({
            "check": "review_required",
            "severity": "high",
            "ok": review == expect["review"],
            "detail": f"expected review={expect['review']}, got {review}",
        })
    if "escalation" in expect:
        checks.append({
            "check": "escalation_needed",
            "severity": "high",
            "ok": escalation == expect["escalation"],
            "detail": f"expected escalation={expect['escalation']}, got {escalation}",
        })
    return checks


def main() -> None:
    print(f"\nWakeel Scenario Tests — backend {BASE_URL}")
    print("=" * 70)
    try:
        httpx.get(f"{BASE_URL}/docs", timeout=5)
    except Exception as exc:
        print(f"[FAIL] backend unreachable: {exc}")
        sys.exit(1)

    report: list[dict] = []
    totals = {"high": [0, 0], "medium": [0, 0]}  # [passed, total]

    for sc in SCENARIOS:
        print(f"\n### {sc['persona']}" + (f"  (session reused)" if sc["session"] else ""))
        sc_rec = {"persona": sc["persona"], "session": sc["session"], "turns": []}
        for turn in sc["turns"]:
            msg = turn["msg"]
            t0 = time.time()
            try:
                status, body = call(msg, sc["session"])
                err = None
            except Exception as e:
                status, body, err = -1, {}, str(e)
            elapsed = round(time.time() - t0, 2)

            checks = check_turn(turn["expect"], status, body) if err is None else [
                {"check": "request", "severity": "high", "ok": False, "detail": err}
            ]
            for ch in checks:
                sev = ch["severity"]
                if sev in totals:
                    totals[sev][1] += 1
                    if ch["ok"]:
                        totals[sev][0] += 1

            all_ok = all(c["ok"] for c in checks)
            icon = "OK  " if all_ok else "FAIL"
            shown = (msg[:42] + "…") if len(msg) > 43 else msg
            print(f"  [{icon}] {shown!r:48} route={body.get('route')!s:18} ({elapsed}s)")
            for c in checks:
                if not c["ok"]:
                    print(f"          ✗ {c['check']} [{c['severity']}]: {c['detail']}")

            sc_rec["turns"].append({
                "msg": msg,
                "elapsed_s": elapsed,
                "http_status": status,
                "route": body.get("route"),
                "final_response": body.get("final_response"),
                "rag_sources": body.get("rag_sources"),
                "review_required": body.get("review_required"),
                "escalation_needed": body.get("escalation_needed"),
                "issue_type": body.get("issue_type"),
                "checks": checks,
                "all_ok": all_ok,
                "error": err,
            })
        report.append(sc_rec)

    # Summary
    print("\n" + "=" * 70)
    hp, ht = totals["high"]
    mp, mt = totals["medium"]
    print(f"HIGH-severity checks : {hp}/{ht} passed")
    print(f"MEDIUM-severity checks: {mp}/{mt} passed")
    turn_total = sum(len(s["turns"]) for s in report)
    turn_ok = sum(1 for s in report for t in s["turns"] if t["all_ok"])
    print(f"Turns fully green     : {turn_ok}/{turn_total}")

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w", encoding="utf-8") as fh:
        json.dump({
            "backend": BASE_URL,
            "summary": {
                "high": totals["high"], "medium": totals["medium"],
                "turns_fully_green": [turn_ok, turn_total],
            },
            "scenarios": report,
        }, fh, ensure_ascii=False, indent=2)
    print(f"\nFull results written to: {os.path.relpath(RESULTS_PATH)}")


if __name__ == "__main__":
    main()

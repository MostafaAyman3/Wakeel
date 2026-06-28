"""
Feature 004 — Clarifying Follow-up for Missing Identifiers: scenario tests.

Hits the live POST /api/v1/support. Multi-turn scenarios use a real UUID
session_id (the conversation store requires a UUID) so attempt-counting and
context carry-over work.

Usage:
    python scripts/test_clarification.py
"""
import sys, json, uuid, urllib.request

sys.stdout.reconfigure(encoding="utf-8")
BASE = "http://127.0.0.1:8000/api/v1/support"


def ask(query, session_id=None, identifier=None):
    body = {"query": query}
    if session_id:
        body["session_id"] = session_id
    if identifier:
        body["identifier"] = identifier
    req = urllib.request.Request(
        BASE, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def new_session():
    return str(uuid.uuid4())


passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} :: {detail}")


def has_arabic(s):
    return any("؀" <= c <= "ۿ" for c in s or "")


print("=== US1 Scenario A — EN: ask, then answer ===")
sa = new_session()
r1 = ask("Where is my order?", session_id=sa)
check("A1 clarification_pending=true", r1.get("clarification_pending") is True, r1.get("final_response", "")[:80])
check("A1 not escalated", r1.get("escalation_needed") is False, str(r1.get("escalation_needed")))
r2 = ask("ORD-2024-1567", session_id=sa)
check("A2 answered original (mentions order/ship)", any(w in r2.get("final_response", "").lower() for w in ("order", "ship", "transit", "deliver")), r2.get("final_response", "")[:100])
check("A2 not a clarification", r2.get("clarification_pending") is False)

print("=== US1/US3 Scenario B — AR: ask in Arabic, then answer ===")
sb = new_session()
b1 = ask("فين الأوردر بتاعي؟", session_id=sb)
check("B1 clarification_pending=true", b1.get("clarification_pending") is True)
check("B1 question in Arabic", has_arabic(b1.get("final_response", "")), b1.get("final_response", "")[:80])
b2 = ask("ORD-2024-1567", session_id=sb)
check("B2 answered (not clarifying)", b2.get("clarification_pending") is False)

print("=== US2 Scenario C — ambiguous bare number ===")
sc = new_session()
c1 = ask("my number is 1567, where is it?", session_id=sc)
check("C1 clarification_pending=true", c1.get("clarification_pending") is True, c1.get("final_response", "")[:80])
check("C1 asks the type (order/invoice/customer)", any(w in c1.get("final_response", "").lower() for w in ("order", "invoice", "customer", "طلب", "فاتورة", "عميل")), c1.get("final_response", "")[:100])

print("=== US4 Scenario D — exhausted attempts -> escalate ===")
sd = new_session()
d1 = ask("Where is my order?", session_id=sd)
check("D1 ask #1 pending", d1.get("clarification_pending") is True)
d2 = ask("I don't know", session_id=sd)
check("D2 ask #2 pending", d2.get("clarification_pending") is True)
d3 = ask("still no idea", session_id=sd)
check("D3 escalated (no 3rd ask)", d3.get("escalation_needed") is True and d3.get("clarification_pending") is False,
      f"pending={d3.get('clarification_pending')} escalate={d3.get('escalation_needed')}")

print("=== Scenario E — no-regression guards ===")
check("E greeting no clarification", ask("hello", session_id=new_session()).get("clarification_pending") is False)
kb = ask("What is your return policy?", session_id=new_session())
check("E knowledge no clarification", kb.get("clarification_pending") is False)
check("E knowledge has sources", len(kb.get("rag_sources", [])) > 0, str(kb.get("rag_sources")))
direct = ask("Where is my order ORD-2024-1567?", session_id=new_session())
check("E direct lookup, no clarification", direct.get("clarification_pending") is False)
bill = ask("invoice INV-0001 is wrong, I did not order it", session_id=new_session())
check("E billing dispute still review_required", bill.get("review_required") is True, str(bill.get("review_required")))

print("=== Scenario F — supplied ref not found (graceful) ===")
sf = new_session()
f1 = ask("status of DEL-999?", session_id=sf)
# DEL-999 is parsed as an order_id; not found -> should NOT be a generic black-box.
check("F mentions the reference DEL-999", "DEL-999" in f1.get("final_response", ""), f1.get("final_response", "")[:120])

print(f"\n{'='*56}\nSUMMARY: {passed} passed, {failed} failed\n{'='*56}")
sys.exit(0 if failed == 0 else 1)

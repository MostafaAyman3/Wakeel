"""
Feature 005 — Conversation Memory & Recall: scenario tests.

Hits the live POST /api/v1/support. Multi-turn scenarios reuse a real UUID
session_id (the conversation store requires a UUID) so the transcript is loaded
and recall works.

Scenarios (from specs/005-chat-memory-recall/quickstart.md):
    M1  recall a name (EN)              — FR-002, SC-001
    M2  recall a name (AR)              — FR-007
    M3  cross-session isolation         — FR-003, SC-002
    M4  update wins (most recent)       — FR-004, SC-005
    M5  unknown, no fabrication         — FR-005, SC-003
    M6  cross-path recall               — FR-006, SC-004

Usage:
    python scripts/test_memory.py
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


def reply(r):
    return (r.get("final_response") or r.get("draft_response") or "")


def asks_for_order(text):
    """Heuristic: did the bot ask for an order/reference number instead of recalling?"""
    t = text.lower()
    return any(w in t for w in ("order number", "reference number", "رقم الطلب", "رقم المرجع", "رقم الأوردر"))


# ── M1 — Recall a name (EN) — FR-002, SC-001 ───────────────────────
print("=== M1 — Recall a name (EN) ===")
s1 = new_session()
ask("Hi, my name is Kareem", session_id=s1)
m1 = ask("what is my name?", session_id=s1)
check("M1 recalls 'Kareem'", "kareem" in reply(m1).lower(), reply(m1)[:120])
check("M1 not an order-number request", not asks_for_order(reply(m1)), reply(m1)[:120])

# ── M2 — Recall a name (AR) — FR-007 ───────────────────────────────
print("=== M2 — Recall a name (AR) ===")
s2 = new_session()
ask("اسمي كريم", session_id=s2)
m2 = ask("اسمي ايه؟", session_id=s2)
check("M2 recalls 'كريم'", "كريم" in reply(m2), reply(m2)[:120])
check("M2 reply in Arabic", has_arabic(reply(m2)), reply(m2)[:120])

# ── M3 — Cross-session isolation — FR-003, SC-002 ──────────────────
print("=== M3 — Cross-session isolation ===")
sa = new_session()
sb = new_session()
ask("my name is Kareem", session_id=sa)
m3 = ask("what is my name?", session_id=sb)
check("M3 session B does NOT know 'Kareem'", "kareem" not in reply(m3).lower(), reply(m3)[:120])

# ── M4 — Update wins (most recent) — FR-004, SC-005 ────────────────
print("=== M4 — Update wins ===")
s4 = new_session()
ask("my name is Kareem", session_id=s4)
ask("actually my name is Khaled", session_id=s4)
m4 = ask("what is my name?", session_id=s4)
check("M4 recalls latest 'Khaled'", "khaled" in reply(m4).lower(), reply(m4)[:120])
check("M4 does not say old 'Kareem'", "kareem" not in reply(m4).lower(), reply(m4)[:120])

# ── M5 — Unknown, no fabrication — FR-005, SC-003 ──────────────────
print("=== M5 — Unknown, no fabrication ===")
s5 = new_session()
m5 = ask("what is my name?", session_id=s5)
check("M5 does not invent a name & no order-number ask",
      not asks_for_order(reply(m5)) and "kareem" not in reply(m5).lower() and "khaled" not in reply(m5).lower(),
      reply(m5)[:160])

# ── M6 — Cross-path recall — FR-006, SC-004 ────────────────────────
print("=== M6 — Cross-path recall ===")
s6 = new_session()
ask("my name is Kareem", session_id=s6)
kb = ask("what is your return policy?", session_id=s6)
check("M6 knowledge turn answered", len(reply(kb)) > 0)
m6 = ask("what is my name?", session_id=s6)
check("M6 still recalls 'Kareem' after a knowledge turn", "kareem" in reply(m6).lower(), reply(m6)[:120])

print(f"\n{'='*56}\nSUMMARY: {passed} passed, {failed} failed\n{'='*56}")
sys.exit(0 if failed == 0 else 1)

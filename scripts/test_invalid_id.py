"""
Feature 006 — Invalid Identifier Retry & Guidance: scenario tests.

Hits the live POST /api/v1/support. Multi-turn scenarios share a real UUID
session_id so the conversation history (metadata tags) accumulates correctly.

Scenarios:
    I1   1st not-found → friendly retry message (EN)              — US1, FR-003, FR-004
    I2   2nd not-found → same retry message, count 2              — US1, FR-003, FR-004
    I3   3rd not-found → escalation menu (no alt-lookup)          — US2, FR-005
    I4   4th not-found → menu re-presented (not plain retry)      — US2, FR-006
    I5   valid ID after failures → record returned, count resets   — US3, FR-009
    I6   new invalid after reset → count 1 (retry, not menu)      — US3, SC-003
    I7   cross-session isolation: session B unaffected by A        — US4, FR-011
    I8   fresh session starts at count 0                          — US4, FR-010
    I9   Arabic conversation → Arabic messages                    — FR-013, SC-006
    I10  no-regression: missing ID still triggers Feature 004     — FR-015, SC-007
    I11  no-regression: valid ID still returns record directly    — FR-014, SC-007

Usage:
    python scripts/test_invalid_id.py

Prerequisites:
    - Backend running on http://127.0.0.1:8000
    - Supabase connection live (for session history storage)
    - The test uses a non-existent order ID (ORD-INVALID-0000) that will
      reliably return no data.  A VALID order ID must be provided via the
      VALID_ORDER_ID constant below (update to a real value in your DB).
"""

import sys
import json
import uuid
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://127.0.0.1:8000/api/v1/support"

# Update this to a real order/invoice ID in your test database
VALID_ORDER_ID = "ORD-2024-1567"
INVALID_ID = "ORD-INVALID-0000"


# ── Helpers ───────────────────────────────────────────────────────────────────

def ask(query, session_id=None, identifier=None):
    body = {"query": query}
    if session_id:
        body["session_id"] = session_id
    if identifier:
        body["identifier"] = identifier
    req = urllib.request.Request(
        BASE,
        data=json.dumps(body).encode(),
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


def reply(r):
    return (r.get("final_response") or "").strip()


def has_arabic(s):
    return any("؀" <= c <= "ۿ" for c in s or "")


# ── Scenario helpers ──────────────────────────────────────────────────────────

RETRY_KEYWORDS_EN = ["couldn't find", "rewrite", "try again"]
MENU_KEYWORDS_EN = ["3 attempts", "Re-enter", "human agent"]
RETRY_KEYWORDS_AR = ["لم نتمكن", "أعد كتابة", "حاول مرة"]
MENU_KEYWORDS_AR = ["3 محاولات", "إعادة إدخال", "موظف"]


def is_retry_message(text, lang="en"):
    kws = RETRY_KEYWORDS_AR if lang == "ar" else RETRY_KEYWORDS_EN
    tl = text.lower()
    return any(kw.lower() in tl for kw in kws)


def is_menu_message(text, lang="en"):
    kws = MENU_KEYWORDS_AR if lang == "ar" else MENU_KEYWORDS_EN
    tl = text.lower()
    return any(kw.lower() in tl for kw in kws)


# ── Scenario I1 & I2: US1 — friendly retry on 1st and 2nd failures ───────────

print("\n=== Scenario I1+I2: US1 — friendly retry (1st & 2nd failures) ===")
sid = new_session()

r1 = ask(f"Where is my order {INVALID_ID}?", session_id=sid)
check("I1 not escalated on 1st failure", not r1.get("escalation_needed"), r1.get("final_response"))
check("I1 is retry message (EN)", is_retry_message(reply(r1)), reply(r1))
check("I1 invalid_id_pending=True", r1.get("invalid_id_pending"), str(r1.get("invalid_id_pending")))
check("I1 invalid_id_menu_shown=False", not r1.get("invalid_id_menu_shown"), str(r1.get("invalid_id_menu_shown")))

r2 = ask(f"Try again: {INVALID_ID}", session_id=sid)
check("I2 not escalated on 2nd failure", not r2.get("escalation_needed"), r2.get("final_response"))
check("I2 is retry message (EN)", is_retry_message(reply(r2)), reply(r2))
check("I2 invalid_id_pending=True", r2.get("invalid_id_pending"), str(r2.get("invalid_id_pending")))
check("I2 invalid_id_menu_shown=False", not r2.get("invalid_id_menu_shown"), str(r2.get("invalid_id_menu_shown")))


# ── Scenario I3: US2 — escalation menu on 3rd failure ────────────────────────

print("\n=== Scenario I3: US2 — escalation menu on 3rd failure ===")
# Continue same session from I1+I2 (already 2 failures)

r3 = ask(f"Still trying: {INVALID_ID}", session_id=sid)
check("I3 not directly escalated (menu first)", not r3.get("escalation_needed"), r3.get("final_response"))
check("I3 is menu message (EN)", is_menu_message(reply(r3)), reply(r3))
check("I3 invalid_id_menu_shown=True", r3.get("invalid_id_menu_shown"), str(r3.get("invalid_id_menu_shown")))
check("I3 re-enter choice present", "re-enter" in reply(r3).lower(), reply(r3))
check("I3 human agent choice present", "human agent" in reply(r3).lower(), reply(r3))
# alt-lookup is disabled by default — choice 3 should NOT appear
check("I3 phone/email choice absent (alt disabled)", "phone" not in reply(r3).lower(), reply(r3))


# ── Scenario I4: US2 — menu re-presented on 4th failure ──────────────────────

print("\n=== Scenario I4: US2 — menu re-presented after 3rd failure ===")

r4 = ask(f"What about {INVALID_ID}?", session_id=sid)
check("I4 menu re-presented (not plain retry)", is_menu_message(reply(r4)), reply(r4))
check("I4 invalid_id_menu_shown=True", r4.get("invalid_id_menu_shown"), str(r4.get("invalid_id_menu_shown")))
check("I4 not direct escalation", not r4.get("escalation_needed"), r4.get("final_response"))


# ── Scenario I5 & I6: US3 — valid ID resets the count ────────────────────────

print("\n=== Scenario I5+I6: US3 — valid ID clears the slate ===")
sid_reset = new_session()

# Cause one failure first
ask(f"My order is {INVALID_ID}", session_id=sid_reset)

# Now provide a valid ID
r5 = ask(f"Actually try {VALID_ORDER_ID}", session_id=sid_reset)
check("I5 valid ID not escalated", not r5.get("escalation_needed"), r5.get("final_response"))
check("I5 no retry/menu on valid ID", not r5.get("invalid_id_pending"), str(r5.get("invalid_id_pending")))
check("I5 valid ID returns record or response", len(reply(r5)) > 0, reply(r5))

# After reset, a new invalid ID should be attempt 1 (retry, not menu)
r6 = ask(f"What about order {INVALID_ID}?", session_id=sid_reset)
check("I6 restart at attempt 1 (retry, not menu)", is_retry_message(reply(r6)), reply(r6))
check("I6 menu not shown after reset", not r6.get("invalid_id_menu_shown"), str(r6.get("invalid_id_menu_shown")))


# ── Scenario I7 & I8: US4 — per-conversation isolation ───────────────────────

print("\n=== Scenario I7+I8: US4 — cross-session isolation ===")
sid_a = new_session()
sid_b = new_session()

# Session A: cause 2 failures
ask(f"Order {INVALID_ID}", session_id=sid_a)
ask(f"Retry {INVALID_ID}", session_id=sid_a)

# Session B: first attempt should still be attempt 1 (retry, not menu)
r7 = ask(f"Where is {INVALID_ID}?", session_id=sid_b)
check("I7 session B unaffected by session A", is_retry_message(reply(r7)), reply(r7))
check("I7 menu not shown in session B (only 1 attempt)", not r7.get("invalid_id_menu_shown"), str(r7.get("invalid_id_menu_shown")))

# Fresh session: starts at 0
sid_fresh = new_session()
r8 = ask(f"Order number {INVALID_ID}", session_id=sid_fresh)
check("I8 fresh session starts at count 0 (retry not menu)", is_retry_message(reply(r8)), reply(r8))
check("I8 fresh session invalid_id_pending=True", r8.get("invalid_id_pending"), str(r8.get("invalid_id_pending")))


# ── Scenario I9: AR language ──────────────────────────────────────────────────

print("\n=== Scenario I9: Arabic conversation → Arabic messages ===")
sid_ar = new_session()

r9 = ask(f"أين طلبي رقم {INVALID_ID}؟", session_id=sid_ar)
check("I9 invalid_id_pending=True", r9.get("invalid_id_pending"), str(r9.get("invalid_id_pending")))
check("I9 reply is in Arabic", has_arabic(reply(r9)), reply(r9))
check("I9 is Arabic retry message", is_retry_message(reply(r9), lang="ar"), reply(r9))

# Cause 2 more failures to trigger the Arabic menu
ask(f"نفس الرقم: {INVALID_ID}", session_id=sid_ar)
r9m = ask(f"مرة ثالثة: {INVALID_ID}", session_id=sid_ar)
check("I9 3rd failure shows Arabic menu", is_menu_message(reply(r9m), lang="ar"), reply(r9m))
check("I9 Arabic menu has_arabic", has_arabic(reply(r9m)), reply(r9m))


# ── Scenario I10: no-regression — missing ID triggers Feature 004 ─────────────

print("\n=== Scenario I10: no-regression — missing ID → Feature 004 clarification ===")
sid_miss = new_session()

r10 = ask("Where is my order?", session_id=sid_miss)
check("I10 clarification asked (not invalid_id)", r10.get("clarification_pending"), str(r10.get("clarification_pending")))
check("I10 invalid_id_pending=False", not r10.get("invalid_id_pending"), str(r10.get("invalid_id_pending")))
check("I10 not escalated", not r10.get("escalation_needed"), r10.get("final_response"))


# ── Scenario I11: no-regression — valid ID goes straight to record ────────────

print("\n=== Scenario I11: no-regression — valid ID → normal record response ===")
sid_valid = new_session()

r11 = ask(f"What is the status of {VALID_ORDER_ID}?", session_id=sid_valid)
check("I11 no invalid_id_pending on valid ID", not r11.get("invalid_id_pending"), str(r11.get("invalid_id_pending")))
check("I11 no clarification on valid ID", not r11.get("clarification_pending"), str(r11.get("clarification_pending")))
check("I11 has a real response", len(reply(r11)) > 0, reply(r11))


# ── Summary ───────────────────────────────────────────────────────────────────

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed out of {passed + failed} checks")
if failed == 0:
    print("ALL CHECKS PASSED ✓")
else:
    print(f"{failed} CHECK(S) FAILED ✗")
    sys.exit(1)

# Problem Report — M3 Support System (Deep Scenario Test)

**Date**: 2026-06-26
**Tested against**: live system — backend `:8000`, Mini-RAG `:8001`, frontend `:3000`
**Method**: 16 real user journeys sent to `POST /api/v1/support` (single-turn + multi-turn with `session_id`).
**Related spec**: [specs/004-clarify-missing-identifier](specs/004-clarify-missing-identifier/spec.md)

---

## Summary

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | Record questions **without** a reference escalate immediately instead of asking a clarifying follow-up | 🔴 Critical | ✅ Fixed (Feature 004) |
| 2 | Unknown / unrecognized reference escalates with a generic message instead of a graceful "not found" | 🟠 High | ✅ Fixed (Feature 004) |
| 3 | English general-knowledge answers prepend an irrelevant "couldn't find your account" apology | 🟡 Medium | Open (out of scope of 004) |
| 4 | Low-signal inputs (e.g. "help") route to `customer_issue` and escalate instead of greeting/clarifying | 🟡 Medium | ◑ Improved — now asks a clarifying question instead of escalating; greeting-route still ideal |
| 5 | Ambiguous bare number ("1567") escalates instead of asking which reference type it is | 🟡 Medium | ✅ Fixed (Feature 004) |

> **Update 2026-06-26 (Feature 004 implemented)**: ISSUE-1, ISSUE-2, ISSUE-5 fixed and verified by `scripts/test_clarification.py` (18/18) plus regression suites (`test_m3_sprint1` 5/5, `test_m3_sprint4` 12/12). Record-dependent questions without a reference now ask a language-matched follow-up (max 2 attempts → escalate); unknown references return a graceful "couldn't find <ref>" message; bare numbers ask which reference type. ISSUE-3 (EN knowledge apology prefix) remains open as a response-template tweak outside this feature's scope.

What already works well is listed at the end.

---

## ISSUE-1 — Missing identifier → immediate escalation (Critical)

A question that needs a record lookup but contains **no** order/invoice/customer number is escalated to a human on the first turn, instead of the assistant asking the customer for the number it needs.

**Evidence**

| Scenario | Query | Result |
|----------|-------|--------|
| S6 | "Where is my order?" | `escalate=True` → "Your case has been escalated…" |
| S7 | "فين الأوردر بتاعي؟" | `escalate=True` → "تم إحالة حالتك…" |
| S9 | "the amount on my bill is wrong" | `escalate=True` |
| S12-t1 | "Where is my order?" | `escalate=True` |
| S13-t1 | "عايز اعرف حالة طلبي" | `escalate=True` |
| S16-t1 | "where is my order?" | `escalate=True` |

**Expected** (spec 004, FR-002): reply with a short question — "Sure — what's your order number?" / "ممكن رقم الطلب؟" — and only escalate after the customer can't provide it.

**Note (good)**: session context carries correctly on the *next* turn. After escalating on S12-t1, sending just `ORD-2024-1567` (S12-t2) **did** answer the original order question ("your order has been shipped…"), same for the Arabic S13-t2. So the fix is mainly "ask instead of escalate" on the first turn; the memory plumbing already works.

---

## ISSUE-2 — Unknown reference → generic escalation, not graceful "not found" (High)

A well-formed but non-existent reference produces the same generic escalation message as a missing one. The customer is never told the number wasn't found or asked to check it.

**Evidence**

| Scenario | Query | Result |
|----------|-------|--------|
| S10 | "what is the status of DEL-999?" | `issue=None, escalate=True` → "Your case has been escalated…" |

**Expected** (spec 004, FR-008 / blueprint Graceful Degradation): "We couldn't find **DEL-999** in our system. Please double-check the number, or we can connect you to an agent." The reference value should appear in the message.

**Side note**: the customer-facing escalation text is **identical** for three very different situations (no reference, reference not found, vague input). Customers can't tell what went wrong or what to do next.

---

## ISSUE-3 — English knowledge answers prepend an irrelevant apology (Medium)

Pure general-knowledge questions (no account needed) get an English answer that starts with a CRM-style apology about not finding the customer's account, then pivots to the real answer. The Arabic path does **not** do this.

**Evidence**

| Scenario | Query | Reply (start) |
|----------|-------|---------------|
| S3 | "What is your return policy?" | *"I'm sorry, but I couldn't find any specific information related to your account. However, I can share our return policy…"* |
| S16-t2 | "what is your return policy?" | *"I'm sorry, but I couldn't find any matching record for your inquiry. However, I can provide you with…"* |
| S4 (AR, for contrast) | "ما هي سياسة الاسترجاع؟" | *"عزيزي العميل، يمكنك إرجاع معظم المنتجات خلال 14 يومًا…"* (clean, no apology) |

**Expected**: for a `general_knowledge` route, answer directly from the knowledge base without the "couldn't find your account" preamble. Behavior should match the clean Arabic path. Likely the English response template merges a CRM "not found" branch into a knowledge answer.

---

## ISSUE-4 — Low-signal input mis-routes to customer_issue + escalates (Medium)

A bare "help" is treated as a customer issue and escalated, rather than greeted or asked what they need.

**Evidence**

| Scenario | Query | Result |
|----------|-------|--------|
| S15 | "help" | `route=customer_issue, escalate=True` |

**Expected**: route to greeting/clarification — "Happy to help! Are you asking about an order, an invoice, or something else?" No escalation.

---

## ISSUE-5 — Ambiguous bare number not disambiguated (Medium)

A number with no recognizable prefix is escalated instead of the assistant asking whether it's an order, invoice, or customer number.

**Evidence**

| Scenario | Query | Result |
|----------|-------|--------|
| S11 | "my number is 1567, where is it?" | `escalate=True` |

**Expected** (spec 004, FR-011): "Is **1567** an order, invoice, or customer number?" This is a subset of ISSUE-1 but distinct because the customer *did* give a value — it just lacks a type.

---

## What works well (no action needed)

| Area | Scenario | Result |
|------|----------|--------|
| Greeting EN | S1 "hello" | ✅ greeting, no escalation |
| Greeting AR | S2 "السلام عليكم" | ✅ "وعليكم السلام! كيف يمكنني مساعدتك؟" |
| Knowledge AR | S4 | ✅ clean policy answer with `rag_sources` |
| Order lookup (with id) | S5 "ORD-2024-1567" | ✅ real status, addresses "Omar" by name |
| Billing dispute gating | S8 "INV-0001 wrong" | ✅ `billing_dispute`, `review_required=True`, held from customer |
| Refund gating | S14 | ✅ `refund_request`, `review_required=True` |
| Multi-turn memory | S12-t2 / S13-t2 | ✅ bare reference answered the original question |
| Topic switch | S16-t2 | ✅ pending order context not misapplied to the policy question |

---

## Recommended order of fixes

1. **ISSUE-1 + ISSUE-5** — implement spec 004 (clarifying follow-up + type disambiguation). Highest impact; turns ~7 of the 16 journeys from dead-ends into answers.
2. **ISSUE-2** — graceful "not found" message that names the reference (small change, big UX win).
3. **ISSUE-3** — strip the account-apology preamble from English `general_knowledge` replies (template fix).
4. **ISSUE-4** — route low-signal inputs to greeting/clarify instead of customer_issue.

---

# Problem Report — Conversation Memory (Feature 005 baseline)

**Date**: 2026-06-26 · **Tested against**: live backend `:8000` + Mini-RAG `:8001`
**Method**: 5 memory journeys via `POST /api/v1/support` with a UUID `session_id` per conversation.

## Summary

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| M-1 | The assistant does not recall facts stated earlier in the same conversation (e.g., the customer's name) | 🔴 Critical | ✅ Fixed (Feature 005) |
| M-2 | "What is my name?" mis-routes to the CRM/issue path and asks for an **order number** instead of recalling the name | 🟠 High | ✅ Fixed (Feature 005) |

> **Update 2026-06-27 (Feature 005 implemented)**: M-1 and M-2 fixed and verified by `scripts/test_memory.py` (10/10) plus regression suites (`test_clarification` 18/18, `test_m3_sprint1` 5/5, `test_m3_sprint4` 12/12). The conversational reply path (`greeting_node`) now receives the recent transcript and recalls facts (name in EN/AR); the intent router (`support_router.py`) routes personal-recall questions to the conversational path instead of the CRM/clarification path. Updates use the most recent value; never-stated facts are not fabricated (no order-number ask); cross-session isolation preserved. Frontend persists a UUID `session_id` in `localStorage` so memory survives a page reload (FR-010) — previously the id was a non-UUID generated per page load, which the conversation store silently dropped.

## Evidence

| Scenario | Turns | Result |
|----------|-------|--------|
| M-1 recall (EN) | "my name is Kareem" → "what is my name?" | t1 greeted "Hi Kareem!" ✅ but t2 replied *"could you provide your order number…"* — **name not recalled** ❌ |
| M-2 recall (AR) | "اسمي كريم" → "اسمي ايه؟" | t2: *"أهلاً بك! كيف يمكنني مساعدتك؟"* — generic greeting, **no recall** ❌ |
| Cross-session | name in session A → ask in session B | B does not know it ✅ (isolation is correct) |
| Update name | "Kareem" → "actually Khaled" → "what's my name?" | generic greeting, **no recall** ❌ |
| Unknown | ask name with no prior mention | asks for an order number ❌ (should say "you haven't told me yet") |

## Root cause (observed)

1. **No recall**: the small-talk / greeting reply path answers from the *current* message only; it does not use the conversation history to recall earlier facts. So a stored name is never returned.
2. **Mis-route**: "what is my name?" is classified as a customer issue → it reaches the input parser → no order/invoice/customer number → the (correct, new) clarification feature asks for a reference number. A personal/conversational question should be handled by the chat path **with memory**, not the record-lookup path.

## Expected after Feature 005

- "my name is X" then "what's my name?" → answers "X" (same conversation), in the question's language.
- A question about the conversation itself (name, what was said) is answered from memory, not routed to record lookup.
- New conversation / never-stated → "I don't have that yet", no fabrication; no cross-conversation leak.

# Wakeel Unified Support Chatbot — Realistic User Scenarios

**Purpose**: Realistic end-to-end conversations from real customer personas, with
the **expected (ideal) system behaviour** for every turn. These scenarios drive
`scripts/test_system_scenarios.py` and the analysis in
`system_analysis_and_solutions.md`.

**System under test**: `POST /api/v1/support` (public chat) → Intent Router →
one of four routes:

| Route | Handler | Needs |
|-------|---------|-------|
| `greeting` | greeting_node (friendly reply) | LLM only |
| `general_knowledge` | rag_node → Mini-RAG | Mini-RAG + KB ingested |
| `customer_issue` | M3 CRM pipeline | Wakeel DB (orders/invoices) |
| `hybrid` | rag_node + CRM pipeline | Mini-RAG + DB |

**Expected-response legend** (per turn we assert):
- **route** — the classification the router should pick
- **lang** — language the reply should be in (mirrors the customer)
- **sources** — whether KB sources should be attached
- **review** — whether `review_required` should be true (held draft)
- **escalation** — whether `escalation_needed` should be true

---

## Persona 1 — Sara (English, browsing shopper, polite)

**Context**: New visitor, no order yet. Wants to understand policies before buying.

| # | Sara says | Expected route | Expected reply (ideal) | lang | sources | review | escalation |
|---|-----------|----------------|------------------------|------|---------|--------|------------|
| 1 | "Hi" | greeting | Short friendly greeting + offer to help | en | no | no | no |
| 2 | "What is your return policy?" | general_knowledge | "You can return most items within 14 days… full refund if unused/original packaging" grounded in KB, cites source | en | yes | no | no |
| 3 | "How long does shipping take?" | general_knowledge | "Standard 5–7 business days, Express 2–3…" from KB | en | yes | no | no |
| 4 | "Thanks!" | greeting | Brief courteous acknowledgement + offer further help | en | no | no | no |

**Why it matters**: First impression (greeting) + the core knowledge value (US1).
A return-policy answer that is NOT grounded (no sources / generic) is a failure.

---

## Persona 2 — Ahmed (Arabic, mobile user, wants quick facts)

**Context**: Arabic speaker, pre-purchase shipping & warranty questions.

| # | Ahmed says | Expected route | Expected reply (ideal) | lang | sources | review | escalation |
|---|-----------|----------------|------------------------|------|---------|--------|------------|
| 1 | "السلام عليكم" | greeting | تحية ودّية قصيرة + عرض المساعدة | ar | no | no | no |
| 2 | "كم يستغرق الشحن؟" | general_knowledge | "الشحن العادي 5–7 أيام عمل…" من قاعدة المعرفة | ar | yes | no | no |
| 3 | "ما هي مدة الضمان؟" | general_knowledge | "ضمان المصنّع 12 شهرًا على الأقل…" من قاعدة المعرفة | ar | yes | no | no |

**Why it matters**: Bilingual grounding. Arabic question MUST get an Arabic,
KB-grounded answer (language-mirroring fix + RAG).

---

## Persona 3 — Mona (English, existing customer, order status)

**Context**: Placed order `ORD-2024-0001`; wants status. Reference is in the text.

| # | Mona says | Expected route | Expected reply (ideal) | lang | sources | review | escalation |
|---|-----------|----------------|------------------------|------|---------|--------|------------|
| 1 | "Hi, where is my order ORD-2024-0001?" | customer_issue | Order status + carrier/tracking/ETA from CRM; friendly | en | no | no | no |
| 2 | "When will it arrive?" (same session) | customer_issue | Uses prior context; gives ETA | en | no | maybe | no |

**Why it matters**: The greeting prefix must NOT make this a greeting (precedence),
and the CRM pipeline must fetch real order data. Session memory on turn 2.

---

## Persona 4 — Khaled (Arabic, frustrated, refund request → human review)

**Context**: Unhappy about invoice `INV-2024-0007`; explicitly asks for a refund.

| # | Khaled says | Expected route | Expected reply (ideal) | lang | sources | review | escalation |
|---|-----------|----------------|------------------------|------|---------|--------|------------|
| 1 | "مرحبا" | greeting | تحية ودّية | ar | no | no | no |
| 2 | "عايز استرداد فلوس فاتورة INV-2024-0007" | customer_issue | The draft is HELD; customer sees "سيتواصل معك أحد أفراد فريق الدعم قريباً" | ar | no | **yes** | no |

**Why it matters**: `refund_request` → mandatory human review. The customer must
see the neutral waiting message, NOT the internal draft (review-hold shaping).

---

## Persona 5 — Layla (English, hybrid: order + policy in one question)

**Context**: Late order + wants to know refund eligibility per policy.

| # | Layla says | Expected route | Expected reply (ideal) | lang | sources | review | escalation |
|---|-----------|----------------|------------------------|------|---------|--------|------------|
| 1 | "My order ORD-2024-0001 is late — can I get a refund per your policy?" | hybrid | ONE merged answer: order status (CRM) + refund policy (KB), coherent | en | yes | maybe | no |

**Why it matters**: Hybrid merges KB knowledge + the customer's CRM data into a
single coherent reply (US3).

---

## Persona 6 — Omar (English, small-talk + session continuity)

**Context**: Chatty; tests memory across turns with one `session_id`.

| # | Omar says | Expected route | Expected reply (ideal) | lang | sources | review | escalation |
|---|-----------|----------------|------------------------|------|---------|--------|------------|
| 1 | "how are you?" | greeting | Friendly small-talk reply | en | no | no | no |
| 2 | "what's your return policy?" | general_knowledge | KB-grounded return policy | en | yes | no | no |
| 3 | "and how long for shipping?" | general_knowledge | Uses context; shipping timeframe from KB | en | yes | no | no |

**Why it matters**: Same `session_id` across turns; turn 3 ("and…") relies on
prior context (conversation memory).

---

## Persona 7 — Edge cases & adversarial inputs

| # | Message | Expected route | Rationale |
|---|---------|----------------|-----------|
| E1 | "ok" | customer_issue | ambiguous, low-confidence → conservative fallback (never greeting) |
| E2 | "Hello, I'm really not happy with you" | customer_issue | complaint wins over greeting framing |
| E3 | "Hi, what is your return policy?" | general_knowledge | question wins over greeting |
| E4 | "هل الفاتورة تشمل ضريبة القيمة المضافة؟" | general_knowledge (tax) | tax question → tax collection |
| E5 | "asdfghjkl" (gibberish) | customer_issue | unclassifiable → conservative fallback, graceful reply |
| E6 | "" (empty) | (HTTP 422) | input validation rejects empty query |

**Why it matters**: These protect the conservative-routing safety property — a
real support need must NEVER be dropped into small-talk, and the system must
degrade gracefully on garbage input.

---

## Cross-cutting expectations (all turns)

1. The reply language always mirrors the customer's message (AR/EN).
2. A `greeting` reply never carries sources, never holds a draft, never escalates.
3. A held reply (`review_required`) shows the neutral waiting message, never the
   internal draft.
4. No internal field names / system jargon leak into any reply.
5. Every turn returns valid JSON (never an unhandled 500 to the customer).

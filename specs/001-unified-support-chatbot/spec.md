# Feature Spec: Unified Support Chatbot (Mini-RAG × M3 CRM)

## Summary

A single customer-facing **chatbot** backed by a unified `/support` endpoint. An
**Intent Router** classifies each customer message and dispatches it to:
- the **RAG pipeline** (Mini-RAG-APP-V1 microservice) for knowledge questions,
- the **M3 CRM agent** for order issues / complaints, or
- **both** (hybrid) for a single merged answer.

Mini-RAG runs as a separate service called over HTTP (reuse, no rewrite). The
frontend reuses existing chat components. See `plan.md` for full architecture,
decisions, and the sprint/task breakdown.

## Actors

- **Customer** — chats publicly (no login); provides order/invoice reference inside the message.
- **Support agent** — authenticated; approves/rejects/escalates held drafts.

## Confirmed Decisions (from /clarify)

- KB scope = BOTH collections: `support_kb` (project_id=1, stub docs) + `tax` (project_id=2).
- Endpoint = `/support` unified; M1 `/query` stays separate.
- Hybrid output = single merged response.
- Customer access = public chat; identifier extracted from message text.
- Chat memory = backend-persisted (`conversations` table) via `session_id`.
- Review UX = hold + "an agent will follow up shortly"; draft hidden from customer.

---

## User Stories

### US1 — Knowledge question via chat (Priority: P1) 🎯 MVP
As a customer, I type a general/knowledge question (e.g. "What is your return
policy?") in the chatbot and get a grounded answer from the knowledge base.

**Independent test:** Send a policy/FAQ question with no order reference → router
picks `general_knowledge` → RAG answer returned with sources, in the question's language.

### US2 — Order issue / complaint via chat (Priority: P1)
As a customer, I describe an order/invoice problem (with a reference in the text)
and the system fetches my data, drafts a resolution, and either replies or holds
the reply for human review / escalates.

**Independent test:** Send "Where is my order ORD-2024-0001?" → router picks
`customer_issue` → M3 pipeline runs → reply (or "agent will follow up" when held).

### US3 — Hybrid question (Priority: P2)
As a customer, I ask something needing both policy knowledge and my own order data
(e.g. "My order ORD-2024-0001 is late — can I get a refund per your policy?") and
receive ONE merged answer.

**Independent test:** Send a mixed question → router picks `hybrid` → RAG context +
CRM data merged into a single coherent reply.

### US4 — Conversation memory (Priority: P3)
As a customer, my follow-up messages in the same session keep prior context.

**Independent test:** Two messages with the same `session_id`; the second uses
context from the first.

---

## Out of Scope

- Rewriting/migrating Mini-RAG internals into Wakeel's stack.
- M1 `/query` analytics endpoint.
- Production auth/SSO between services; response streaming.

## Tests Requested

Yes — integration tests at the end (Phase final), run/validated by Claude.

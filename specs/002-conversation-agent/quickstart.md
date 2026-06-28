# Quickstart: Conversation Agent (Small-Talk Route)

Validates the new `greeting` route end-to-end. The greeting path needs **only**
the backend + OpenAI (no Mini-RAG, no Postgres), so it is testable even when the
DB/RAG are unavailable.

## Prerequisites

- Wakeel backend running: `python -m uvicorn backend.main:app --port 8000`
- `OPENAI_API_KEY` set in `.env` (used by `llm_fast`).
- (Optional) Mini-RAG `:8001` only for the knowledge-route regression check.

## Scenario 1 — Friendly greeting (EN)

```bash
curl -s http://localhost:8000/api/v1/support \
  -H "Content-Type: application/json" \
  -d '{"query":"Hi"}'
```

Expected: `route == "greeting"`, a short friendly `final_response`,
`rag_sources == []`, `review_required == false`, `escalation_needed == false`.

## Scenario 2 — Friendly greeting (AR)

```bash
curl -s http://localhost:8000/api/v1/support \
  -H "Content-Type: application/json" \
  -d '{"query":"السلام عليكم، كيف حالك؟"}'
```

Expected: `route == "greeting"`, reply in Arabic, no sources, no review.

## Scenario 3 — Knowledge regression (must NOT be greeting)

```bash
curl -s http://localhost:8000/api/v1/support \
  -H "Content-Type: application/json" \
  -d '{"query":"What is your return policy?"}'
```

Expected: `route == "general_knowledge"` (grounded answer if Mini-RAG ingested).

## Scenario 4 — Issue regression (must NOT be greeting)

```bash
curl -s http://localhost:8000/api/v1/support \
  -H "Content-Type: application/json" \
  -d '{"query":"Where is my order ORD-2024-0001?"}'
```

Expected: `route == "customer_issue"`, CRM pipeline runs.

## Scenario 5 — Mixed greeting + question

```bash
curl -s http://localhost:8000/api/v1/support \
  -H "Content-Type: application/json" \
  -d '{"query":"Hi, what is your return policy?"}'
```

Expected: `route == "general_knowledge"` (the question wins over the greeting).

## Automated check

```bash
python scripts/test_conversation_agent.py
```

Asserts: greetings (AR/EN) → `greeting` with no sources/review; knowledge and
issue messages still route correctly (no regression). See
[contracts/router.md](./contracts/router.md) for the full routing table and
[data-model.md](./data-model.md) for state effects.

## UI check

Open `http://localhost:3000/m3`, send "Hi" → a friendly reply appears with a
**Greeting** route badge and no sources; send a policy question → **Knowledge**
badge; send an order question → **Issue** badge.

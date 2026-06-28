# Quickstart & Validation: Clarifying Follow-up for Missing Identifiers

Runnable scenarios that prove the feature works end-to-end. These are the same
journeys from `problem.md` that currently fail (escalate) and must pass (clarify)
after implementation.

## Prerequisites

Three services running (see repo run instructions):

```bash
# 1) Backend
uvicorn backend.main:app --reload                     # http://localhost:8000
# 2) Mini-RAG (separate venv)
cd MIni-RAG-APP-V1/src && ../.venv/Scripts/python -m uvicorn main:app --port 8001
# 3) Frontend (optional, for manual UI check)
cd frontend && npm run dev                            # http://localhost:3000
```

All calls below hit `POST http://localhost:8000/api/v1/support`. See
[contracts/support-endpoint.md](./contracts/support-endpoint.md) for the schema
and [data-model.md](./data-model.md) for the state fields.

## Scenario A — Ask, then answer (FR-001/002/005, SC-001)

Single conversation (`session_id="qa-A"`):

1. Send `{ "query": "Where is my order?", "session_id": "qa-A" }`
   - **Expect**: `clarification_pending=true`, `escalation_needed=false`; `final_response` asks for the order/invoice/customer number.
2. Send `{ "query": "ORD-2024-1567", "session_id": "qa-A" }`
   - **Expect**: a real status answer for ORD-2024-1567 (addresses the customer), `clarification_pending=false`.

## Scenario B — Arabic parity (FR-006, SC-003)

`session_id="qa-B"`:

1. `{ "query": "فين الأوردر بتاعي؟", "session_id": "qa-B" }` → clarifying question **in Arabic**.
2. `{ "query": "ORD-2024-1567", "session_id": "qa-B" }` → answer in Arabic.

## Scenario C — Ambiguous number (FR-011, D6)

1. `{ "query": "my number is 1567, where is it?", "session_id": "qa-C" }`
   - **Expect**: question asking whether 1567 is an order, invoice, or customer number (`missing_slot="ambiguous_type"`).

## Scenario D — Exhausted attempts → hand off (FR-007, SC-005)

`session_id="qa-D"`, reply without a reference each time:

1. "Where is my order?" → clarifying question (attempt 1)
2. "I don't know" → clarifying question (attempt 2)
3. "still don't know" → **`escalation_needed=true`**, handed to a human (no 3rd ask).

## Scenario E — No-regression guards

- Greeting: `{ "query": "hello" }` → friendly greeting, `clarification_pending=false` (SC-004).
- Knowledge: `{ "query": "What is your return policy?" }` → policy answer with `rag_sources`, never asks for a reference.
- Direct lookup: `{ "query": "Where is my order ORD-2024-1567?" }` → answers immediately, no clarification (FR-010).
- Billing with data: after supplying `INV-0001` for a dispute → `review_required=true` (FR-013 preserved).

## Scenario F — Not found (FR-008)

1. `{ "query": "status of DEL-999?", "session_id": "qa-F" }` (or supply DEL-999 when asked)
   - **Expect**: graceful "we couldn't find **DEL-999**, please verify or contact support" — the reference value appears; not a generic escalation.

## Automated check

Run the scenario script (added by this feature):

```bash
python scripts/test_clarification.py
```

**Expected**: all scenarios A–F pass; the escalation-on-missing-identifier
counts from the `problem.md` baseline drop to zero for the clarifiable cases.

## Done / acceptance

- Scenarios A, B, D, E pass (P1/P2 stories + guards).
- Scenario C passes (ambiguous-type).
- Scenario F passes (graceful not-found).
- Re-running the `problem.md` deep test shows ISSUE-1 and ISSUE-5 resolved.

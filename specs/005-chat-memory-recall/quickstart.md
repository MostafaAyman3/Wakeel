# Quickstart & Validation: Conversation Memory & Recall

Runnable scenarios proving recall works. These are the `problem.md` "Feature 005
baseline" failures that must pass after implementation.

## Prerequisites

```bash
uvicorn backend.main:app --reload                     # http://localhost:8000
cd MIni-RAG-APP-V1/src && ../.venv/Scripts/python -m uvicorn main:app --port 8001
cd frontend && npm run dev                            # http://localhost:3000  (for the reload check)
```

All API calls hit `POST http://localhost:8000/api/v1/support`. Multi-turn
scenarios MUST reuse one **UUID** `session_id` (see
[contracts/memory-behavior.md](./contracts/memory-behavior.md)).

## Scenario M1 — Recall a name (EN) — FR-002, SC-001

`session_id="<uuid>"`:
1. `{ "query": "Hi, my name is Kareem", "session_id": SID }` → friendly reply.
2. `{ "query": "what is my name?", "session_id": SID }`
   - **Expect**: reply contains "Kareem" (NOT a request for an order number).

## Scenario M2 — Recall a name (AR) — FR-007

1. `{ "query": "اسمي كريم", "session_id": SID2 }`
2. `{ "query": "اسمي ايه؟", "session_id": SID2 }` → reply contains "كريم", in Arabic.

## Scenario M3 — Cross-session isolation — FR-003, SC-002

1. State the name in `SID_A`.
2. In a fresh `SID_B`, ask "what is my name?" → assistant does **not** know it.

## Scenario M4 — Update wins — FR-004, SC-005

1. "my name is Kareem" → 2. "actually my name is Khaled" → 3. "what is my name?"
   - **Expect**: "Khaled".

## Scenario M5 — Unknown, no fabrication — FR-005, SC-003

1. New session, "what is my name?" with nothing stated.
   - **Expect**: says it doesn't have the name yet (does NOT invent one, does NOT
     ask for an order number).

## Scenario M6 — Cross-path recall — FR-006, SC-004

1. "my name is Kareem".
2. Ask a general-knowledge question ("what is your return policy?") → answered normally.
3. "what is my name?" → still "Kareem" (memory survived the knowledge turn).

## Scenario M7 — Reload persistence (manual, UI) — FR-010

1. In the browser, tell the assistant your name.
2. **Reload the page**, then ask "what is my name?" → it still knows.
3. Click **New chat**, ask again → it does not (fresh conversation).

## Automated check

```bash
python scripts/test_memory.py
```

**Expected**: M1–M6 pass. Re-running the `problem.md` Feature 005 baseline shows
M-1 and M-2 resolved.

## Done / acceptance

- M1, M2 (recall AR/EN), M4 (update), M5 (no fabrication), M6 (cross-path) pass.
- M3 (isolation) still passes (no regression).
- M7 verified manually in the UI.

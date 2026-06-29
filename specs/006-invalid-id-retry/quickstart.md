
# Quickstart: Invalid Identifier Retry & Guidance

Validation guide proving the retry-then-escalate behavior works end-to-end.
Implementation details live in [contracts/invalid-id-behavior.md](./contracts/invalid-id-behavior.md)
and [data-model.md](./data-model.md).

## Prerequisites

- Backend deps installed (existing project venv). No DB migration needed.
- A `session_id` is required to exercise the counter (it persists turns). Reuse the same
  `session_id` across requests to simulate one conversation; use a fresh one for isolation tests.
- Config defaults: `m3_invalid_id_max_attempts=3`, `m3_alt_lookup_enabled=False`.

## Run the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

## Scripted validation

```bash
python scripts/test_invalid_id.py
```

This script drives the graph directly (like `scripts/test_memory.py`) and asserts the scenarios
below. It should print a pass/fail line per scenario and exit non-zero on any failure.

## Manual validation (HTTP)

Send these to `POST /api/v1/m3/support` (adjust to the real route) with a shared `session_id`.
Use an order ID that does **not** exist (e.g. `ORD-000000`) to force "not found".

| # | Turn (same session) | Expected `final_response` | Expected flags |
|---|---------------------|---------------------------|----------------|
| 1 | "Where is my order ORD-000000?" | Friendly retry message | `invalid_id_pending=true`, not escalated |
| 2 | "ORD-000001" (also missing) | Friendly retry message (again) | attempt 2, not escalated |
| 3 | "ORD-000002" (also missing) | Escalation menu (re-enter / human / [phone-email off]) | menu shown, not escalated |
| 4a | a **valid** order ID | Real order status (normal answer) | streak reset; next invalid → attempt 1 |
| 4b | "talk to a human" | Hand-off message | `escalation_needed=true` → escalation_node |

## Scenarios the test suite must cover

1. **US1 / FR-004** — 1st and 2nd not-found IDs each return the retry message; count = 1 then 2.
2. **US2 / FR-005** — 3rd not-found ID returns the escalation menu (with only re-enter + human
   when `m3_alt_lookup_enabled=False`).
3. **US2.5 / FR-006** — a 4th not-found ID after the menu re-presents the menu (not the plain retry).
4. **US2.3 / FR-007** — replying "talk to a human" after the menu routes to `escalation_node` with
   the conversation context.
5. **US3 / FR-009 / SC-003** — a valid ID mid-streak returns the record and resets; a subsequent
   invalid ID starts again at the retry message (attempt 1).
6. **US4 / FR-011 / SC-004** — two failures in session A, then session B's first invalid ID is
   attempt 1 (menu not shown).
7. **FR-010** — a fresh `session_id` starts at count 0.
8. **FR-013 / SC-006** — an Arabic conversation receives the Arabic retry message and Arabic menu.
9. **FR-014 / FR-015 / SC-007 (no regression)**:
   - A message with **no** identifier still triggers Feature 004 clarification (not this feature).
   - A **valid** identifier still returns its record normally with no retry message.
   - RAG/knowledge and greeting paths are unaffected.

## Expected outcomes (success criteria)

- 100% of not-found IDs yield a retry message or the menu — never a generic error or fabricated
  record (SC-001).
- Attempts 1–2 → retry; attempt 3 → menu, every time (SC-002).
- The menu (path to human/alternate) is always reachable within 3 attempts (SC-005).
- No existing M3 scenario regresses (SC-007).

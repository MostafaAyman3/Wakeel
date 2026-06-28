# Tasks: Conversation Memory & Recall

**Input**: Design documents from `/specs/005-chat-memory-recall/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/memory-behavior.md](./contracts/memory-behavior.md), [quickstart.md](./quickstart.md)

**Tests**: Included — the feature explicitly asked for deep scenario testing; scenarios M1–M6 in quickstart.md drive `scripts/test_memory.py`.

**Organization**: Grouped by user story (priority order), each independently testable against the live `/support` endpoint with a reused UUID `session_id`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependency)
- **[Story]**: US1–US4 from spec.md
- Exact file paths included

## Path Conventions

Web app (per plan.md): agent graph under `agents/m3/`, FastAPI under `backend/`, frontend under `frontend/`, scenario scripts under `scripts/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the environment needed to validate recall.

- [X] T001 Verify backend :8000 and Mini-RAG :8001 are running and `POST /api/v1/support` accepts a `session_id` (per [quickstart.md](./quickstart.md)); confirm the `conversations` table persists turns.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Make the conversational reply path memory-aware and route recall questions to it. MUST complete before US1–US4 behave.

⚠️ No user-story behavior works until this phase is done.

- [X] T002 [P] Update `agents/prompts/greeting_agent.py` — instruct the reply to use the provided **conversation history** to recall facts the customer stated earlier (e.g., their name); answer recall questions ONLY from that history; if a fact was never stated, say so and offer to note it; NEVER invent (FR-005). Keep replies short and language-matched.
- [X] T003 Update `agents/m3/nodes/greeting_node.py` — read `state["chat_history"]` and include the recent turns (up to the loaded window) in the `llm_fast` call so the reply can recall earlier facts. Preserve the existing static AR/EN fallback and never-raise behavior. (Depends on T002.)
- [X] T004 [P] Update `agents/prompts/support_router.py` — define that questions answerable from the conversation itself (personal recall like "what's my name?", "what did I say?", chit-chat referencing earlier turns) route to `greeting`; an actionable record request still wins → `customer_issue`. Add AR/EN examples (fixes problem.md M-2).
- [X] T005 Verify `agents/m3/nodes/intent_router_node.py` passes enough recent `chat_history` to the router for the new distinction to work; widen the history slice only if needed. (Depends on T004.)

**Checkpoint**: "what's my name?" routes to the conversational path, which now sees the transcript.

---

## Phase 3: User Story 1 — Recall a fact the customer stated (Priority: P1) 🎯 MVP

**Goal**: "my name is Kareem" → later "what's my name?" answers "Kareem" (AR/EN), not an order-number request.

**Independent Test**: quickstart M1 + M2 — two turns on one `session_id`; the recall reply contains the stated name in the question's language.

- [X] T006 [US1] Confirm end-to-end recall on the conversational path for both languages (manual curl per [quickstart.md](./quickstart.md) M1/M2); adjust the T002 prompt wording if the model paraphrases instead of returning the name.
- [X] T007 [P] [US1] Create `scripts/test_memory.py` with Scenario M1 (EN recall) + M2 (AR recall) — reuse one UUID `session_id`; assert turn-2 reply contains the stated name and is NOT a clarification/order-number request.

**Checkpoint**: The reported bug ("بقوله اسمي و ارجع اساله مبيردش") is fixed and tested.

---

## Phase 4: User Story 2 — Use earlier context across paths (Priority: P2)

**Goal**: Memory stays available even when other paths (knowledge) handle a turn; earlier context is usable later.

**Independent Test**: quickstart M6 — state name, ask a knowledge question, then ask the name again → still recalled.

- [X] T008 [US2] Update `agents/m3/nodes/response_generator_node.py` to accept and lightly use `state["chat_history"]` so issue-path replies stay coherent with earlier turns (FR-006); keep current behavior when no history.
- [X] T009 [P] [US2] Add Scenario M6 (cross-path recall) to `scripts/test_memory.py` — name → general-knowledge question → recall name; assert the name still comes back.

**Checkpoint**: Recall is not lost when a non-greeting path handles an intervening turn.

---

## Phase 5: User Story 3 — Memory is private to each conversation (Priority: P2)

**Goal**: Facts never cross conversations.

**Independent Test**: quickstart M3 — name in session A; new session B asks the name → B does not know it.

- [X] T010 [US3] Confirm `backend/repositories/conversations.py` loads history strictly by `session_id` (no change expected); document the guarantee inline if missing.
- [X] T011 [P] [US3] Add Scenario M3 (cross-session isolation) to `scripts/test_memory.py` — assert a name stated in session A is unknown in session B (0 leaks, SC-002).

**Checkpoint**: Isolation proven and regression-guarded.

---

## Phase 6: User Story 4 — Updates and unknowns (Priority: P3)

**Goal**: Latest restated value wins; never fabricate an unknown.

**Independent Test**: quickstart M4 (update → Khaled) and M5 (unknown → declines without inventing).

- [X] T012 [US4] Ensure the T002 greeting prompt instructs: on a restated/changed fact use the most recent value (FR-004); on a never-stated fact, decline and offer to note it (FR-005) — refine wording if M4/M5 fail.
- [X] T013 [P] [US4] Add Scenarios M4 (update wins) + M5 (unknown, no fabrication) to `scripts/test_memory.py`.

**Checkpoint**: Memory stays trustworthy on edits and gaps.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Reload persistence (FR-010), regression validation, and docs.

- [X] T014 [P] Persist the session id in `frontend/hooks/useM3Support.ts` — read `session_id` from `localStorage` on mount (generate + store if absent), reuse it for every turn so memory survives a page reload; "New chat" generates a new id and overwrites storage (FR-010). Verify in the browser (quickstart M7).
- [X] T015 Run regression suites — `scripts/test_clarification.py`, `scripts/test_m3_sprint1.py`, `scripts/test_m3_sprint4.py` — and confirm no regressions from the router/greeting changes.
- [X] T016 Re-run the `problem.md` Feature 005 baseline; mark M-1 and M-2 Fixed with evidence; add an execution-log step in `docs/progress/agent_execution_log.md`.

---

## Dependencies & Execution Order

- **Setup (T001)** → **Foundational (T002–T005)** → user stories.
- **Foundational blocks everything**: T002/T003 (greeting reads history) + T004/T005 (router) must land before recall works.
- **Within Foundational**: T002 ∥ T004 (different files); T003 needs T002; T005 needs T004.
- **User Story order**: US1 (P1) → US2 (P2) → US3 (P2) → US4 (P3). US3 is mostly verification; US4 is prompt-wording + tests; US2 adds cross-path history.
- **Polish (T014–T016)** last; T014 (frontend) is independent and can be done in parallel with US2–US4; T016 needs all stories.

## Parallel Execution Examples

- **Foundational kickoff**: T002 (greeting prompt) ∥ T004 (router prompt); then T003 and T005.
- **Per-story tests**: T007, T009, T011, T013 are `[P]` (separate functions appended to `scripts/test_memory.py`).
- **Polish**: T014 (frontend) runs in parallel with the backend stories.

## Implementation Strategy

- **MVP = Phase 1 + 2 + US1 (T001–T007)**: the exact reported bug — name recall — works and is tested. Demo-ready.
- **Increment 2 (US2 + US3 + US4)**: cross-path memory, isolation guard, update/unknown correctness.
- **Increment 3 (Polish)**: reload persistence (FR-010) + regression + docs.

---

**Total tasks**: 16 · **Setup**: 1 · **Foundational**: 4 · **US1**: 2 · **US2**: 2 · **US3**: 2 · **US4**: 2 · **Polish**: 3

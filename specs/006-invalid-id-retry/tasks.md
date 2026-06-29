---
description: "Task list for Invalid Identifier Retry & Guidance (Feature 006)"
---

# Tasks: Invalid Identifier Retry & Guidance

**Input**: Design documents from `/specs/006-invalid-id-retry/`

**Prerequisites**: [plan.md](./plan.md) (required), [spec.md](./spec.md) (user stories), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/invalid-id-behavior.md](./contracts/invalid-id-behavior.md), [quickstart.md](./quickstart.md)

**Tests**: Test tasks ARE included — the spec's Testing section requests `scripts/test_invalid_id.py`.

**Organization**: Tasks are grouped by user story. This is a backend-only feature whose behavior is concentrated in one new node (`invalid_id_node`) plus a routing change; the shared scaffolding lives in the Foundational phase, and each user story adds/validates one slice of behavior.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)
- All paths are repository-relative.

## Path Conventions

Web app (FastAPI agent graph + Next.js). This feature touches only backend Python:
`agents/m3/…`, `backend/…`, `scripts/…`. No frontend change (per plan.md).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Configuration and constants the rest of the feature depends on.

- [x] T001 Add `m3_invalid_id_max_attempts: int = 3` and `m3_alt_lookup_enabled: bool = False` to the settings class in `backend/core/config.py`, next to the existing `m3_clarification_max_attempts` (research.md §7).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared state, counting helper, node skeleton, routing, and persistence wiring that ALL user stories build on.

**⚠️ CRITICAL**: No user-story behavior can be exercised until this phase is complete.

- [x] T002 Add the new fields to `M3State` in `agents/m3/schemas/m3_state.py`: `invalid_id_attempts: int`, `invalid_id_pending: bool`, `invalid_id_menu_shown: bool`, `alt_lookup_choice: Optional[str]` (per data-model.md), and seed their defaults (`0`, `False`, `False`, `None`) in `build_initial_state`.
- [x] T003 Create `agents/m3/nodes/invalid_id_node.py` with an `async def handle_invalid_id(state: M3State) -> dict` skeleton and a `_trailing_invalid_id_streak(chat_history)` helper that counts consecutive most-recent assistant turns tagged `metadata.invalid_id == True`, stopping at the first non-tagged assistant turn (research.md §2–§3, mirrors `clarification_node._count_prior_asks`). Never raises.
- [x] T004 Wire the node into the graph in `agents/m3/graphs/m3_graph.py`: register `invalid_id_node`, add a `_completeness_router` that returns `"invalid_id"` when `data_completeness == 0.0` AND `customer_identifier` has a non-empty `type`+`value`, `"escalate"` for other escalation cases, else `"classify"`; replace the existing `_escalation_router` edge on `completeness_check` with this router and add edge `invalid_id_node → END` (contracts §"Routing changes").
- [x] T005 Extend assistant-turn tagging in `backend/api/v1/m3_support.py`: build an `assistant_metadata` dict that sets `invalid_id=True` when `result["invalid_id_pending"]`, `invalid_id_menu=True` when `result["invalid_id_menu_shown"]`, and preserves the existing `clarification` tag (contracts §"API metadata tagging").

**Checkpoint**: Graph compiles; a not-found ID now reaches `invalid_id_node` (which still no-ops until US1) instead of escalating immediately.

---

## Phase 3: User Story 1 - Friendly retry on a wrong ID (Priority: P1) 🎯 MVP

**Goal**: A supplied-but-not-found ID returns the friendly retry message and increments the per-conversation count (attempts 1–2), instead of escalating.

**Independent Test**: With a shared `session_id`, send a non-existent order ID once, then again; both replies are the friendly retry message and the turn is not escalated.

### Tests for User Story 1

- [x] T006 [P] [US1] Add scenarios 1 (1st/2nd not-found → retry message, count 1 then 2) to a new `scripts/test_invalid_id.py`, driving the compiled graph directly like `scripts/test_memory.py`; assert `invalid_id_pending` and `final_response` wording, and that `escalation_needed` is False (quickstart.md scenario 1).

### Implementation for User Story 1

- [x] T007 [US1] Implement the retry branch in `agents/m3/nodes/invalid_id_node.py`: compute `attempt = streak + 1`; when `attempt < settings.m3_invalid_id_max_attempts`, return `final_response`/`draft_response` = the friendly retry message, `invalid_id_attempts=attempt`, `invalid_id_pending=True`, `invalid_id_menu_shown=False`, `escalation_needed=False`, plus response hygiene (`review_required=False`, `confidence_score=0.0`, `rag_sources=[]`) (contracts §node output table).
- [x] T008 [P] [US1] Add the canonical EN + static AR retry message templates and language selection (from `state["language"]`) in `agents/m3/nodes/invalid_id_node.py`; create optional `agents/prompts/invalid_id_agent.py` for tone adaptation with the static templates as the guaranteed fallback (contracts §"Message wording", research.md §6).

**Checkpoint**: First/second not-found IDs return the retry message in AR/EN; T006 passes. MVP is demonstrable.

---

## Phase 4: User Story 2 - Escalation menu after three failures (Priority: P1)

**Goal**: The 3rd consecutive failure stops the retry loop and presents the escalation menu; "talk to a human" routes to the existing hand-off; a further bad ID re-presents the menu; "search by phone/email" is omitted when the capability is off.

**Independent Test**: Cause three consecutive not-found IDs in one session; the 3rd reply is the escalation menu (re-enter / human / [phone-email omitted]). Replying "talk to a human" escalates.

### Tests for User Story 2

- [x] T009 [P] [US2] Add scenarios 2, 3, 4 to `scripts/test_invalid_id.py`: 3rd not-found → escalation menu (`invalid_id_menu_shown=True`, only two choices when `m3_alt_lookup_enabled=False`); a 4th not-found re-presents the menu (not the plain retry); "talk to a human" after the menu sets `escalation_needed=True` and reaches `escalation_node` with context (quickstart.md scenarios 2–4).

### Implementation for User Story 2

- [x] T010 [US2] Implement the escalation-menu branch in `agents/m3/nodes/invalid_id_node.py`: when `attempt >= settings.m3_invalid_id_max_attempts`, return the menu as `final_response`, `invalid_id_attempts=attempt`, `invalid_id_pending=True`, `invalid_id_menu_shown=True`, `escalation_needed=False`; this also covers re-presenting the menu on subsequent failures (FR-006), since the streak stays ≥ 3.
- [x] T011 [P] [US2] Add the EN + static AR escalation-menu templates in `agents/m3/nodes/invalid_id_node.py`, rendering choice 3 ("search by phone/email") only when `settings.m3_alt_lookup_enabled` is True, and renumbering when omitted (contracts §"Message wording", FR-008).
- [x] T012 [US2] Add the menu-choice pre-check in `agents/m3/nodes/input_parser_node.py`: when the most-recent assistant turn has `metadata.invalid_id_menu == True` and the new message is a human-agent request (small AR/EN intent set: "human", "agent", "representative", "موظف", "خدمة العملاء", or the index "2"), set `escalation_needed=True` (and skip identifier extraction) so the existing `_escalation_router`/`escalation_node` hands off with full context (contracts §"Routing changes", FR-007).

**Checkpoint**: 3rd failure shows the menu; human-agent choice hands off; menu re-presents on continued failures. US1 + US2 both work.

---

## Phase 5: User Story 3 - A valid ID clears the slate (Priority: P1)

**Goal**: A valid, found ID resets the streak and returns to normal flow; a later invalid ID starts again at attempt 1.

**Independent Test**: Fail one or two attempts, then send a valid ID; the record is returned and a subsequent invalid ID is treated as attempt 1 (retry message, not the menu).

### Tests for User Story 3

- [x] T013 [P] [US3] Add scenario 5 to `scripts/test_invalid_id.py`: after 1–2 failures, a valid ID returns the record (no `invalid_id_pending`), and a following not-found ID restarts at the retry message with count 1 (quickstart.md scenario 5, SC-003).

### Implementation for User Story 3

- [x] T014 [US3] Verify/confirm the reset is implicit (no explicit code): a successful lookup turn is NOT tagged `invalid_id`, so `_trailing_invalid_id_streak` (T003) returns 0 on the next failure. If T013 reveals the streak is not broken by a success turn, fix `_trailing_invalid_id_streak` in `agents/m3/nodes/invalid_id_node.py` to stop at the first non-tagged assistant turn (research.md §3, FR-009).

**Checkpoint**: Mid-streak success resets the count; T013 passes. US1–US3 work.

---

## Phase 6: User Story 4 - Each conversation counts independently (Priority: P2)

**Goal**: The count is scoped to one `session_id`; a new conversation starts at 0 and is unaffected by another.

**Independent Test**: Reach two failures in session A; in session B the first not-found ID is attempt 1 (retry message), not the menu.

### Tests for User Story 4

- [x] T015 [P] [US4] Add scenarios 6 and 7 to `scripts/test_invalid_id.py`: two failures in session A do not affect session B's first attempt (count 1, not menu); a fresh `session_id` starts at count 0 (quickstart.md scenarios 6–7, SC-004, FR-010/FR-011).

### Implementation for User Story 4

- [x] T016 [US4] Confirm session scoping holds end-to-end: `load_conversation_history(session_id)` already isolates per-session history, so the streak helper is naturally per-conversation. Add an assertion-only check (no code change expected) and, if T015 fails, ensure `invalid_id_node` reads only `state["chat_history"]` (never a global) in `agents/m3/nodes/invalid_id_node.py`.

**Checkpoint**: Counts never leak across conversations; all four stories pass.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Language coverage, no-regression verification, and docs.

- [x] T017 [P] Add the Arabic-language scenario (scenario 8) to `scripts/test_invalid_id.py`: an Arabic conversation receives the Arabic retry message and Arabic menu (FR-013, SC-006).
- [x] T018 [P] Add no-regression scenarios (scenario 9) to `scripts/test_invalid_id.py`: a no-identifier message still triggers Feature 004 clarification (not this feature); a valid identifier still returns its record with no retry message; greeting/RAG paths unaffected (FR-014, FR-015, SC-007).
- [ ] T019 [P] Run the existing suites to confirm no regression: `scripts/test_memory.py` (Feature 005) and any Feature 004 clarification tests still pass alongside `scripts/test_invalid_id.py`.
- [ ] T020 Run the full `quickstart.md` validation (manual HTTP table + `python scripts/test_invalid_id.py`) and confirm all success criteria SC-001…SC-007 hold.
- [x] T021 [P] Update structured logging in `agents/m3/nodes/invalid_id_node.py` to emit `invalid_id_attempt` events (attempt number, branch, language) consistent with the other nodes' logging style.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1, T001)**: No dependencies — start immediately.
- **Foundational (Phase 2, T002–T005)**: Depends on T001. **BLOCKS all user stories.**
- **User Stories (Phases 3–6)**: All depend on Foundational completion.
  - US1 (P1) → US2 (P1) build on the same node file, so run sequentially (shared file).
  - US3 (P1) and US4 (P2) mostly verify the counting helper from Foundational and can follow US1.
- **Polish (Phase 7)**: Depends on the user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Needs Foundational. The MVP slice.
- **US2 (P1)**: Builds on US1 (same node; attempt branch logic). Logically after US1.
- **US3 (P1)**: Validates reset; depends on the streak helper (T003) and US1's retry branch.
- **US4 (P2)**: Validates isolation; depends on the streak helper (T003). Independent of US2/US3 logic.

### Within Each User Story

- Write the test task first (it should fail), then implement.
- `invalid_id_node` retry branch (US1) before menu branch (US2) — same file, ordered.

### Parallel Opportunities

- Test-authoring tasks across stories (T006, T009, T013, T015, T017, T018) are `[P]` — different
  scenarios appended to the same script can be drafted independently, but commit serially to avoid
  edit conflicts on `scripts/test_invalid_id.py`.
- T008 and T011 (message templates) are `[P]` relative to routing/API tasks (different files).
- Polish tasks T017–T019, T021 are `[P]` (independent files/scenarios).

---

## Parallel Example: Foundational Phase

```bash
# After T001 (config), these touch different files and can proceed together:
Task: "T002 Add invalid-ID fields to M3State in agents/m3/schemas/m3_state.py"
Task: "T003 Create invalid_id_node skeleton + streak helper in agents/m3/nodes/invalid_id_node.py"
Task: "T005 Extend assistant metadata tagging in backend/api/v1/m3_support.py"
# T004 (graph wiring) depends on T002 and T003 existing.
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup (T001).
2. Phase 2: Foundational (T002–T005) — graph routes not-found IDs to the new node.
3. Phase 3: User Story 1 (T006–T008) — friendly retry message for attempts 1–2.
4. **STOP and VALIDATE**: not-found IDs now retry instead of escalating. Demo-ready MVP.

### Incremental Delivery

1. Setup + Foundational → not-found branch intercepted.
2. + US1 → retry message (MVP).
3. + US2 → escalation menu + human hand-off.
4. + US3 → reset on valid ID.
5. + US4 → per-conversation isolation.
6. Polish → AR coverage, no-regression, quickstart.

---

## Notes

- [P] = different files, no dependencies; serialize edits to the shared `scripts/test_invalid_id.py`.
- No DB migration and no frontend change (plan.md): the counter is derived from `chat_history` metadata.
- "Search by phone/email" lookup execution is intentionally deferred behind `m3_alt_lookup_enabled=False`; this feature only renders/omits the choice and routes the human-agent choice (research.md §5).
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.

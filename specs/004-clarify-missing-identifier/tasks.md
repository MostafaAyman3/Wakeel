# Tasks: Clarifying Follow-up for Missing Identifiers

**Input**: Design documents from `/specs/004-clarify-missing-identifier/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/support-endpoint.md](./contracts/support-endpoint.md), [quickstart.md](./quickstart.md)

**Tests**: Included — the feature explicitly asked for deep scenario testing; scenarios A–F in quickstart.md drive `scripts/test_clarification.py`.

**Organization**: Grouped by user story (priority order) so each can be implemented and validated independently against the live `/support` endpoint.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependency)
- **[Story]**: US1–US4 from spec.md
- Exact file paths included

## Path Conventions

Web app (per plan.md): backend agent graph under `agents/m3/`, FastAPI under `backend/`, scenario scripts under `scripts/`. No `frontend/` change required.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm environment and add the single tunable used by all stories.

- [x] T001 Verify the three dev services run (backend :8000, Mini-RAG :8001 in its venv, frontend :3000) per [quickstart.md](./quickstart.md) prerequisites; confirm `POST /api/v1/support` responds.
- [x] T002 [P] Add `m3_clarification_max_attempts: int = 2` to `backend/core/config.py` Settings (configurable limit per FR-007 / research D2).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared scaffolding every story depends on — state fields, prompt, the clarification node, and the graph branch. MUST complete before US1–US4.

⚠️ No user-story work can start until this phase is done.

- [x] T003 [P] Add clarification state fields to `agents/m3/schemas/m3_state.py` — `clarification_needed: bool`, `missing_slot: str | None`, `clarification_attempts: int`, `pending_value: str | None` — and initialize them in `build_initial_state` (defaults: `False`, `None`, `0`, `None`) per [data-model.md](./data-model.md).
- [x] T004 [P] Create clarification prompt `agents/prompts/clarification_agent.py` — bilingual (AR/EN) system prompt that, given `missing_slot` (`identifier` vs `ambiguous_type`) and any `pending_value`, produces ONE short friendly question asking for the exact reference (mirrors `agents/prompts/greeting_agent.py` style).
- [x] T005 Create `agents/m3/nodes/clarification_node.py` (`async def clarify(state)`) — compute `clarification_attempts` from `state["chat_history"]`; if attempts ≥ limit set `escalation_needed=True` (defer to escalation), else compose the AR/EN question via `llm_fast` + the T004 prompt, returning `final_response`, `draft_response`, `clarification_needed=True`, `review_required=False`, `escalation_needed=False`, with static AR/EN fallback on LLM error. (Depends on T003, T004.)
- [x] T006 Wire the clarification branch into `agents/m3/graphs/m3_graph.py` — register `clarification_node`; add a conditional edge after `input_parser` routing to `data_fetcher` (identifier present), `clarification_node` (clarification_needed), or the existing escalation path; route `clarification_node` → `END` for a normal ask and → `escalation_node` when it set `escalation_needed`. (Depends on T005.)
- [x] T007 Surface `clarification_pending: bool = False` in `backend/api/v1/m3_support.py` `SupportResponse` and populate it from the graph result per [contracts/support-endpoint.md](./contracts/support-endpoint.md). (Depends on T003.)

**Checkpoint**: Graph compiles with the new node; `clarification_pending` is returned. No behavior change yet until US1 flips input_parser.

---

## Phase 3: User Story 1 — Ask for the missing reference, then answer (Priority: P1) 🎯 MVP

**Goal**: A record-dependent question with no reference returns a clarifying question (not an escalation); supplying the reference next turn answers the original question.

**Independent Test**: quickstart Scenario A & B — turn 1 yields `clarification_pending=true` (AR/EN matched), turn 2 with the reference answers the order question.

- [x] T008 [US1] In `agents/m3/nodes/input_parser_node.py`, when no identifier is found, set `clarification_needed=True` + `missing_slot="identifier"` instead of `escalation_needed=True`/`error="no_identifier_found"` (keep escalation only as the exhausted-attempts fallback handled by the node).
- [x] T009 [US1] In `agents/m3/nodes/clarification_node.py`, implement the `missing_slot="identifier"` wording path — ask for the order/invoice/customer number, language-matched.
- [x] T010 [P] [US1] Add Scenario A + B to `scripts/test_clarification.py` (new file) — multi-turn with a shared `session_id`; assert turn-1 `clarification_pending=true`, `escalation_needed=false`, AR question for AR input; turn-2 answers ORD-2024-1567.

**Checkpoint**: US1 fully testable on its own — the core flow works end-to-end.

---

## Phase 4: User Story 2 — Ambiguous request gets a focused question (Priority: P2)

**Goal**: A bare number with no recognizable type prompts "is this an order, invoice, or customer number?" instead of escalating.

**Independent Test**: quickstart Scenario C — "my number is 1567" → question asking the reference type.

- [x] T011 [US2] In `agents/m3/nodes/input_parser_node.py`, detect a value present but type-unresolved (no `ORD-/INV-/CUST-` prefix) → set `missing_slot="ambiguous_type"` + `pending_value=<raw value>`, `clarification_needed=True`.
- [x] T012 [US2] In `agents/m3/nodes/clarification_node.py`, implement the `missing_slot="ambiguous_type"` wording path — ask which type the `pending_value` is (uses T004 prompt branch).
- [x] T013 [P] [US2] Add Scenario C to `scripts/test_clarification.py` — assert the ambiguous-number reply asks for the reference type.

**Checkpoint**: US2 works independently of US2/US4; reuses the US1 node.

---

## Phase 5: User Story 3 — Carry context across the conversation (Priority: P2)

**Goal**: The original question and a later bare-reference reply combine to answer the original question; a topic switch mid-clarification is handled on its own merits.

**Independent Test**: quickstart Scenario A/B turn-2 answer the original question; topic-switch (S16) routes the new message correctly without misapplying the pending reference.

- [x] T014 [US3] Verify/extend `agents/m3/nodes/intent_router_node.py` so a bare-reference reply inherits `customer_issue` from `chat_history` (already conversation-aware) and a clearly different message (e.g. a policy question) re-routes correctly; add the minimal guard if the bare value is misrouted.
- [x] T015 [US3] Ensure `agents/m3/nodes/input_parser_node.py` binds the reference supplied on the follow-up turn (including a `pending_value` resolved by a type answer) so `data_fetcher` runs against it.
- [x] T016 [P] [US3] Add multi-turn + topic-switch assertions to `scripts/test_clarification.py` — turn-2 answers the original question; a return-policy message during a pending clarification is answered as knowledge, not treated as the missing reference.

**Checkpoint**: Conversation coherence proven; no contextless replies.

---

## Phase 6: User Story 4 — Stop asking and hand off when needed (Priority: P3)

**Goal**: After 2 unsuccessful asks (or repeated unmatched references) the assistant stops and escalates with context.

**Independent Test**: quickstart Scenario D — third reference-less turn escalates (no 3rd ask).

- [x] T017 [US4] In `agents/m3/nodes/clarification_node.py`, finalize the attempt count derived from `chat_history` against `settings.m3_clarification_max_attempts`; at the limit set `escalation_needed=True` and route to the existing escalation path (FR-007). (Depends on T002, T005.)
- [x] T018 [US4] Confirm `agents/m3/nodes/escalation_node.py` summary includes the conversation context (original question + what was asked) for the human (FR-012) — extend the summary only if missing.
- [x] T019 [P] [US4] Add Scenario D to `scripts/test_clarification.py` — two clarifying asks then escalation on the third reference-less turn; assert no infinite loop.

**Checkpoint**: Loop is bounded; human safety net intact.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Spec requirements that span stories + the related `problem.md` fixes, and final regression validation.

- [x] T020 [P] Graceful "not found" (FR-008): in `agents/m3/nodes/data_completeness_node.py` / `response_generator_node.py`, when a *supplied* reference matches no record, return a message naming the reference ("couldn't find DEL-999, please verify…") instead of the generic escalation text (fixes `problem.md` ISSUE-2). Add Scenario F to `scripts/test_clarification.py`.
- [x] T021 [P] No-regression guards: extend `scripts/test_clarification.py` with Scenario E — greeting and general-knowledge never ask for a reference (SC-004), a first-message-with-valid-reference answers directly (FR-010), and a billing/refund case still returns `review_required=true` (FR-013).
- [x] T022 Re-run the `problem.md` deep test against the live system; confirm ISSUE-1 and ISSUE-5 are resolved and update `problem.md` statuses (Open → Fixed) with evidence.
- [x] T023 [P] Update `docs/progress/agent_execution_log.md` with a step documenting the clarification feature (files changed, decisions, test results).

---

## Dependencies & Execution Order

- **Setup (T001–T002)** → **Foundational (T003–T007)** → user stories.
- **Foundational blocks everything**: T003 (state) and T005 (node)/T006 (graph) must land before any story behaves.
- **User Story order**: US1 (P1) → US2 (P2) → US3 (P2) → US4 (P3). US2/US3/US4 each reuse the US1 node but are independently testable.
- **Within Foundational**: T003 ∥ T004 (parallel); T005 needs T003+T004; T006 needs T005; T007 needs T003.
- **Polish (T020–T023)** last; T022 needs all stories complete.

### Story dependency notes

- US1 is the MVP and the prerequisite *behavior* (flipping input_parser + the node's identifier path). US2 adds the ambiguous-type branch; US4 adds the attempt cap. US3 is mostly verification of existing session memory plus a guard.

## Parallel Execution Examples

- **Foundational kickoff**: T003 and T004 in parallel (different files), then T005 → T006, with T007 alongside T006.
- **Per-story tests**: T010, T013, T016, T019 are all `[P]` (append to the same script in coordinated sections, or separate test functions) and can be written as each story's implementation lands.
- **Polish**: T020, T021, T023 in parallel; T022 after them.

## Implementation Strategy

- **MVP = Phase 1 + 2 + US1 (T001–T010)**: delivers the headline behavior — reference-less questions get a clarifying follow-up and resolve on the next turn. Demo-ready on its own.
- **Increment 2 (US2 + US4)**: ambiguous-type handling + bounded attempts (robustness).
- **Increment 3 (US3 + Polish)**: conversation-coherence verification + graceful not-found + regression guards + docs.

---

**Total tasks**: 23 · **Setup**: 2 · **Foundational**: 5 · **US1**: 3 · **US2**: 3 · **US3**: 3 · **US4**: 3 · **Polish**: 4

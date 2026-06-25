---
description: "Task list for Knowledge-Path & Router Fixes"
---

# Tasks: Knowledge-Path & Router Fixes

**Input**: [plan.md](./plan.md), [spec.md](./spec.md),
decisions in [wakeel_agent_instructions.md](../../wakeel_agent_instructions.md)
**Tests**: Re-run `scripts/test_system_scenarios.py` + `scripts/test_conversation_agent.py`
after each milestone (validated by Claude). Baseline: HIGH 58/65, MEDIUM 13/23, 10/21 green.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different files, no incomplete dependency)
- **[Story]**: US1–US6 (Setup/Polish have no story label)
- Decisions are finalized; do NOT re-evaluate options.

## Path Conventions

Backend/agents in `agents/` + `backend/`; RAG service in `MIni-RAG-APP-V1/`
(separate service, restart after edits — no `--reload`).

---

## Phase 1: Setup

- [X] T001 Confirm all three services are running and baseline is reproducible: backend `:8000`, Mini-RAG `:8001`, support_kb ingested (`GET /api/v1/nlp/index/info/1` > 0). Re-run `python scripts/test_system_scenarios.py` to capture the pre-fix baseline.

**Checkpoint**: Baseline confirmed (knowledge turns held, AR answers in EN).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared state/signal both US1 and later stories depend on. The router
must emit `language` for every route before downstream nodes can use it.

- [X] T002 Add language detection in `agents/m3/nodes/intent_router_node.py` (`route_intent`): reuse the Arabic-range check used in `greeting_node`, set `language` in the returned state update so all downstream paths inherit it. (Fix 2 Part A)

**Checkpoint**: Router returns a concrete `language` (`ar`/`en`) for every message.

---

## Phase 3: User Story 1 — Knowledge answers reach the customer, in their language (P1) 🎯 MVP

**Goal**: `general_knowledge` answers are no longer held by the review gate and are
returned in the customer's language. (Fixes 1 + 2 — ship together.)
**Independent Test**: "What is your return policy?" → `review_required=false`, real
KB answer in `final_response`; "كم يستغرق الشحن؟" → Arabic answer.

- [X] T003 [US1] In `agents/m3/nodes/human_review_node.py` (`human_review_gate`), short-circuit at the top: if `state["route"]` is `greeting` or `general_knowledge` → return `{"review_required": False}` before any confidence/keyword checks. (Fix 1, Option A)
- [X] T004 [US1] In `agents/m3/nodes/response_generator_node.py` (`generate_response`/`_build_prompt_data`), when `language == "auto"` or empty, re-detect language from the customer message before building the prompt. (Fix 2 Part B guard)
- [X] T005 [US1] In `agents/prompts/support_router.py`, add short acknowledgements ("ok", "تمام", "👍") as explicit `greeting` examples (stabilizes intent; pairs with Fix 7). (same file as T009/T011 — sequential)
- [X] T006 [US1] Verify in `backend/api/v1/m3_support.py` that the review-hold message uses `result["language"]` (now populated by T002) so held messages are language-correct; adjust only if needed. 
- [X] T007 [US1] Restart backend; re-run `python scripts/test_system_scenarios.py` and confirm all `general_knowledge` turns: `review_required=false`, real KB answer, AR answers in Arabic. Also run `python scripts/test_conversation_agent.py` (greeting must stay green).

**Checkpoint** 🎯 MVP: knowledge route works bilingually end-to-end.

---

## Phase 4: User Story 2 — Multi-turn follow-ups keep route context (P2)

**Goal**: Follow-up questions inherit prior route via conversation history.
**Independent Test**: session "where is my order ORD-2024-0001?" then "when will it
arrive?" → both `customer_issue`.

- [X] T008 [US2] In `backend/api/v1/m3_support.py`, confirm `chat_history` (loaded when `session_id` present) is placed in the initial graph state the router can read; adjust if the router doesn't currently receive it.
- [X] T009 [US2] In `agents/prompts/support_router.py`, add a short "recent conversation" block to the prompt so follow-ups inherit context. (same file as T005/T011 — sequential)
- [X] T010 [US2] In `agents/m3/nodes/intent_router_node.py` (`route_intent`), read `state["chat_history"]` and include the last **3 turns** (hard cap N=3, default 3) in the router call. Document the "no `session_id` → single-turn" known limitation in the node docstring. (Fix 3, Option A)
- [X] T011 [US2] Restart backend; re-run the two-turn order session and confirm both turns route `customer_issue`. (extends `scripts/test_system_scenarios.py` Mona persona — already covered)

**Checkpoint**: multi-turn continuity restored (with `session_id`).

---

## Phase 5: User Story 3 — Knowledge answers carry source citations (P3)

**Goal**: `rag_sources` populated from retrieved chunk document names.
**Independent Test**: a knowledge answer returns `rag_sources` with ≥1 doc name.

- [X] T012 [US3] (Primary, Option A) In `MIni-RAG-APP-V1/src/controllers/NLPController.py` (`answer_rag_question`), also return the retrieved chunks' document/source names (already retrieved internally for the prompt).
- [X] T013 [US3] In `MIni-RAG-APP-V1/src/routes/nlp.py` (`/index/answer/{project_id}`), include those source names in the JSON response. (depends on T012)
- [X] T014 [US3] In `backend/services/rag_client.py` (`rag_answer`), map the returned source names into the `sources` field. (depends on T013)
- [X] T015 [US3] Restart Mini-RAG + backend; re-run scenarios and confirm knowledge answers return `rag_sources` (e.g. `["return_policy.txt"]`). FALLBACK (Option B) only if Mini-RAG edits are blocked: in `agents/m3/nodes/rag_node.py`, call `/index/search/{project_id}` in parallel with `/answer` for sources.

**Checkpoint**: citations appear on knowledge answers (UI Sources line).

---

## Phase 6: User Story 4 — Faster knowledge responses (P4)

**Goal**: Lower knowledge-turn latency. **Only after US1 is confirmed working.**
**Independent Test**: knowledge-turn latency drops from the 11–17s range.

- [X] T016 [US4] In `agents/m3/nodes/response_generator_node.py` (`generate_response`), when `route == general_knowledge`, use `llm_fast` (gpt-4o-mini) instead of `llm_primary` (gpt-4o). (Fix 6, Option A; depends on US1 = T003+T004 confirmed). (same file as T004 — sequential)
- [X] T017 [US4] Restart backend; re-run scenarios and record knowledge-turn timings vs the baseline.

**Checkpoint**: knowledge latency meaningfully reduced, answers still correct.

---

## Phase 7: User Story 5 — Audit captures issue_type on escalation (P5)

**Goal**: Escalation summary records the issue category. Customer-facing impact: none.
**Independent Test**: refund-on-missing-invoice escalation shows
`issue_type=refund_request` in the escalation summary.

- [X] T018 [P] [US5] In `agents/m3/nodes/escalation_node.py` (no-data escalation branch), add a lightweight keyword-based classification to set `issue_type` before building the escalation summary/audit. (Fix 5)
- [X] T019 [US5] Restart backend; re-run Khaled's refund scenario and confirm `issue_type=refund_request` in the escalation summary. (depends on T018)

**Checkpoint**: escalation audit trail labelled.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T020 [P] Update test expectations for short acknowledgements: in `scripts/test_system_scenarios.py` (and `scripts/test_conversation_agent.py` if present), expect "ok" → `greeting`. (Fix 7 calibration)
- [X] T021 [P] Complete tax ingestion (ops, Fix 8): raise the ingest client timeout to 600s OR batch the push in `scripts/ingest_mini_rag.py`, then run `python scripts/ingest_mini_rag.py --only tax`; verify `GET /api/v1/nlp/index/info/2` > 0.
- [X] T022 Final full validation: re-run `python scripts/test_system_scenarios.py` and confirm the expected outcome (~19–20/21 turns green; knowledge 6/6; AR 3/3; sources populated). Update `docs/testing/system_analysis_and_solutions.md` with the post-fix results.

---

## Dependencies & Execution Order

### Phase / milestone order
1. Setup (T001) → 2. Foundational (T002) → 3. **US1 (T003–T007) = MVP, ship Fix1+Fix2+Fix7 together** → 4. US2 (T008–T011) → 5. US3 (T012–T015) → 6. US4 (T016–T017, after US1) → 7. US5 (T018–T019, parallelizable) → 8. Polish (T020–T022).

### Same-file sequencing (cannot be [P])
- `agents/prompts/support_router.py`: T005 → T009 (and any router-prompt edit)
- `agents/m3/nodes/response_generator_node.py`: T004 → T016
- `agents/m3/nodes/intent_router_node.py`: T002 → T010
- `MIni-RAG-APP-V1/...` chain: T012 → T013 → T014

### Parallel opportunities
- US5 (T018) can proceed in parallel with US2/US3/US4.
- Polish T020 and T021 are independent ([P]).

### Critical constraints (from instructions)
- Fix 1 + Fix 2 ship together (do not ship one without the other).
- Fix 6 (T016) only after US1 confirmed.
- Router history capped at N=3 (default 3).
- Services run without `--reload` → restart before each re-test.

---

## Implementation Strategy

### MVP first
Setup → Foundational → US1 → **STOP & validate**: knowledge route returns real
bilingual answers, greeting unregressed. This is the highest-value increment.

### Incremental delivery
US1 (knowledge MVP) → US2 (continuity) → US3 (citations) → US4 (latency) →
US5 (audit) → Polish (calibration + tax ops + final validation). Each milestone is
independently testable via the scenario suite.

---

## Notes

- No new dependencies, no DB migration.
- Rejected options (out of scope): S1-B, S1-C, S3-B, S3-C, S6-B, S6-C.
- Commit grouping: Fix 1+2+7 in one commit; others per milestone.

## Post-implementation result (2026-06-25)

- All 22 tasks complete. Final `scripts/test_system_scenarios.py`: **HIGH 65/65,
  MEDIUM 23/23, 21/21 turns green** (baseline 58/65, 13/23, 10/21).
- T021 tax ingest verified: `GET /api/v1/nlp/index/info/2` → 884 vectors.
- **Extra fix beyond the planned 8**: validation re-runs exposed a flaky router —
  `gpt-4o-mini` non-deterministically mis-routed Arabic knowledge/greeting turns to
  `customer_issue`. Switched the intent router to `gpt-4o` (`llm_primary`) in
  `agents/m3/nodes/intent_router_node.py`; routing is now deterministic and correct.
  See `docs/testing/system_analysis_and_solutions.md` §6 for the full write-up.

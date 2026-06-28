---
description: "Task list for Unified Support Chatbot (Mini-RAG × M3 CRM)"
---

# Tasks: Unified Support Chatbot (Mini-RAG × M3 CRM)

**Input**: Design documents from `/specs/001-unified-support-chatbot/`
**Prerequisites**: plan.md (required), spec.md (required)
**Tests**: Integration tests included in the final phase (run/validated by Claude).
**Organization**: Tasks grouped by user story for independent implementation & testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 / US2 / US3 / US4 (Setup, Foundational, Polish have no story label)
- Exact file paths are included in each task.

## Path Conventions

Web app: backend at `backend/`, agents at `agents/`, frontend at `frontend/`,
RAG microservice at `MIni-RAG-APP-V1/` (separate service — run, not modified).

---

## Phase 1: Setup (Shared Prerequisites)

**Purpose**: Stand up the RAG service, seed knowledge, add config, fix blocking bugs.

- [ ] T001 Run Mini-RAG locally: copy `MIni-RAG-APP-V1/src/.env.example` → `MIni-RAG-APP-V1/src/.env`, fill LLM/OCR/Supabase keys, start `uvicorn main:app`; verify `GET /api/v1/nlp/index/info/1` responds.
- [X] T002 [P] Create stub support-KB docs (return/shipping policy, FAQ, warranty) in AR+EN as `data/support_kb/*.txt` (clearly marked PLACEHOLDER).
- [ ] T003 Ingest both collections via Mini-RAG `upload → process → index/push`: tax docs as project_id=2, `data/support_kb/*` as project_id=1; verify `index/info/1` and `index/info/2` report >0 vectors. (depends on T001, T002)
- [X] T004 [P] Add config keys `MINI_RAG_BASE_URL`, `RAG_SUPPORT_KB_PROJECT_ID=1`, `RAG_TAX_PROJECT_ID=2` in `backend/core/config.py` and `.env.example`.
- [X] T005 [P] Fix language bug in `agents/m3/nodes/response_generator_node.py`: include the customer message in `_build_prompt_data` and add explicit "Respond ONLY in {lang}".
- [X] T006 [P] Fix review-keyword false positive in `agents/m3/nodes/human_review_node.py`: remove bare `"by"`/`"within"`; use word-boundary / phrase matching.

**Checkpoint**: Mini-RAG serving both collections; config + node bugs fixed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Router + RAG client + state + public endpoint + graph entry. **No user story can be implemented until this is complete.**

- [X] T007 Create RAG HTTP client `backend/services/rag_client.py`: `async def rag_answer(query, project_id, chat_history) -> dict` calling `POST {MINI_RAG_BASE_URL}/api/v1/nlp/index/answer/{project_id}` (httpx, timeout, try/except → `{answer, sources, ok}`). (depends on T004)
- [X] T008 [P] Extend `agents/m3/schemas/m3_state.py`: add `route`, `route_confidence`, `rag_context`, `rag_sources`, `rag_collection`; add defaults in `build_initial_state`.
- [X] T009 [P] Create router prompt `agents/prompts/support_router.py`: AR/EN system prompt → `general_knowledge | customer_issue | hybrid` + target `collection`.
- [X] T010 Create router node `agents/m3/nodes/intent_router_node.py` (model on `agents/m1/nodes/intent_classifier_node.py`): GPT-4o-mini structured output → set `route`, `route_confidence`, `rag_collection`; low confidence → default `customer_issue`. (depends on T008, T009)
- [X] T011 Make `POST /support` public in `backend/api/v1/m3_support.py`: remove JWT dependency from the customer path; keep `/approve`, `/reject`, `/escalate` JWT-protected.
- [X] T012 Wire router as graph entry in `agents/m3/graphs/m3_graph.py`: add `intent_router` (entry); `customer_issue → input_parser → …` (existing flow); `general_knowledge → rag_node → response_generator`; `hybrid → rag_node → input_parser → …`. Graph compiles. (depends on T010)
- [X] T013 Frontend chatbot shell: replace `CustomerInputForm` in `frontend/app/m3/page.tsx` with chat using `frontend/components/chat/{ChatInterface,ChatInput,MessageList,MessageBubble}.tsx`; wire `frontend/hooks/useM3Support.ts` + `frontend/lib/api.ts` to public `/support`. (depends on T011)

**Checkpoint**: Chat works end-to-end; all messages currently flow to the issue pipeline.

---

## Phase 3: User Story 1 — Knowledge question via chat (Priority: P1) 🎯 MVP

**Goal**: A knowledge question returns a grounded RAG answer with sources, in the question's language.
**Independent Test**: Send "What is your return policy?" (no order ref) → `route=general_knowledge` → KB answer + sources.

- [X] T014 [US1] Create RAG node `agents/m3/nodes/rag_node.py`: `async def run_rag(state)` picks collection from `rag_collection`/route, calls `rag_client.rag_answer`, writes `rag_context` + `rag_sources`; never raises. (depends on T007)
- [X] T015 [US1] Wire `general_knowledge → rag_node → response_generator` in `agents/m3/graphs/m3_graph.py`. (depends on T012, T014)
- [X] T016 [US1] In `agents/m3/nodes/response_generator_node.py`, handle knowledge-only answers using `rag_context` (answer + KB citation, no fabrication). (depends on T014; same file as T005 — sequential)
- [X] T017 [US1] Add `route` and `rag_sources` to `SupportResponse` in `backend/api/v1/m3_support.py` and map from graph result. (depends on T011)
- [X] T018 [US1] Frontend: render knowledge answer with a `route` badge and `rag_sources` list in `frontend/components/m3/*` / chat components. (depends on T013, T017)

**Checkpoint**: Knowledge Q&A works through the chatbot — MVP deliverable.

---

## Phase 4: User Story 2 — Order issue / complaint via chat (Priority: P1)

**Goal**: An order issue runs the M3 agent; safe replies send, risky ones are held with a waiting message, escalations surface.
**Independent Test**: "Where is my order ORD-2024-0001?" → `route=customer_issue` → reply, or "an agent will follow up shortly" when `review_required`.

- [X] T019 [US2] Review-hold shaping in `backend/api/v1/m3_support.py`: when `review_required=True` and not escalated, customer-facing field returns neutral "an agent will follow up shortly" (AR/EN); keep the draft in `transparency_data` for agents only. (depends on T017; same file — sequential)
- [X] T020 [US2] Frontend: render normal reply, the waiting message, and escalation state in chat (`frontend/components/m3/*`). (depends on T018; same area — sequential)

**Checkpoint**: Issue resolution + human-review hold + escalation visible in chat.

---

## Phase 5: User Story 3 — Hybrid question (Priority: P2)

**Goal**: A mixed question returns ONE merged answer combining KB knowledge + the customer's CRM data.
**Independent Test**: "My order ORD-2024-0001 is late — can I get a refund per your policy?" → `route=hybrid` → single merged reply.

- [X] T021 [US3] RAGEnrich in `agents/m3/nodes/context_builder_node.py`: when `rag_context` present, add `context["knowledge"] = rag_context`. (depends on T014)
- [X] T022 [US3] Wire `hybrid → rag_node → input_parser → …` in `agents/m3/graphs/m3_graph.py` (carry `rag_context` through state). (depends on T015; same file — sequential)
- [X] T023 [US3] In `agents/m3/nodes/response_generator_node.py`, add a "Knowledge base" section to the prompt and merge KB + CRM into one answer. (depends on T016, T021; same file — sequential)

**Checkpoint**: Hybrid merged answers work end-to-end.

---

## Phase 6: User Story 4 — Conversation memory (Priority: P3)

**Goal**: Follow-up messages in the same session keep prior context.
**Independent Test**: Two messages with the same `session_id`; the second uses context from the first.

- [X] T024 [US4] Create `backend/repositories/conversations.py`: load prior turns and append new turns to the existing `conversations` table.
- [X] T025 [US4] In `backend/api/v1/m3_support.py`, add optional `session_id` to `SupportRequest`; load history → pass as `chat_history` into the graph and `rag_client`; append user turn + final answer after the run. (depends on T024, T019; same file — sequential)

**Checkpoint**: Multi-turn context retained across messages.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation (by Claude) and docs.

- [X] T026 [P] Create E2E test `scripts/test_unified_support.py`: POST `/support` for knowledge / issue / hybrid; assert `route`, answer language, `rag_sources`, review flags.
- [ ] T027 Manual UI pass (Claude): run Mini-RAG + backend + frontend; send the 3 message types; verify replies, sources, waiting/escalation states.
- [X] T028 [P] Update `docs/architecture/` (plan + this feature) with any deltas found during testing.

---

## Dependencies & Execution Order

### Phase order
1. **Setup (P1)** → 2. **Foundational (P2)** → 3. **US1** → 4. **US2** → 5. **US3** → 6. **US4** → 7. **Polish**.
- Setup has no dependencies. Foundational depends on Setup. All user stories depend on Foundational. Polish depends on the stories being built.

### User story independence
- **US1 (P1)**: after Foundational; self-contained (knowledge route).
- **US2 (P1)**: after Foundational; the `customer_issue` route already exists from T012 — US2 adds hold/escalation UX.
- **US3 (P2)**: after US1 (reuses `rag_node` + response generator).
- **US4 (P3)**: after Foundational; independent of US1–US3 behavior.

### Same-file sequencing (cannot be [P] together)
- `agents/m3/nodes/response_generator_node.py`: T005 → T016 → T023
- `agents/m3/graphs/m3_graph.py`: T012 → T015 → T022
- `backend/api/v1/m3_support.py`: T011 → T017 → T019 → T025

---

## Parallel Opportunities

- **Setup**: T002, T004, T005, T006 run in parallel (different files).
- **Foundational**: T008 and T009 run in parallel; T007 parallel with both.
- **Polish**: T026 and T028 run in parallel.

---

## Implementation Strategy

### MVP first (US1 only)
1. Phase 1 Setup → 2. Phase 2 Foundational → 3. Phase 3 US1.
4. **STOP and VALIDATE**: knowledge Q&A in the chatbot. Demo.

### Incremental delivery
Foundation → US1 (knowledge, MVP) → US2 (issues+hold) → US3 (hybrid) → US4 (memory).
Each story is independently testable and adds value without breaking prior ones.

---

## Notes

- Mini-RAG is a separate running service — no Wakeel code lives in it.
- [P] = different files, no incomplete dependencies.
- Each [Story] task maps to a user story for traceability.
- Commit after each task or logical group.
- Stop at any checkpoint to validate the story independently.
- Claude runs the final integration + UI validation (T026–T027).

## Remaining Manual Steps

- **T001**: User must copy `MIni-RAG-APP-V1/src/.env.example` → `.env`, fill in keys, and start `uvicorn main:app`.
- **T003**: After T001 is done, ingest `data/support_kb/*` as project_id=1 and tax docs as project_id=2 via Mini-RAG's upload/process/push endpoints.
- **T027**: Run both servers + frontend (`npm run dev`) and send the 3 message types manually to confirm end-to-end behaviour.

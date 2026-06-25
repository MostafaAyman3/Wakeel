---
description: "Task list for Conversation Agent (Small-Talk Route)"
---

# Tasks: Conversation Agent (Small-Talk Route)

**Input**: Design documents from `/specs/002-conversation-agent/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/router.md, quickstart.md
**Tests**: One integration test script at the end (run/validated by Claude), per plan.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete dependencies)
- **[Story]**: US1 / US2 / US3 (Setup, Foundational, Polish have no story label)
- Exact file paths included.

## Path Conventions

Extends feature 001 (Unified Support Chatbot): agents at `agents/`, backend at
`backend/`, frontend at `frontend/`. No new service. No migration.

---

## Phase 1: Setup

**Purpose**: No new dependencies or scaffolding — confirm the feature-001 graph
imports cleanly before editing.

- [x] T001 Sanity check: from repo root, confirm `agents/m3/graphs/m3_graph.py` compiles and the current 3-route router imports (run `python -c "from agents.m3.graphs.m3_graph import build_support_graph; build_support_graph()"`).

**Checkpoint**: Baseline graph builds.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Teach the router the 4th route. ALL user stories depend on this.

- [x] T002 Extend the `route` Literal to include `greeting` in `agents/m3/schemas/m3_state.py` (type: `Literal["greeting","general_knowledge","customer_issue","hybrid"]`); keep `build_initial_state` default `route="customer_issue"`.
- [x] T003 Update the router prompt in `agents/prompts/support_router.py`: add the `greeting` route, its definition (pure social/small-talk, AR+EN examples), the conservative precedence rules (actionable request wins; low confidence → `customer_issue`, never `greeting`), and set `collection=none` for greeting. Mirror the table in `specs/002-conversation-agent/contracts/router.md`.
- [x] T004 Update `agents/m3/nodes/intent_router_node.py`: add `"greeting"` to `_VALID_ROUTES`; keep the `< 0.5` confidence fallback to `customer_issue` (NOT greeting).

**Checkpoint**: Router can emit `greeting`; graph still compiles (greeting not yet wired → would fall through). Do not ship until Phase 3 wires it.

---

## Phase 3: User Story 1 — Friendly small-talk reply (Priority: P1) 🎯 MVP

**Goal**: A social message gets a short friendly reply in the same language, with
no RAG/CRM lookup, no sources, no review, no escalation.
**Independent Test**: POST `/support` `{"query":"Hi"}` → `route=greeting`, friendly
`final_response`, `rag_sources=[]`, `review_required=false`, `escalation_needed=false`.

- [x] T005 [P] [US1] Create `agents/prompts/greeting_agent.py`: a short bilingual (AR/EN) system prompt for a friendly support chatbot — 1–2 sentences, warm, ends by inviting the customer to ask their question / describe their issue; "reply ONLY in {lang}"; no data, no markdown.
- [x] T006 [US1] Create `agents/m3/nodes/greeting_node.py`: `async def greet(state)` → detect/read `language`, call `llm_fast` with the greeting prompt + customer message, return `{draft_response, final_response (same), review_required: False, escalation_needed: False, confidence_score: 1.0, rag_sources: []}`. Never raises; on LLM failure return a static friendly fallback (AR/EN). (depends on T005)
- [x] T007 [US1] Wire the greeting branch in `agents/m3/graphs/m3_graph.py`: register `greeting_node`; in `_route_from_intent` add `greeting → "greet"`; add conditional edge target `greeting_node`; `add_edge("greeting_node", END)`. Greeting must NOT pass through `rag_node`, the CRM pipeline, or `human_review_gate`. (depends on T002, T004, T006)
- [x] T008 [US1] In `backend/api/v1/m3_support.py`, confirm `SupportResponse.route` accepts `"greeting"` (it's a free `str` default "customer_issue"); update the field comment to list `greeting | general_knowledge | customer_issue | hybrid`. No logic change needed since greeting sets review/escalation false. (depends on T007)
- [x] T009 [P] [US1] Frontend: add `"greeting"` to `RouteType` in `frontend/types/m3.ts`, and a badge label ("Greeting") + color in `frontend/components/chat/MessageBubble.tsx` (`ROUTE_LABEL`/`ROUTE_COLOR`). (depends on T007)

**Checkpoint**: "Hi" / "السلام عليكم" → friendly reply with a Greeting badge; MVP done.

---

## Phase 4: User Story 2 — Knowledge questions still reach RAG (Priority: P1)

**Goal**: Adding greeting must not steal knowledge traffic.
**Independent Test**: "What is your return policy?" → `route=general_knowledge`;
"Hi, what is your return policy?" → `route=general_knowledge` (question wins).

- [x] T010 [US2] Verify/strengthen precedence in `agents/prompts/support_router.py`: add explicit mixed-message examples ("Hi, what is your return policy?" → general_knowledge) so greeting never overrides a knowledge question. (same file as T003 — sequential)

**Checkpoint**: Knowledge route unaffected by the new greeting route.

---

## Phase 5: User Story 3 — Issues/complaints still reach the CRM agent (Priority: P1)

**Goal**: A complaint must never be treated as small-talk.
**Independent Test**: "Where is my order ORD-2024-0001?" → `route=customer_issue`;
"Hello, I'm not happy with you" → `customer_issue` (not greeting).

- [x] T011 [US3] Verify/strengthen precedence in `agents/prompts/support_router.py`: add complaint-with-greeting examples ("Hello, I want a refund for INV-5" → customer_issue) and reaffirm low-confidence → `customer_issue`. (same file as T003/T010 — sequential)

**Checkpoint**: Issue/complaint route unaffected; no real need dropped into greeting.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Automated validation (by Claude) and docs.

- [x] T012 [P] Create `scripts/test_conversation_agent.py`: POST `/support` for greeting (EN+AR), knowledge, issue, and mixed greeting+question; assert `route`, greeting reply language, `rag_sources==[]` and `review_required==false` for greetings, and no regression on knowledge/issue routing. (per quickstart.md scenarios)
- [x] T013 Manual UI pass (Claude): open `http://localhost:3000/m3`; send "Hi", a policy question, and an order question; verify Greeting/Knowledge/Issue badges and that greeting shows no sources/waiting message.
- [x] T014 [P] Update `docs/architecture/m3_system_architecture.md` (and feature-001 plan if needed) to show the 4th `greeting` route in the router/graph diagram + node list.

---

## Dependencies & Execution Order

### Phase order
1. Setup (T001) → 2. Foundational (T002–T004) → 3. US1 (T005–T009) → 4. US2 (T010) → 5. US3 (T011) → 6. Polish (T012–T014).
- Foundational blocks all stories (shared router). US1 delivers the MVP. US2/US3 are guardrail/regression refinements on the shared router prompt. Polish depends on the stories.

### Same-file sequencing (cannot be [P] together)
- `agents/prompts/support_router.py`: T003 → T010 → T011
- `agents/m3/graphs/m3_graph.py`: T007 (single edit)

### Parallel opportunities
- T005 and T009 are [P] (different files) within US1; T006/T007/T008 are sequential (graph + node chain).
- T012 and T014 are [P] in Polish.

---

## Implementation Strategy

### MVP first (US1)
Setup → Foundational → US1 → **STOP and validate**: send "Hi" and confirm a
friendly Greeting-badged reply with no sources/review. Demo.

### Incremental delivery
US1 (greeting works) → US2 (knowledge guardrail) → US3 (issue guardrail) → Polish
(automated test + docs). Each step is independently testable; greeting logic needs
neither Postgres nor Mini-RAG, so it is validatable even while feature-001
ingestion waits on the DB migration.

---

## Notes

- No new dependencies, no DB migration, no new service.
- Greeting path is terminal: `intent_router → greeting_node → END`.
- [P] = different files, no incomplete dependencies.
- Commit after each task or logical group.

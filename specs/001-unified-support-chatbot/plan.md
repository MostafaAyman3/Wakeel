# Implementation Plan — Unified Support Chatbot: Mini-RAG × M3 CRM

> **Goal:** Merge the existing **Mini-RAG-APP-V1** (RAG + OCR engine) with the
> **M3 CRM agent** behind one `/support` chat endpoint. A customer chats with the
> system; an **Intent Router** decides whether the message is a *knowledge*
> question (→ Mini-RAG), a *customer issue/complaint* (→ M3 agent), or *both*
> (→ hybrid merged answer). The frontend becomes a **chatbot**.
>
> **Status:** PLAN ONLY — no code yet. Claude will run/test at the end.
> **Build constraint:** every task is small, explicit, and self-contained so a
> cheaper model can implement it without ambiguity.

---

## 1. Core Strategy — REUSE, don't rebuild

Mini-RAG-APP-V1 is already a complete, working FastAPI RAG service with:
- Provider-factory pattern (LLM: OpenAI/Cohere/Gemini · OCR: Mistral · VectorDB: Supabase pgvector / Qdrant).
- `project_id`-based **collections** (one collection per knowledge base).
- Endpoints: `upload → process (OCR+chunk) → index/push → search → answer`.
- RAG answer with **chat_history** support and AR/EN prompt templates.

**Decision: run Mini-RAG as a standalone microservice.** M3 calls it over HTTP.
We do **not** import its code or merge its dependencies into Wakeel.

Why (this is the cheap-model-friendly choice):
- Zero dependency conflicts (Mini-RAG uses `supabase-py`, `qdrant-client`,
  `mistralai`; Wakeel uses SQLAlchemy async + LangGraph).
- Reuses OCR, chunking, multi-LLM, and chat_history **as-is** — no rewrite.
- The only new RAG code in Wakeel is a thin **HTTP client** + one graph node.

```
┌──────────────────────────┐         HTTP          ┌──────────────────────────┐
│  Wakeel (M3 CRM)          │  ──────────────────►  │  Mini-RAG-APP-V1 service  │
│  /support + LangGraph     │   POST /nlp/index/    │  OCR · chunk · pgvector   │
│  rag_node → RagClient     │   answer/{project_id} │  /answer returns RAG text │
└──────────────────────────┘  ◄──────────────────  └──────────────────────────┘
```

---

## 2. Target Architecture

```
Customer (chatbot UI) ─► POST /support ─► Intent Router (LangGraph entry)
                          ├─ general_knowledge ─► rag_node ──► RagClient → Mini-RAG /answer ─┐
                          ├─ customer_issue    ─► input_parser → … → response_generator ─────┤
                          └─ hybrid            ─► rag_node + agent pipeline (merge) ──────────┘
                                                                                              ▼
                                              ResponseGenerator (uses rag_context + CRM data)
                                                                                              ▼
                                              HumanReviewGate ─► approve / reject / escalate
```

Mini-RAG collections (its `project_id`):
| project_id | Collection | Content |
|---|---|---|
| `1` | `support_kb` | return/shipping policy, FAQ, warranty (**stub docs in S0.T3**, real later) |
| `2` | `tax` | existing tax law docs |

---

## 3. Confirmed Decisions

1. **KB scope = BOTH** — two Mini-RAG collections (support_kb + tax). Router/RAG
   node picks the collection per query.
2. **Endpoint = `/support` unified**, M1 `/query` stays separate.
3. **Hybrid output = single merged response** (rag_context flows into the M3
   ResponseGenerator; one coherent answer).
4. **Mini-RAG = separate service over HTTP** (§1).
5. **Frontend = chatbot** reusing existing `frontend/components/chat/*`.

### Clarifications (resolved via /clarify)
6. **Support-KB docs = create stub samples** — S0 generates placeholder policy/FAQ/
   warranty docs (AR/EN) so the pipeline is testable now; real docs swap in later.
7. **Customer access = public chat, identifier inside the message** — no customer
   login. `/support` is public (no JWT for the customer path); `InputParser`
   extracts the order/invoice/customer reference from the chat text (current
   behavior). Agent review endpoints (`/approve` etc.) stay JWT-protected.
8. **Chat memory = backend-persisted** — use the existing `conversations` table.
   The backend stores each turn and supplies `chat_history` to both Mini-RAG and
   the M3 ResponseGenerator (frontend sends only the new message + a session id).
9. **Review UX = hold + waiting message** — when `review_required=True`, the draft
   is NOT shown to the customer. The customer sees "an agent will follow up
   shortly"; the draft waits in the agent review panel for approve/reject.

---

## 4. Prerequisites (Sprint 0 clears these)

- **P1 · Mini-RAG must be runnable** with its own `.env` (LLM/OCR/Supabase keys).
- **P2 · Both collections ingested** in Mini-RAG (tax docs + sourced support-KB docs).
- **P3 · Wakeel readonly DB bug** — `retrieve()` failed with `WinError 10054` on
  the readonly engine. (Only affects the *old* in-Wakeel RAG; the new design uses
  Mini-RAG, so this is downgraded — but M3 data fetchers still use the DB, verify.)
- **P4 · Known M3 node bugs** (fix because we touch these nodes):
  - ResponseGenerator answers in English for Arabic input (customer message never
    passed to the prompt).
  - HumanReviewGate `"by"` / `"within"` keywords cause false-positive reviews.

---

## 5. Sprint Breakdown

> Each task lists: **files**, **what to do**, **acceptance**. Tasks are ordered;
> a later task never depends on an unbuilt one. No task spans more than ~1 file
> of new logic.

### Sprint 0 — Foundations & prerequisites
- **S0.T1** Run Mini-RAG locally. *Files:* `MIni-RAG-APP-V1/src/.env` (from `.env.example`).
  *Do:* fill keys, `uvicorn main:app`, hit `/api/v1/nlp/index/info/1`.
  *Accept:* service answers on its port; health/info returns JSON.
- **S0.T2** Create the two collections + ingest. *Do:* via Mini-RAG
  `upload → process → index/push` for project_id=2 (tax) and project_id=1 (support_kb).
  *Accept:* `index/info/1` and `index/info/2` both report >0 vectors.
- **S0.T3** Create **stub** support-KB docs (return/shipping policy, FAQ, warranty)
  in AR + EN as `.txt`. *Files (new):* `data/support_kb/*.txt`. *Do:* short
  placeholder content per topic (clearly marked PLACEHOLDER). *Accept:* files
  exist and are uploaded as project_id=1 in S0.T2; real docs swap in later.
- **S0.T4** Fix P4 bug #1 (language). *Files:* `agents/m3/nodes/response_generator_node.py`.
  *Do:* include the customer message in `_build_prompt_data`; add explicit
  "Respond ONLY in {lang}". *Accept:* AR query → AR answer (unit check).
- **S0.T5** Fix P4 bug #2 (review keywords). *Files:* `agents/m3/nodes/human_review_node.py`.
  *Do:* remove bare `"by"`/`"within"`; use word-boundary / phrase match.
  *Accept:* status_inquiry full-data response → `review_required=False`.
- **S0.T6** Add config. *Files:* `backend/core/config.py`, `.env.example`.
  *Do:* add `MINI_RAG_BASE_URL`, `RAG_SUPPORT_KB_PROJECT_ID=1`, `RAG_TAX_PROJECT_ID=2`.
  *Accept:* `get_settings()` exposes them.

### Sprint 1 — RAG client + RAG node
- **S1.T1** HTTP client. *Files (new):* `backend/services/rag_client.py`.
  *Do:* `async def rag_answer(query, project_id, chat_history) -> dict` calling
  `POST {MINI_RAG_BASE_URL}/api/v1/nlp/index/answer/{project_id}` (httpx, timeout,
  try/except → returns `{answer, sources, ok}`). *Accept:* unit test hits the live
  Mini-RAG and returns an answer.
- **S1.T2** State fields. *Files:* `agents/m3/schemas/m3_state.py`.
  *Do:* add `route`, `route_confidence`, `rag_context`, `rag_sources`,
  `rag_collection`; add defaults to `build_initial_state`. *Accept:* import + defaults present.
- **S1.T3** RAG node. *Files (new):* `agents/m3/nodes/rag_node.py`.
  *Do:* `async def run_rag(state)` → pick collection from `rag_collection`/route,
  call `rag_client.rag_answer`, write `rag_context` + `rag_sources`. Never raises.
  *Accept:* node returns context for a KB query; empty-safe on failure.

### Sprint 2 — Intent Router
- **S2.T1** Router prompt. *Files (new):* `agents/prompts/support_router.py`.
  *Do:* AR/EN system prompt → classify into `general_knowledge | customer_issue |
  hybrid` + target `collection`. *Accept:* prompt string importable.
- **S2.T2** Router node. *Files (new):* `agents/m3/nodes/intent_router_node.py`
  (model on `agents/m1/nodes/intent_classifier_node.py`).
  *Do:* GPT-4o-mini structured output → set `route`, `route_confidence`,
  `rag_collection`. Low confidence → default `customer_issue`. *Accept:* 6 sample
  messages (AR/EN) route correctly in a unit test.

### Sprint 3 — Graph restructure
- **S3.T1** Wire router as entry + conditional routes. *Files:* `agents/m3/graphs/m3_graph.py`.
  *Do:* add `intent_router` (entry), `rag_node`; conditional edges:
  `general_knowledge → rag_node → response_generator`;
  `customer_issue → input_parser → …`;
  `hybrid → rag_node → input_parser → …`. *Accept:* graph compiles; all 3 routes
  reach a terminal node.
- **S3.T2** RAGEnrich in context. *Files:* `agents/m3/nodes/context_builder_node.py`.
  *Do:* if `rag_context` present, add `context["knowledge"] = rag_context`.
  *Accept:* hybrid run shows knowledge inside context.

### Sprint 4 — Response merge + API
- **S4.T1** ResponseGenerator uses RAG. *Files:* `agents/m3/nodes/response_generator_node.py`.
  *Do:* add a "Knowledge base" section (from `rag_context`) to the prompt with a
  citation + no-fabrication rule. *Accept:* merged answer cites KB when present.
- **S4.T2** API response fields. *Files:* `backend/api/v1/m3_support.py`.
  *Do:* add `route`, `rag_sources` to `SupportResponse`; map from graph result.
  *Accept:* `/support` returns the new fields for all 3 routes.
- **S4.T3** Public customer access. *Files:* `backend/api/v1/m3_support.py`.
  *Do:* remove the JWT dependency from `POST /support` (customer path is public);
  keep `/approve`, `/reject`, `/escalate` JWT-protected (agents only).
  *Accept:* `/support` works with no Authorization header; review endpoints reject
  unauthenticated calls.
- **S4.T4** Conversation persistence. *Files (new):* `backend/repositories/conversations.py`;
  *Files:* `backend/api/v1/m3_support.py`. *Do:* accept optional `session_id`;
  load prior turns from the `conversations` table → pass as `chat_history` into the
  graph; append the new user turn + final answer after the run. *Accept:* a second
  message in the same `session_id` sees prior context.
- **S4.T5** Review-hold response shaping. *Files:* `backend/api/v1/m3_support.py`.
  *Do:* when `review_required=True` and not escalated, the customer-facing field
  returns a neutral "an agent will follow up shortly" message (AR/EN); the actual
  `draft_response` stays in `transparency_data` for the agent panel only.
  *Accept:* customer payload hides the draft; agent payload still has it.

### Sprint 5 — Frontend chatbot
- **S5.T1** Chat page. *Files:* `frontend/app/m3/page.tsx` (replace
  `CustomerInputForm` with chat), reuse `components/chat/ChatInterface.tsx`,
  `ChatInput`, `MessageList`, `MessageBubble`. *Accept:* `/m3` shows a chat UI.
- **S5.T2** Wire to API. *Files:* `frontend/hooks/useM3Support.ts`, `frontend/lib/api.ts`.
  *Do:* generate/keep a `session_id` (client-side); send only the new message +
  `session_id` to public `/support` (no auth header). Render the customer-facing
  reply in the thread. *Accept:* sending a message shows the reply; a follow-up in
  the same session keeps context.
- **S5.T3** Show route + sources + review state. *Files:* chat components / `components/m3/*`.
  *Do:* badge for `route` (knowledge/issue/hybrid); list `rag_sources` for
  knowledge answers; when `review_required`, show the "an agent will follow up
  shortly" message (the draft is hidden from the customer). *Accept:* each route
  renders correctly; held replies show the waiting message, not the draft.

### Sprint 6 — Integration tests (Claude runs at the end)
- **S6.T1** E2E test script. *Files (new):* `scripts/test_unified_support.py`.
  *Do:* login → POST `/support` for: pure knowledge Q, pure issue (real
  identifier), hybrid; assert route, answer language, sources, review flags.
- **S6.T2** Manual UI pass. *Do:* Claude runs both servers + frontend, sends the
  3 message types, verifies replies. *Accept:* all 3 paths work end-to-end.

---

## 6. Files Summary

```
NEW  data/support_kb/*.txt  (AR+EN stub docs)        (S0.T3)
NEW  backend/services/rag_client.py                 (S1.T1)
NEW  agents/m3/nodes/rag_node.py                     (S1.T3)
NEW  agents/m3/nodes/intent_router_node.py           (S2.T2)
NEW  agents/prompts/support_router.py                (S2.T1)
NEW  backend/repositories/conversations.py           (S4.T4)
NEW  scripts/test_unified_support.py                 (S6.T1)
MOD  backend/core/config.py · .env.example           (S0.T6)
MOD  agents/m3/schemas/m3_state.py                   (S1.T2)
MOD  agents/m3/graphs/m3_graph.py                    (S3.T1)
MOD  agents/m3/nodes/context_builder_node.py         (S3.T2)
MOD  agents/m3/nodes/response_generator_node.py      (S0.T4, S4.T1)
MOD  agents/m3/nodes/human_review_node.py            (S0.T5)
MOD  backend/api/v1/m3_support.py                    (S4.T2/T3/T4/T5: route+sources, public,
                                                      session_id+history, review-hold)
MOD  frontend/app/m3/page.tsx                        (S5.T1)
MOD  frontend/hooks/useM3Support.ts · lib/api.ts     (S5.T2)
MOD  frontend/components/m3 / chat components         (S5.T3)
RUN  MIni-RAG-APP-V1 (separate service, no Wakeel code change)
```

> Note: `SupportRequest` schema (in `m3_support.py`) gains an optional
> `session_id: str | None` (S4.T4); the existing `identifier` field becomes
> optional for the public chat path (S4.T3).

---

## 7. Sprint Dependency Order

```
S0 (foundations) → S1 (rag client/node) → S2 (router) → S3 (graph)
→ S4 (response+api) → S5 (frontend) → S6 (tests by Claude)
```
Each sprint is independently testable before the next starts.

---

## 8. Risks & Mitigations

- **Two services to run** → document a single startup script; keep Mini-RAG URL in config.
- **Latency** (router + RAG HTTP + agent + GPT-4o) → start simple; cache later if needed.
- **Support-KB content is stubbed** → answers are placeholder-quality until real
  policy/FAQ docs replace the S0.T3 stubs (re-run ingest, same project_id=1).
- **Public `/support`** (S4.T3) → abuse risk; mitigate post-MVP with rate-limiting
  / a lightweight anonymous session token. Review endpoints stay JWT-protected.
- **Auth between services** → MVP: same network/no auth; add a shared token post-MVP.
- **Mini-RAG `project_id` vs collection naming** → fix the two IDs in config (S0.T6).

---

## 9. Out of Scope (this plan)

- Rewriting Mini-RAG internals or migrating it into Wakeel's stack.
- M1 `/query` analytics endpoint (stays separate).
- Production auth/SSO between services.
- Real-time streaming responses (can be a later sprint).
```

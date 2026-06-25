# M3 — Customer Support Agent: System Architecture

> Complete architecture of the M3 Customer Support Agent across Sprints 0–4.
> Branch: `m3-sprint4-human-review-escalation`.
> Read alongside `agent_execution_log_m3s1.md` (Sprint 3 & 4 implementation log).

---

## 1. Purpose

M3 is an autonomous customer-support agent. A customer sends a free-form message
(Arabic or English) referencing an order / invoice / customer. The agent:

1. Parses the message and extracts the reference identifier.
2. Fetches all related data (invoice, order, shipping, history) **in parallel**.
3. Classifies the issue and builds structured context.
4. Generates a draft reply grounded only in real data (GPT-4o).
5. Decides whether a human must review the reply before it is sent.
6. Escalates to a human agent when it cannot answer safely.
7. Logs every decision to an immutable audit trail.

Core principle: **never fabricate, never crash, always degrade gracefully.**
Every node returns a partial state update and routes forward even on failure.

---

## 2. High-Level Architecture

```
                          ┌──────────────────────────────┐
   Customer (AR/EN)  ──►  │   FastAPI  /api/v1/support    │   ◄── JWT auth
                          │   m3_support.py               │
                          └───────────────┬──────────────┘
                                          │  build_initial_state()
                                          ▼
                          ┌──────────────────────────────┐
                          │   LangGraph  support_graph    │
                          │   (m3_graph.py, M3State)      │
                          └───────────────┬──────────────┘
                                          │ nodes
              ┌───────────────────────────┼────────────────────────────┐
              ▼                                                          ▼
   ┌────────────────────┐                                   ┌────────────────────┐
   │  Agent Nodes        │   read/write M3State             │  Tools / Data layer │
   │  (agents/m3/nodes)  │ ───────────────────────────────► │  (agents/m3/tools)  │
   └────────────────────┘                                   └─────────┬──────────┘
                                                                       │ SELECT-only
                                                                       ▼
                                                  ┌────────────────────────────────┐
                                                  │  PostgreSQL / Supabase           │
                                                  │  invoices, customers, orders,    │
                                                  │  shipments, customer_interactions│
                                                  │  audit_log                       │
                                                  └────────────────────────────────┘
```

---

## 3. Layered Design

| Layer | Location | Responsibility |
|---|---|---|
| **API** | `backend/api/v1/m3_support.py` | HTTP contract, JWT auth, request/response validation, review endpoints. Never returns HTTP error for agent failures. |
| **Orchestration** | `agents/m3/graphs/m3_graph.py` | LangGraph `StateGraph` wiring nodes + conditional routers. |
| **State** | `agents/m3/schemas/m3_state.py` | `M3State` TypedDict (total=False) + `build_initial_state()`. |
| **Nodes** | `agents/m3/nodes/*.py` | The 8 pipeline steps (business logic). |
| **Tools** | `agents/m3/tools/*.py` | Data-source fetchers (SELECT-only SQL). |
| **Repository** | `backend/repositories/m3_repository.py`, `audit_logs.py` | Reusable DB queries. |
| **Services** | `backend/services/human_review_service.py`, `audit_service.py` | Review actions + audit logging. |
| **Audit** | `backend/models/audit_log.py`, `schemas/audit.py` | Immutable decision trail. |

---

## 4. LangGraph Pipeline (the heart of M3)

```
START
  │
  ▼
InputParser ──► DataFetcher ──► CompletenessCheck
                                       │
                          ┌────────────┴─────────────┐  _escalation_router
                  escalate│                           │classify
                          ▼                           ▼
                  ResponseGenerator           IssueClassifier
                          ▲                           │
                          │                           ▼
                          └─────────────────── ContextBuilder
                          │
                          ▼
                  HumanReviewGate
                          │
                ┌─────────┴──────────┐  _review_router
         escalate│                    │end
                 ▼                    ▼
          EscalationNode ──► END     END  (with review_required / draft_response)
```

### Conditional routers

- **`_escalation_router`** (after CompletenessCheck): if `escalation_needed` →
  skip classification, go straight to ResponseGenerator (which emits the
  no-data fallback). Otherwise → IssueClassifier.
- **`_review_router`** (after HumanReviewGate): if `escalation_needed` →
  EscalationNode. Otherwise → END (the draft is returned; `review_required`
  tells the UI whether a human must approve before sending).

---

## 5. The 8 Nodes

### 5.1 InputParserNode — `input_parser_node.py`  (Sprint 1)
- Detects language (AR/EN) via `detect_language`.
- Extracts `{identifier_type, identifier_value}` + clean `issue_description`
  using GPT-4o-mini structured output (`ParsedInput`).
- **Regex fallback** (`ORD/DEL/TRK`, `INV`, `CUST/CUS` prefixes) if the LLM fails.
- A pre-supplied identifier from the API is trusted and skips extraction.
- **No identifier at all → `escalation_needed = True`** (graceful degradation).

### 5.2 DataFetcherNode — `data_fetcher_node.py`  (Sprint 1)
- Runs **4 fetchers concurrently** via `asyncio.gather(return_exceptions=True)`:
  - `fetch_invoice` (REAL — invoices + customers) → `invoice_fetcher_tool`
  - `fetch_order`, `fetch_shipping`, `fetch_history` → `mock_data_tool`
- Any failing/empty source resolves to `None` — one failure never crashes the rest.

### 5.3 DataCompletenessCheckNode — `data_completeness_node.py`  (Sprint 1)
- Pure/deterministic, no I/O. Scores completeness:
  - all 4 present → `1.0`
  - some present → `0.5`
  - none present → `0.0` + `escalation_needed = True`
- Sprint 1: `confidence_score = data_completeness` (refined in Sprint 3).
- `get_confidence_label()` (High ≥0.8 / Medium ≥0.5 / Low) is shared with the API.

### 5.4 IssueClassifierNode — `issue_classifier_node.py`  (Sprint 2)
- GPT-4o-mini structured output → `issue_type` ∈ {status_inquiry,
  billing_dispute, shipping_issue, refund_request, general_complaint} + priority.
- Feeds a compact data summary into the prompt for better classification.
- Falls back to `general_complaint` / `Medium` on error.

### 5.5 ContextBuilderNode — `context_builder_node.py`  (Sprint 2)
- Pure transform: normalizes `fetched_data` into a clean `context` dict
  (invoice / order / shipping[] / history[]), adds `missing_fields` when partial.

### 5.6 ResponseGeneratorNode — `response_generator_node.py`  (Sprint 3)
- **Repeat-issue detection**: same `issue_type` in history >2 times within 180
  days → `escalation_needed = True`.
- **Confidence scoring**: `data_completeness ×0.5 + classification ×0.3 + context ×0.2`.
- **3-tier GPT-4o generation**:
  - Tier A (completeness 1.0): full detailed answer
  - Tier B (partial): available info + 24h follow-up
  - Tier C (no data): "no matching record" fallback
- Static AR/EN fallback templates when the LLM call fails.

### 5.7 HumanReviewGateNode — `human_review_node.py`  (Sprint 4)
Sets `review_required` by rule:

| Condition | Decision |
|---|---|
| `escalation_needed == True` | skip review → escalate |
| `issue_type == billing_dispute` | mandatory review |
| `issue_type == refund_request` | mandatory review |
| `confidence_score < 0.70` | mandatory review |
| draft contains financial/delivery promise | mandatory review |
| status_inquiry / general_complaint + high confidence | optional (no review) |

`_contains_financial_commitment()` scans the draft for AR/EN keywords
(refund, compensation, discount, استرداد, تعويض, خصم, سيصل, …).

### 5.8 EscalationNode — `escalation_node.py`  (Sprint 4)
- Builds an `escalation_summary` (identifier, issue_type, data presence map, reason).
- Logs `action_taken="escalated"` to the audit trail (best-effort, never blocks).
- Sets a customer-facing AR/EN escalation message in `final_response`.
- `_get_escalation_reason()` derives the reason (no data / missing sources / flag).

---

## 6. M3State (shared graph state)

`TypedDict(total=False)` — each node returns only the keys it changed; LangGraph
merges. `build_initial_state()` is the single source of defaults (API + tests).

| Group | Fields | Set by |
|---|---|---|
| Input | `customer_identifier`, `issue_description`, `language` | InputParser |
| Classification | `issue_type`, `issue_priority`, `context` | IssueClassifier / ContextBuilder |
| Data | `fetched_data`, `data_completeness`, `missing_fields` | DataFetcher / Completeness |
| Confidence | `confidence_score` | Completeness (S1) → ResponseGenerator (S3) |
| Response | `draft_response` | ResponseGenerator |
| Review/Escalation | `review_required`, `escalation_needed`, `rejection_context`, `final_response`, `escalation_summary` | HumanReviewGate / Escalation |
| Internal | `error` | any node (never raised to client) |

---

## 7. Data Sources

Read **SELECT-only** from PostgreSQL/Supabase. "Mock" = synthetic data seeded
as real tables in Sprint 0, not in-memory.

| Logical source | Table | Tool | Cardinality |
|---|---|---|---|
| invoice (REAL) | `invoices` + `customers` | `invoice_fetcher_tool` | 1 row |
| order | `orders` | `mock_data_tool.fetch_order` | 1 row |
| shipping | `shipments` | `mock_data_tool.fetch_shipping` | 1 row |
| history | `customer_interactions` | `mock_data_tool.fetch_history` | **N rows** (repeat detection) |

Each tool resolves all 3 identifier types (`order_id` / `invoice_id` /
`customer_id`) via dedicated JOIN queries, so they run in parallel without
coordination. `jsonify_row(s)` normalizes rows (dates → ISO strings) for JSON.

---

## 8. API Surface — `/api/v1/support`

| Method | Path | Purpose |
|---|---|---|
| POST | `/support` | Full pipeline. Returns `SupportResponse` (draft, final, confidence, review/escalation flags, transparency_data). Optional `rejection_context` re-runs with feedback. |
| POST | `/support/approve` | Approve draft → audit `approved` |
| POST | `/support/reject` | Reject with feedback → audit `rejected` (Reject & Regenerate) |
| POST | `/support/escalate` | Manual escalation → audit `escalated` |

- All routes require JWT (`get_current_user`).
- `/support` **never** raises HTTP errors for agent failures — it returns a safe
  escalated response so the frontend contract is stable.
- `transparency_data` is for the agent review screen only — **not** for the customer.

---

## 9. Audit Trail

`audit_log` table (`backend/models/audit_log.py`):
`id (UUID)`, `case_id` (indexed), `issue_type`, `confidence_score`,
`review_required`, `action_taken` ∈ {approved, rejected, escalated},
`agent_id`, `details`, `created_at`.

- `audit_service.log_decision()` wraps the repository with structured logging.
- Audit writes are **best-effort inside the graph** (try/except) so logging
  failures never block a customer response — but review-action endpoints surface
  errors to the caller.

---

## 10. Tech Stack

- **Orchestration**: LangGraph `StateGraph` (async, partial-update TypedDict state)
- **LLMs**: GPT-4o-mini (parsing, classification) · GPT-4o (response generation) — `agents/shared/llm_client.py`
- **API**: FastAPI + Pydantic v2, JWT auth
- **DB**: PostgreSQL (Supabase) via SQLAlchemy async + asyncpg, SELECT-only for fetchers
- **Logging**: structlog (`backend/core/logging.py`)

---

## 11. Key Design Decisions

1. **Graceful degradation everywhere** — every node returns valid state and
   routes forward; failures flip `escalation_needed` instead of raising.
2. **Parallel data fetch** — 4 sources via `asyncio.gather`; independent failures.
3. **TypedDict state** (not Pydantic) inside the graph for LangGraph merge
   semantics; Pydantic only at the API boundary.
4. **Human-in-the-loop by risk** — financial/refund/low-confidence/promise drafts
   require review; safe high-confidence answers auto-send.
5. **Grounded generation** — GPT-4o answers only from fetched data; no fabrication.
6. **Immutable audit** — every approve/reject/escalate decision is recorded.
7. **`m3_orchestrator.py` is a CLI convenience wrapper, NOT used by the API**
   (the endpoint invokes `support_graph` directly).

---

## 12. End-to-End Example (AR order inquiry, full data)

```
POST /support { query: "أين طلبي ORD-1023؟" }
  → InputParser:        identifier={order_id, ORD-1023}, language=ar
  → DataFetcher:        invoice✓ order✓ shipping✓ history✓ (parallel)
  → CompletenessCheck:  completeness=1.0, confidence=1.0
  → (router: classify)
  → IssueClassifier:    status_inquiry / Low
  → ContextBuilder:     structured context
  → ResponseGenerator:  Tier A Arabic reply, confidence=1.0
  → HumanReviewGate:    review_required=False (high conf, status_inquiry)
  → (router: end)
  → END → SupportResponse { draft_response, review_required:false, ... }
```
```
POST /support { query: "عايز استرد فلوسي عن INV-77" }
  → ... → IssueClassifier: refund_request
  → HumanReviewGate: review_required=True (refund → mandatory review)
  → END → agent must /approve or /reject before the customer sees it
```
```
POST /support { query: "مشكلة في طلب رقم XYZ" }   (no resolvable identifier / no data)
  → InputParser/Completeness: escalation_needed=True
  → ResponseGenerator (Tier C) → HumanReviewGate (escalate)
  → EscalationNode: audit "escalated" + AR escalation message → END
```
```
```

---

## Addendum — Unified Router & Conversation Agent (features 001 + 002)

The M3 pipeline is fronted by an **Intent Router** (graph entry) that classifies
each `/support` message into one of four routes:

| Route | Path through the graph | Needs data? |
|-------|------------------------|-------------|
| `greeting` | `intent_router → greeting_node → END` | No — friendly small-talk reply only |
| `general_knowledge` | `intent_router → rag_node → response_generator → review → END` | RAG (Mini-RAG) |
| `customer_issue` | `intent_router → input_parser → … → response_generator → review` | CRM/DB |
| `hybrid` | `intent_router → rag_node → input_parser → … → response_generator → review` | RAG + CRM |

- **greeting** (feature 002): pure social/small-talk ("Hi", "شكراً") gets a short,
  language-matched friendly reply via the fast LLM. It skips RAG, the CRM
  pipeline, and the human-review gate, and never sets sources/review/escalation.
- Routing is **conservative**: any actionable request or low router confidence
  falls back to `customer_issue`, so a real support need is never treated as
  small-talk.

# AERIE — Agentic ERP Intelligence Engine
## Engineering Delivery Plan
### Version 1.0 | Classification: Internal Engineering | Status: Execution-Ready

---

> *Prepared by: Principal Engineering Manager / Staff AI Engineer / Technical Program Manager*
> *Based on: Vision & Discovery Document v1.0 · Master PRD v1.0 · System Architecture Document v1.0*
> *Team Size: 6 Engineers | Timeline: ~9 Weeks*

---

## Table of Contents

- [Part 1 — Epic Breakdown](#part-1--epic-breakdown)
- [Part 2 — Sprint Planning](#part-2--sprint-planning)
- [Part 3 — Detailed Task Breakdown](#part-3--detailed-task-breakdown)
- [Part 4 — Development Order & Dependency Graph](#part-4--development-order--dependency-graph)
- [Part 5 — Engineer Allocation](#part-5--engineer-allocation)
- [Part 6 — MVP Reduction Strategy](#part-6--mvp-reduction-strategy)
- [Part 7 — Coding Agent Specifications](#part-7--coding-agent-specifications)
- [Part 8 — Repository Structure](#part-8--repository-structure)
- [Part 9 — Testing Strategy](#part-9--testing-strategy)
- [Part 10 — Final Delivery Plan](#part-10--final-delivery-plan)

---

# PART 1 — Epic Breakdown

---

## Epic 1 — Project Foundation & Infrastructure

**Objective:** Establish the complete local development environment, repository structure, CI tooling, Docker Compose stack, Odoo instance, and mock dataset. No agent code is written here; this epic creates the substrate on which all other epics depend.

**Business Value:** Zero delivery is possible without a running Odoo instance, a seeded dataset, and a working Docker Compose stack. Failures at this layer cause cascading delays across all downstream epics. Completing this first eliminates the #1 category of demo-day risk (environment failure).

**Technical Scope:**
- Git repository initialization with defined folder structure
- `docker-compose.yml` defining: Odoo, PostgreSQL (Odoo DB), PostgreSQL (App DB), Redis, FastAPI stub, Next.js stub, Chroma
- Odoo Community Edition installed and accessible (JSON-RPC verified)
- `seed_mock_data.py` script: generates and loads all required entities (15 customers, 10 suppliers, 50 products, 300 sales orders, 800 SOLs, 200 invoices, 150 POs, 400 POLs, 50 stock quantities, 50 reorder rules, 100 supplier pricelists)
- Schema validation script (`schema_validate.py`) verifying all Odoo field paths match live instance
- `demo_data_guide.md` documenting the key data stories (critical products, top customers, star supplier, outlier supplier)
- LangSmith account connected and environment variable configured
- `structlog` configured for structured JSON logging
- `.env.example` with all required environment variables documented
- Shared `OdooClient` class: singleton, auth refresh, rate limiter (10 calls/sec), full logging

**Dependencies:** None — this is the root epic.

---

## Epic 2 — Authentication & Session Management

**Objective:** Implement JWT-based authentication, role management, Redis session context, and the audit log infrastructure that underpins all agent actions.

**Business Value:** Security is a non-negotiable enterprise signal. Every judge and evaluator will look for it. Authentication and the audit log must be in place before any ERP write path is built, because the confirmation gate depends on session-scoped confirmation tokens.

**Technical Scope:**
- FastAPI authentication endpoints: `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`
- JWT issuing (access token 8h, refresh token 7d), bcrypt password hashing, httpOnly cookie delivery
- User table in PostgreSQL: `id`, `username`, `password_hash`, `role` (admin/manager/analyst/procurement/sales), `created_at`
- Role enum and FastAPI dependency (`require_role`) for all protected endpoints
- Redis session management: `get_session_context`, `update_session_context`, `delete_session_context`
- Audit log table: INSERT-ONLY schema per PRD Section 18.5 (UUID, timestamp, session_id, user_id, action_type, odoo_model, odoo_record_id, action_payload, outcome, failure_reason, agent_id)
- `AuditLogger` service class used by all agents
- Confirmation token system: single-use, session-scoped, 10-minute expiry

**Dependencies:** Epic 1 (PostgreSQL, Redis running)

---

## Epic 3 — Odoo Integration Layer

**Objective:** Build the production-grade `OdooClient` and the YAML Schema Registry — the two foundational services that every agent depends on for ERP data access.

**Business Value:** Every feature in both modules reads from or writes to Odoo. The quality and reliability of the Odoo integration layer directly determines the reliability of the entire system. A well-designed client here eliminates a class of bugs everywhere else.

**Technical Scope:**
- `OdooClient` class (singleton):
  - `authenticate()`: returns UID, stores credentials server-side only
  - `search_read(model, domain, fields, limit, offset)`: paginated, logged, rate-limited
  - `create(model, values)`: gated (requires confirmation token), logged, writes to audit log
  - `write(model, record_id, values)`: gated, logged
  - `execute_action(model, method, record_ids)`: gated, logged
  - `fields_get(model)`: for schema validation
  - Retry logic: 1 retry on failure, then raise `OdooConnectionError`
  - Rate limiter: token bucket, 10 calls/sec
  - Full structured logging per call
- Schema Registry (`schema_registry.yaml`): maps NLP concepts → Odoo model + field paths
  - Covers: customers, products, sales orders, invoices, purchase orders, stock levels, reorder rules, supplier pricelists
- `schema_validate.py`: compares registry against live Odoo instance, fails loudly on mismatch
- Entity Resolver service: `resolve_entity(name, model_type)` → Odoo record ID
- Domain Filter Builder: `build_domain_filter(entities, time_range, filters)` → Odoo domain list

**Dependencies:** Epic 1 (OdooClient requires live Odoo + mock data)

---

## Epic 4 — Copilot Core (Module 1 — Chat + ERP Query)

**Objective:** Build the conversational backbone of Module 1: the Copilot Orchestrator (AGENT-1-01), the ERP Query Agent (AGENT-1-02), and the LangGraph state machine that connects them. By the end of this epic, users can ask natural language questions about ERP data and receive accurate, formatted responses.

**Business Value:** This is the first user-visible AI capability. It validates the entire agent pipeline end-to-end, proves Arabic NLP works, and creates the foundation on which the Action Agent and Analytics pipeline are built. Without this, there is no demo.

**Technical Scope:**
- LangGraph state machine: `CopilotGraph` with nodes for Orchestrator, ERP Query Agent, and terminal state
- Copilot Orchestrator (AGENT-1-01):
  - Language detection tool: `detect_language(text)` → ISO 639-1
  - Intent classifier: `classify_intent(text, context)` → intent code + confidence + entities
  - Session context manager (Redis read/write)
  - Router: dispatches to ERP Query Agent or Analytics Supervisor based on intent
  - Clarification request handler (confidence < 0.70)
- ERP Query Agent (AGENT-1-02):
  - Entity resolution via Schema Registry
  - Domain filter construction
  - Odoo `search_read` execution
  - Pagination handling (50 records/call)
  - Result formatter: table, list, summary — in user's language
  - Error handling: not-found, empty results, API failure
- WebSocket streaming endpoint: `WS /api/v1/copilot/chat/stream`
- REST fallback: `POST /api/v1/copilot/chat`
- Session endpoints: `POST /api/v1/copilot/session`, `DELETE /api/v1/copilot/session/{id}`
- Arabic NLP validation: 30-query test set (20 required by PRD), iterate until ≥90% accuracy

**Dependencies:** Epics 1, 2, 3

---

## Epic 5 — ERP Action Agent & Confirmation Gate (Module 1)

**Objective:** Build the ERP Action Agent (AGENT-1-03) and the human-in-the-loop Confirmation Gate — the security and trust centerpiece of the entire platform.

**Business Value:** The Confirmation Gate is simultaneously the most important safety feature and the most important enterprise-readiness signal. It must be airtight. No judge, enterprise evaluator, or recruiter will trust an AI that touches production data without human approval. This epic must be flawless.

**Technical Scope:**
- ERP Action Agent (AGENT-1-03):
  - Missing field extraction: asks clarifying questions before confirmation
  - Entity validation against Odoo (pre-confirmation)
  - Confirmation Summary builder: human-readable, structured, bilingual
  - Odoo write execution (on approval only)
  - Audit log write on every action (approved, rejected, cancelled)
- Confirmation Gate:
  - Confirmation token generation (UUID, session-scoped, 10-minute TTL, stored in Redis)
  - `POST /api/v1/copilot/actions/{action_id}/confirm` endpoint
  - `POST /api/v1/copilot/actions/{action_id}/reject` endpoint
  - Backend validation: same session, unexpired token, not previously used (replay protection)
  - UI-independent: the gate is enforced at the API layer, not just the frontend
- Supported write actions (MVP): create `sale.order` (quotation), create `sale.order.line`
- Audit log entries for all outcomes: success, failure, cancelled_by_user

**Dependencies:** Epics 3, 4

---

## Epic 6 — Analytics Multi-Agent System (Module 1)

**Objective:** Build the Analytics Supervisor and its four sub-agents (Data Retrieval, KPI Computation, Visualization, Insight Generation) — the most technically impressive and demo-critical capability of Module 1.

**Business Value:** The analytics pipeline is what separates AERIE from a chatbot in the eyes of every evaluator. Four agents visibly collaborating to produce a multi-KPI business review with charts and narrative in 30 seconds is the signature demo moment. This epic must be prioritized and polished to perfection.

**Technical Scope:**
- Analytics Supervisor (AGENT-1-04): receives analytics intent, coordinates sub-agents, assembles final report
- Data Retrieval Agent (AGENT-1-05):
  - Fetches raw data: sales orders, invoices, products, purchase orders for specified time range
  - Handles period-over-period data retrieval (current + prior period)
  - Returns structured data payload to KPI agent
- KPI Computation Agent (AGENT-1-06):
  - CODE-ONLY computation (no LLM for number generation — prevents hallucination)
  - Computes: total revenue, revenue delta %, top customers (by revenue), top products, order count, avg order value, outstanding invoice total, stock health summary
  - Period-over-period comparison for all applicable KPIs
  - Returns typed `KPIReport` object
- Visualization Agent (AGENT-1-07):
  - Receives KPI data, selects appropriate chart types
  - Generates Recharts-compatible JSON chart configurations (no image generation)
  - Chart types: bar (revenue by month), line (revenue trend), pie (customer mix), table (top products)
  - Returns chart config array
- Insight Generation Agent (AGENT-1-08):
  - Strictly grounded: only references values in the `KPIReport` object
  - Generates 3–5 narrative business insights in user's language
  - Arabic output with RTL formatting when Arabic session
- Analytics report endpoint: `GET /api/v1/copilot/reports/{report_id}`
- LangGraph sub-graph: Analytics pipeline as a nested graph within the main Copilot graph
- Performance target: ≤30 seconds end-to-end

**Dependencies:** Epics 3, 4

---

## Epic 7 — Procurement Intelligence System (Module 2)

**Objective:** Build the complete Module 2 agent system: Procurement Orchestrator, Inventory Monitor Agent, Demand Forecaster Agent, Supplier Evaluator Agent, and RFQ Generator Agent — with the procurement-specific Confirmation Gate.

**Business Value:** The "system detected a stockout before you did and already has the RFQ ready for your approval" moment is the highest-value procurement demo. This epic delivers the core of the business case for AERIE in enterprise settings. Proactive AI replacing reactive firefighting.

**Technical Scope:**
- Procurement Orchestrator (AGENT-2-01): schedules monitoring cycles, coordinates sub-agents, manages procurement state
- Inventory Monitor Agent (AGENT-2-02):
  - Reads `stock.quant`, `stock.warehouse.orderpoint` for all 50 products
  - Computes risk state per product: CRITICAL / AT RISK / WATCH / HEALTHY
  - CRITICAL formula: current_stock ≤ (lead_time_days × avg_daily_consumption)
  - Generates alert objects for state transitions
  - Scheduled cycle (configurable, default 60 min); also on-demand via `POST /api/v1/procurement/monitoring/run`
- Demand Forecaster Agent (AGENT-2-03):
  - Reads 90 days of `sale.order.line` history per product
  - Implements: simple moving average (primary), Prophet (if available) or Statsmodels
  - Outputs: projected stockout date, confidence level (HIGH/MEDIUM/LOW), recommended order quantity
  - Confidence logic: HIGH ≥90 days history; MEDIUM 30–89 days; LOW <30 days
  - Respects MOQ from `product.supplierinfo`
- Supplier Evaluator Agent (AGENT-2-04):
  - Deterministic scoring (no LLM for scoring math — LLM only for rationale text)
  - Scoring criteria: price consistency (25%), on-time delivery rate (35%), order fulfillment accuracy (25%), lead time (15%)
  - Reads from `purchase.order`, `purchase.order.line`, `product.supplierinfo`
  - Flags "New Supplier — Limited Data" for suppliers with <2 historical POs
  - Ranks suppliers per-product (not globally)
- RFQ Generator Agent (AGENT-2-05):
  - Receives at-risk products + supplier rankings
  - Generates draft RFQ objects (not yet written to Odoo)
  - Combines RFQs for shared suppliers when applicable
  - Triggers Procurement Confirmation Gate
- Procurement Confirmation Gate:
  - Draft RFQs stored in app DB pending review
  - `POST /api/v1/procurement/rfq/drafts/{draft_id}/approve`: validates token, writes `purchase.order` (RFQ state) to Odoo, logs
  - `POST /api/v1/procurement/rfq/drafts/{draft_id}/reject`: discards draft, logs with reason
  - Batch approval support
- Procurement API endpoints per Section 16.2
- Procurement Health Score: composite score per product and portfolio level

**Dependencies:** Epics 1, 2, 3

---

## Epic 8 — OCR Supplier Quote Processing (Module 2 — Should Have)

**Objective:** Build the OCR Agent that processes supplier quotation PDFs and extracts structured data for supplier comparison.

**Business Value:** Demonstrates a complete "quote-to-comparison" workflow — a real procurement pain point. Also shows multi-modal AI capability (document understanding). This is a Should Have; deliver after Epic 7 core is stable.

**Technical Scope:**
- OCR Agent (AGENT-2-06):
  - Primary extractor: GPT-4o Vision (document → structured JSON)
  - Fallback: Tesseract + regex for standard templates
  - Extracts: Supplier Name, Product, Unit Price, MOQ, Lead Time, Payment Terms, Validity Date
  - Confidence scoring per field
  - Low-confidence fields flagged in UI for user review
- File upload endpoint: `POST /api/v1/procurement/quotes/upload`
  - Validation: PDF only, ≤10MB
  - Returns `quote_id` for retrieval
- Quote retrieval: `GET /api/v1/procurement/quotes/{quote_id}` → structured extraction result
- Editable review table before data enters supplier comparison
- Arabic PDF support

**Dependencies:** Epic 7

---

## Epic 9 — Frontend Experience

**Objective:** Build the complete React/Next.js frontend: Copilot chat interface, Analytics report view, Confirmation panels, Procurement dashboard, Product risk list, RFQ review panel, Supplier comparison, and Audit log viewer.

**Business Value:** The frontend is the demo. A polished, professional UI is not optional — it is the artifact judges, recruiters, and clients see first. It must communicate enterprise quality immediately. Arabic RTL must work correctly. Loading states must be visible. The Agent Reasoning Panel must be compelling.

**Technical Scope:**
- Next.js app with Tailwind CSS
- Typography: IBM Plex Arabic / Noto Kufi Arabic + Inter (English)
- Semantic color system: green (healthy), yellow (watch), orange (at-risk), red (critical/error)
- **UI-01 Login:** JWT auth form, httpOnly cookie handling
- **UI-02 Main Dashboard:** Navigation hub, health summary widgets
- **UI-03 Copilot Chat:**
  - Left sidebar: session history, language toggle (AR/EN)
  - Main area: message history (RTL for Arabic), streaming message display
  - Input area: text input, submit button, loading indicator
  - Agent Reasoning Panel: collapsible, shows real-time agent steps from WebSocket stream
  - Confirmation Panel overlay (UI-05): modal, cannot dismiss by clicking outside, dynamic CTA text
- **UI-04 Analytics Report View:**
  - Executive summary card
  - KPI grid (metric + delta badge)
  - Recharts chart components: `RevenueBarChart`, `TrendLineChart`, `CustomerPieChart`, `ProductTable`
  - Insight cards with data references
- **UI-06 Procurement Dashboard:**
  - Portfolio Health Score gauge
  - Alert notification panel
  - Risk summary: counts by state (CRITICAL / AT RISK / WATCH / HEALTHY)
- **UI-07 Product Risk List:**
  - Filterable, sortable table: product, category, current stock, reorder point, risk state, projected stockout date
  - Risk state color badges
- **UI-08 RFQ Review Panel:**
  - `RFQDraftCard` (expandable)
  - `SupplierScoreBadge`
  - `AIRationaleNote`
  - `ApprovalBar` (sticky bottom, "Approve All" / "Reject All")
- **UI-09 Supplier Comparison Panel:**
  - Side-by-side table
  - Radar chart (Recharts `RadarChart`)
  - `SelectSupplierButton`
- **UI-10 Quote Upload & Review:**
  - PDF drag-and-drop upload
  - Editable extraction result table with confidence highlights
- **UI-11 Audit Log Viewer:** paginated table, filterable by action type / date / user
- WebSocket client for streaming agent steps
- Toast notifications (bottom-right, 4s auto-dismiss) for all write operations
- Skeleton loaders and loading spinners for all async operations
- Empty state components for all tables and lists

**Dependencies:** Epics 4, 5, 6, 7

---

## Epic 10 — Observability, Hardening & Demo Preparation

**Objective:** Connect LangSmith to all agent invocations, complete integration testing, run demo scenario dry-runs, fix all critical bugs, and prepare the demo environment for zero-failure delivery.

**Business Value:** A system that crashes during the demo is worth zero points. This epic converts a working system into a reliable one. LangSmith traces visible during the demo are a significant technical differentiator — showing judges agent-by-agent reasoning chains is the answer to "how is this different from a chatbot?"

**Technical Scope:**
- LangSmith `@traceable` decorator or `with_config` wrapper on every agent invocation
- Verify all 5 demo scenarios run end-to-end without agent failure
- Verify Arabic queries return correct RTL responses on all 30 test queries (≥90% accuracy)
- Verify LangSmith traces visible for all multi-agent workflows
- Verify Confirmation Gate intercepts all write operations in demo scenarios
- Verify ≥3 RFQ drafts visible in procurement dashboard at demo start
- Verify Analytics report KPI values match mock dataset ground truth
- Verify Docker Compose stack starts cleanly on a fresh machine
- Verify Audit log contains entries from all demo scenario write actions
- Performance testing: simple query ≤5s, analytics report ≤30s, RFQ generation ≤15s
- Demo environment Docker snapshot committed to repository
- Demo script (`DEMO_SCRIPT.md`) with exact steps, fallback plans, and talking points
- Backup: Docker volume with pre-seeded Odoo data snapshot

**Dependencies:** All previous epics complete

---

# PART 2 — Sprint Planning

*All sprints are 2 weeks except Sprint 0 (1 week setup sprint). Total timeline: ~9 weeks.*

---

## Sprint 0 — Environment, Foundation, and Data (1 Week)

**Goal:** Every engineer has a running local environment. Odoo is live. Mock data is seeded. The Docker Compose stack is running. No AI code exists yet, but the substrate for everything is ready.

**Deliverables:**
- Git repository initialized with full folder structure
- `docker-compose.yml` running: Odoo, PostgreSQL (×2), Redis, FastAPI (stub), Next.js (stub), Chroma
- Odoo Community Edition accessible at `localhost:8069`, JSON-RPC verified working
- `seed_mock_data.py` complete and idempotent — all required entities loaded
- `schema_validate.py` passing — all schema registry entries verified against live Odoo
- `demo_data_guide.md` written — key data stories documented
- `OdooClient` class: authenticate, search_read, basic logging (write operations stubbed with gate placeholder)
- LangSmith account connected, `LANGCHAIN_API_KEY` in `.env.example`
- `structlog` configured
- FastAPI project skeleton: health endpoint responding, JWT middleware scaffolded
- Next.js project skeleton: root page rendering, Tailwind configured, Arabic font loaded
- All engineers have verified the stack runs on their local machine

**Success Criteria:**
- `docker-compose up` starts all services without errors on at least 2 engineer machines
- `curl localhost:8069/web/dataset/call_kw` returns a valid Odoo response
- `python seed_mock_data.py` loads all entities (verified in Odoo UI)
- `python schema_validate.py` exits with zero errors
- FastAPI `/health` endpoint returns `{"status": "ok"}`

**Risks:**
- Odoo Docker image version incompatibility — mitigate by pinning exact Odoo version in docker-compose
- Mock data generation time underestimated — allocate Engineer F (DevOps/Data) exclusively to this
- Schema registry field name mismatches — `schema_validate.py` catches these before agent development begins

---

## Sprint 1 — Copilot Core: Orchestrator + ERP Query + Basic Chat UI (2 Weeks)

**Goal:** A user can open the chat interface, type a natural language ERP query in English or Arabic, and receive a correct, formatted response from live Odoo data. The end-to-end pipeline (User → FastAPI → LangGraph → Orchestrator → ERP Query Agent → Odoo → Response) is working.

**Deliverables:**
- Authentication endpoints: login, refresh, logout (JWT, bcrypt, httpOnly cookie)
- User seed data (5 test users, one per role)
- Redis session context: get/set/delete
- Audit log table + `AuditLogger` service
- Copilot Orchestrator (AGENT-1-01): language detection, intent classification (query.data intent path), session context management, routing
- ERP Query Agent (AGENT-1-02): entity resolution, domain filter construction, Odoo search_read, result formatting
- LangGraph `CopilotGraph` v1: Orchestrator → ERP Query Agent → terminal state
- `POST /api/v1/copilot/chat` REST endpoint (non-streaming)
- Session endpoints: create, delete
- Basic chat UI (UI-03 simplified): text input, message history, language toggle (AR/EN) — no streaming yet, no agent panel
- Login page (UI-01)

**Success Criteria:**
- Query "Show me the top 5 customers by revenue" returns correct customer list from Odoo
- Query "ما هي المنتجات التي مخزونها منخفض؟" (What products have low stock?) returns Arabic-language response with correct stock data
- Intent classifier correctly routes `query.data` intents to ERP Query Agent
- Session context retained across 3-turn conversation
- Login works, protected endpoints reject unauthenticated requests

**Risks:**
- Arabic intent classification accuracy may be low initially — plan 2–3 days of prompt iteration
- LangGraph state machine coordination bugs — enforce typed input/output schemas from day 1
- Entity resolution failures on Arabic names — test entity resolver against Arabic mock data early

---

## Sprint 2 — Analytics Multi-Agent + ERP Action Agent + Streaming UI (2 Weeks)

**Goal:** The analytics pipeline is working (4 agents → KPI report with charts). The ERP Action Agent with Confirmation Gate is working. The chat UI streams responses and shows the Agent Reasoning Panel. This sprint delivers the two most demo-critical features.

**Deliverables:**
- Analytics Supervisor (AGENT-1-04) + full sub-agent chain
- Data Retrieval Agent (AGENT-1-05): multi-period data fetching
- KPI Computation Agent (AGENT-1-06): all KPIs computed in code, period-over-period deltas
- Visualization Agent (AGENT-1-07): Recharts JSON chart configurations for all 4 chart types
- Insight Generation Agent (AGENT-1-08): strictly grounded, bilingual narrative
- LangGraph nested Analytics sub-graph
- Analytics report endpoint + report storage
- ERP Action Agent (AGENT-1-03): field extraction, entity validation, confirmation summary, write execution
- Confirmation Gate: token generation, confirm/reject endpoints, replay protection
- WebSocket streaming endpoint: agent step events + text tokens
- UI-03 upgrade: WebSocket client, streaming display, Agent Reasoning Panel (collapsible, real-time steps)
- UI-04 Analytics Report View: KPI grid, all 4 Recharts chart types, insight cards
- UI-05 Action Confirmation Panel: modal overlay, dynamic CTA, Approve/Cancel buttons

**Success Criteria:**
- "Give me a business review for last month" returns a report with ≥3 KPIs, ≥2 charts, ≥3 insights in ≤30 seconds
- LangSmith trace shows ≥4 distinct agent invocations for analytics pipeline
- "Create a quotation for [Customer]" triggers Confirmation Panel before any Odoo write
- Cancelling the Confirmation Panel writes a `cancelled_by_user` entry to audit log
- Confirming creates the Odoo record and returns the record ID
- Agent Reasoning Panel shows live steps while response is streaming

**Risks:**
- Analytics pipeline latency may exceed 30s — identify bottleneck agent; add parallel Odoo calls where possible
- KPI Computation Agent produces wrong numbers — add unit tests verifying against known mock data values
- WebSocket stability issues — implement polling fallback immediately as contingency

---

## Sprint 3 — Procurement Module Core: Monitor + Forecast + RFQ (2 Weeks)

**Goal:** The Module 2 core pipeline is working end-to-end: the system detects at-risk inventory, generates demand forecasts, ranks suppliers, produces draft RFQs, and the procurement manager can approve or reject them from the UI — causing an actual Odoo RFQ record to be created.

**Deliverables:**
- Procurement Orchestrator (AGENT-2-01): scheduling, sub-agent coordination, state management
- Inventory Monitor Agent (AGENT-2-02): full product catalog scan, risk state computation, alert generation
- Demand Forecaster Agent (AGENT-2-03): 90-day history analysis, stockout projection, confidence levels, MOQ respect
- Supplier Evaluator Agent (AGENT-2-04): deterministic scoring, per-product ranking, new-supplier flag
- RFQ Generator Agent (AGENT-2-05): draft RFQ objects, shared-supplier combination logic, confirmation gate trigger
- Procurement Confirmation Gate: draft storage, approve/reject endpoints, Odoo write on approval, audit log
- All Module 2 API endpoints per Section 16.2
- UI-06 Procurement Dashboard: health score, alert panel, risk summary
- UI-07 Product Risk List: filterable/sortable, risk state badges, projected stockout dates
- UI-08 RFQ Review Panel: draft cards, supplier score badges, AI rationale, approval bar

**Success Criteria:**
- Monitoring cycle scans all 50 products and correctly classifies ≥10 as CRITICAL/AT RISK
- Demand forecast for a CRITICAL product includes projected stockout date and confidence level
- 3 draft RFQs visible in procurement dashboard before any user interaction
- Approving an RFQ creates a `purchase.order` in RFQ state in Odoo with correct product, quantity, and supplier
- Rejecting an RFQ writes a "rejected" entry to audit log; no Odoo record created
- Supplier with low on-time delivery receives lower score than reliable supplier in comparison

**Risks:**
- Demand forecasting logic errors causing incorrect stockout dates — validate against manually computed values from mock data
- Procurement orchestrator state machine complexity — simplify: sequential pipeline, not fully parallel, for MVP
- Module 2 may be underestimated — Supplier Evaluator Agent can be descoped to basic scoring if Sprint 3 is tight

---

## Sprint 4 — OCR, Supplier Comparison UI, Polish & Hardening (2 Weeks)

**Goal:** OCR supplier quote processing is working. The supplier comparison UI is built. All Should Have features are delivered. The system is hardened against the known risks. Demo scenarios are scripted and rehearsed once.

**Deliverables:**
- OCR Agent (AGENT-2-06): GPT-4o Vision extraction, confidence scoring, low-confidence highlighting
- File upload endpoint + quote review endpoint
- UI-10 Quote Upload & Review: drag-and-drop, editable extraction table, confidence highlights
- UI-09 Supplier Comparison Panel: side-by-side table, radar chart, supplier override
- UI-11 Audit Log Viewer: paginated, filterable
- Proactive alert push: real-time notifications when product crosses risk threshold (WebSocket or polling)
- Arabic RTL report formatting (full report layout, not just response text)
- Period-over-period comparison visible in all analytics KPIs
- Combined RFQ suggestion when ≥2 at-risk products share a supplier
- Procurement Health Score composite calculation finalized
- All LangSmith `@traceable` wrappers verified
- First full demo scenario dry-run (all 5 scenarios)

**Success Criteria:**
- OCR processes mock supplier PDF and extracts supplier name, unit price, lead time with ≥80% accuracy
- Low-confidence fields are highlighted in the review table
- Supplier comparison panel shows radar chart and correct ranking
- Arabic executive review report renders with RTL formatting
- First dry-run: ≥4 of 5 demo scenarios complete without agent failure

**Risks:**
- OCR accuracy on PDF layout variations — restrict demo to single controlled PDF template; document this limitation
- Scope creep pulling engineers into polish over substance — PM (Engineer A) enforces feature freeze after Week 1 of Sprint 4
- First dry-run failures requiring significant rework — if this happens, defer OCR/UI-10 and focus on core scenario stability

---

## Sprint 5 — Integration, Final Hardening & Demo Day (1 Week)

**Goal:** Zero-failure demo. Every acceptance criterion from the PRD is verified. The Docker Compose stack is demo-ready and committed as a snapshot. The demo script is finalized. Three full rehearsals are completed.

**Deliverables:**
- Full acceptance criterion verification against PRD Section 13
- Performance verification: simple query ≤5s, analytics ≤30s, RFQ generation ≤15s, monitoring cycle ≤60s
- Arabic NLP final validation: ≥18/20 test queries correctly classified
- Docker Compose clean-start test on a machine that has never run the project
- Odoo Docker volume snapshot committed (pre-seeded data backup)
- Demo environment setup guide (`DEMO_SETUP.md`)
- Demo script (`DEMO_SCRIPT.md`): exact steps, expected outputs, fallback plans, talking points
- ≥3 full rehearsals of all 5 demo scenarios
- All critical bugs from Sprint 4 dry-run fixed
- README.md complete: project overview, setup instructions, architecture diagram
- LangSmith trace screenshots documented for presentation use

**Success Criteria:**
- All 8 quality gates from PRD Section 20.4 pass in 48-hour pre-demo dry-run:
  1. All 5 demo scenarios complete without agent failure
  2. Arabic queries return correct RTL responses
  3. LangSmith traces visible for all multi-agent workflows
  4. Confirmation gate intercepts all write operations
  5. ≥3 RFQ drafts visible in procurement dashboard
  6. Analytics KPI values match mock dataset ground truth
  7. Docker Compose starts cleanly from fresh repository clone
  8. Audit log contains entries from all demo scenario write actions

**Risks:**
- Critical bug discovered in final week — maintain a prioritized bug list; know which bugs are demo-blocking vs. cosmetic
- Demo machine environment differences — test Docker Compose on the actual demo machine ≥48 hours before demo day

---

# PART 3 — Detailed Task Breakdown

*Legend: SP = Story Points (1=trivial, 2=simple, 3=medium, 5=complex, 8=very complex)*

---

## Sprint 0 Tasks

### Feature: Environment & Infrastructure

**Task: Docker Compose Stack**
- Subtask: Write `docker-compose.yml` with all 7 services | SP: 3 | Complexity: Medium
- Subtask: Configure Odoo service with environment variables and volume mounts | SP: 2 | Complexity: Low
- Subtask: Configure PostgreSQL (Odoo DB) with init scripts | SP: 1 | Complexity: Low
- Subtask: Configure PostgreSQL (App DB) with init scripts | SP: 1 | Complexity: Low
- Subtask: Configure Redis service | SP: 1 | Complexity: Low
- Subtask: Configure Chroma service | SP: 1 | Complexity: Low
- Subtask: Write `.env.example` with all required variables documented | SP: 1 | Complexity: Low
- Subtask: Verify all services start and are healthy (`docker-compose up`) | SP: 2 | Complexity: Medium

**Task: OdooClient Foundation**
- Subtask: Implement `authenticate()` with session management | SP: 3 | Complexity: Medium | Dep: Odoo running
- Subtask: Implement `search_read()` with pagination + logging | SP: 3 | Complexity: Medium
- Subtask: Implement write method stubs (gated, placeholder confirmation check) | SP: 2 | Complexity: Low
- Subtask: Implement rate limiter (token bucket, 10 calls/sec) | SP: 2 | Complexity: Medium
- Subtask: Implement retry logic (1 retry on failure) | SP: 2 | Complexity: Low
- Subtask: Unit tests for OdooClient | SP: 3 | Complexity: Medium

**Task: Mock Data Generation**
- Subtask: Write `seed_mock_data.py` skeleton with Odoo write utilities | SP: 2 | Complexity: Low
- Subtask: Generate and seed customers (15) with Arabic names | SP: 2 | Complexity: Low
- Subtask: Generate and seed suppliers (10) with varied performance profiles | SP: 2 | Complexity: Low
- Subtask: Generate and seed products (50) with categories, Arabic names, reorder points | SP: 3 | Complexity: Medium
- Subtask: Generate and seed sales orders (300) + order lines (800) | SP: 5 | Complexity: Complex | Dep: Products, Customers seeded
- Subtask: Generate and seed invoices (200) with correct partner and amount linkage | SP: 3 | Complexity: Medium
- Subtask: Generate and seed purchase orders (150) + lines (400) | SP: 3 | Complexity: Medium
- Subtask: Generate and seed stock quantities (50) with correct health distribution | SP: 2 | Complexity: Low
- Subtask: Generate and seed reorder rules (50) | SP: 2 | Complexity: Low
- Subtask: Generate and seed supplier pricelists (100) | SP: 2 | Complexity: Low
- Subtask: Implement idempotency (skip if records already exist) | SP: 3 | Complexity: Medium
- Subtask: Write `demo_data_guide.md` documenting key data stories | SP: 2 | Complexity: Low

**Task: Schema Registry**
- Subtask: Author `schema_registry.yaml` for all required Odoo models and fields | SP: 3 | Complexity: Medium
- Subtask: Implement `schema_validate.py` comparing registry against live Odoo | SP: 2 | Complexity: Medium
- Subtask: Run validation and fix mismatches | SP: 2 | Complexity: Low

**Task: Project Skeleton**
- Subtask: Initialize FastAPI project with folder structure | SP: 1 | Complexity: Low
- Subtask: Configure `structlog` for JSON logging | SP: 1 | Complexity: Low
- Subtask: Health endpoint (`GET /health`) | SP: 1 | Complexity: Low
- Subtask: Initialize Next.js project with Tailwind, Arabic fonts | SP: 2 | Complexity: Low

---

## Sprint 1 Tasks

### Feature: Authentication & Session Management

**Task: Authentication API**
- Subtask: User table migration + seed (5 test users, one per role) | SP: 2 | Complexity: Low
- Subtask: `POST /auth/login` — bcrypt validation, JWT issuance, httpOnly cookie | SP: 3 | Complexity: Medium
- Subtask: `POST /auth/refresh` — refresh token validation, new access token | SP: 2 | Complexity: Low
- Subtask: `POST /auth/logout` — cookie clear | SP: 1 | Complexity: Low
- Subtask: `require_role` FastAPI dependency (role enum, route protection) | SP: 2 | Complexity: Low
- Subtask: Unit tests for auth endpoints | SP: 2 | Complexity: Low

**Task: Audit Log Infrastructure**
- Subtask: `audit_log` table migration (INSERT-ONLY schema) | SP: 1 | Complexity: Low
- Subtask: `AuditLogger` service class | SP: 2 | Complexity: Low
- Subtask: Unit tests for AuditLogger | SP: 1 | Complexity: Low

**Task: Redis Session Management**
- Subtask: `get_session_context(session_id)` | SP: 1 | Complexity: Low
- Subtask: `update_session_context(session_id, update)` | SP: 1 | Complexity: Low
- Subtask: `delete_session_context(session_id)` | SP: 1 | Complexity: Low
- Subtask: Context schema: 10-turn window, truncation logic | SP: 2 | Complexity: Low
- Subtask: Session expiry: 60 min inactivity, graceful reset message | SP: 2 | Complexity: Low

### Feature: Copilot Orchestrator

**Task: Language Detection Tool**
- Subtask: Implement `detect_language(text)` → ISO 639-1 | SP: 2 | Complexity: Low

**Task: Intent Classifier**
- Subtask: Implement `classify_intent(text, context)` — prompt engineering for all intent codes | SP: 5 | Complexity: Complex
- Subtask: Intent confidence threshold logic (< 0.70 → clarification) | SP: 2 | Complexity: Low
- Subtask: Multi-intent extraction (sequential intent handling) | SP: 3 | Complexity: Medium
- Subtask: Arabic intent classification prompt iteration (30-query test set) | SP: 5 | Complexity: Complex

**Task: LangGraph CopilotGraph v1**
- Subtask: State schema definition (`CopilotState`) | SP: 2 | Complexity: Low
- Subtask: Orchestrator node implementation | SP: 3 | Complexity: Medium
- Subtask: ERP Query Agent node implementation | SP: 3 | Complexity: Medium
- Subtask: Routing conditional edges | SP: 2 | Complexity: Medium
- Subtask: Terminal state + response assembly | SP: 2 | Complexity: Low
- Subtask: LangSmith `@traceable` on all nodes | SP: 1 | Complexity: Low

### Feature: ERP Query Agent

**Task: Entity Resolver**
- Subtask: `resolve_entity(name, model_type)` → fuzzy match to Odoo record ID | SP: 3 | Complexity: Medium
- Subtask: Arabic name entity resolution | SP: 3 | Complexity: Medium
- Subtask: Entity resolution failure handling | SP: 2 | Complexity: Low

**Task: Domain Filter Builder**
- Subtask: `build_domain_filter(entities, time_range, filters)` | SP: 3 | Complexity: Medium
- Subtask: Relative date resolution ("last month" → absolute date range) | SP: 2 | Complexity: Low

**Task: Query Execution & Formatting**
- Subtask: `odoo_search_read()` wrapper with pagination | SP: 2 | Complexity: Low
- Subtask: `format_data_response()` — table, list, summary formats in EN/AR | SP: 3 | Complexity: Medium
- Subtask: Schema registry `lookup_schema()` integration | SP: 2 | Complexity: Low

### Feature: Copilot REST API

**Task: Session + Chat Endpoints**
- Subtask: `POST /api/v1/copilot/session` | SP: 1 | Complexity: Low
- Subtask: `DELETE /api/v1/copilot/session/{id}` | SP: 1 | Complexity: Low
- Subtask: `POST /api/v1/copilot/chat` (non-streaming) | SP: 2 | Complexity: Low

### Feature: Basic Chat UI

**Task: UI-01 Login Page**
- Subtask: Login form component, JWT cookie handling | SP: 2 | Complexity: Low

**Task: UI-03 Basic Chat (Non-Streaming)**
- Subtask: Chat message history component | SP: 2 | Complexity: Low
- Subtask: Text input + submit | SP: 1 | Complexity: Low
- Subtask: Language toggle (AR/EN), RTL layout switching | SP: 3 | Complexity: Medium
- Subtask: Loading indicator | SP: 1 | Complexity: Low

---

## Sprint 2 Tasks

### Feature: Analytics Multi-Agent System

**Task: Analytics Supervisor**
- Subtask: `AnalyticsSupervisor` node (AGENT-1-04): receive intent, coordinate sub-graph, assemble report | SP: 5 | Complexity: Complex
- Subtask: LangGraph Analytics sub-graph: state schema + node wiring | SP: 5 | Complexity: Complex

**Task: Data Retrieval Agent (AGENT-1-05)**
- Subtask: Multi-period data fetcher: current period + prior period for all required models | SP: 5 | Complexity: Complex
- Subtask: Structured `AnalyticsDataPayload` return type | SP: 2 | Complexity: Low

**Task: KPI Computation Agent (AGENT-1-06)**
- Subtask: Revenue computation (total, by month, period-over-period delta) | SP: 3 | Complexity: Medium
- Subtask: Top customers by revenue (top 5) | SP: 2 | Complexity: Low
- Subtask: Top products by revenue | SP: 2 | Complexity: Low
- Subtask: Order count, avg order value | SP: 2 | Complexity: Low
- Subtask: Outstanding invoice total | SP: 2 | Complexity: Low
- Subtask: Stock health summary | SP: 2 | Complexity: Low
- Subtask: Typed `KPIReport` Pydantic model | SP: 2 | Complexity: Low
- Subtask: Unit tests verifying KPIs against known mock data values | SP: 3 | Complexity: Medium

**Task: Visualization Agent (AGENT-1-07)**
- Subtask: Chart type selection logic | SP: 2 | Complexity: Low
- Subtask: Revenue bar chart JSON (Recharts config) | SP: 2 | Complexity: Low
- Subtask: Trend line chart JSON | SP: 2 | Complexity: Low
- Subtask: Customer mix pie chart JSON | SP: 2 | Complexity: Low
- Subtask: Product table data structure | SP: 1 | Complexity: Low

**Task: Insight Generation Agent (AGENT-1-08)**
- Subtask: Grounded insight prompt (data-reference-only constraint) | SP: 3 | Complexity: Medium
- Subtask: Arabic insight generation | SP: 3 | Complexity: Medium
- Subtask: Insight output validation (references only present data values) | SP: 2 | Complexity: Low

**Task: Analytics API**
- Subtask: Analytics intent routing in CopilotGraph | SP: 2 | Complexity: Low
- Subtask: Report storage (app DB or Redis cache) | SP: 2 | Complexity: Low
- Subtask: `GET /api/v1/copilot/reports/{report_id}` | SP: 1 | Complexity: Low

### Feature: ERP Action Agent & Confirmation Gate

**Task: ERP Action Agent (AGENT-1-03)**
- Subtask: Missing field extraction + clarification request loop | SP: 5 | Complexity: Complex
- Subtask: Entity validation (pre-confirmation) | SP: 2 | Complexity: Low
- Subtask: Confirmation Summary builder (bilingual, structured) | SP: 3 | Complexity: Medium
- Subtask: Odoo write execution on approval | SP: 3 | Complexity: Medium
- Subtask: Audit log write (success / failure / cancelled_by_user) | SP: 2 | Complexity: Low

**Task: Confirmation Gate**
- Subtask: Confirmation token generation (UUID, TTL=10min, Redis storage) | SP: 2 | Complexity: Low
- Subtask: `POST /api/v1/copilot/actions/{action_id}/confirm` with session + token validation | SP: 3 | Complexity: Medium
- Subtask: `POST /api/v1/copilot/actions/{action_id}/reject` | SP: 2 | Complexity: Low
- Subtask: Replay protection (mark token as used on first call) | SP: 2 | Complexity: Low

### Feature: Streaming UI

**Task: WebSocket Streaming**
- Subtask: FastAPI WebSocket endpoint (`WS /api/v1/copilot/chat/stream`) | SP: 5 | Complexity: Complex
- Subtask: Message type implementations: agent_step, text_token, chart_ready, action_required, complete, error | SP: 3 | Complexity: Medium
- Subtask: Polling fallback (`POST /chat` with full response) | SP: 2 | Complexity: Low

**Task: UI-03 Streaming Chat Upgrade**
- Subtask: WebSocket client with reconnection logic | SP: 3 | Complexity: Medium
- Subtask: Streaming message display (incremental token rendering) | SP: 2 | Complexity: Medium
- Subtask: Agent Reasoning Panel component (collapsible, real-time step list) | SP: 3 | Complexity: Medium

**Task: UI-04 Analytics Report View**
- Subtask: KPI grid component (metric + delta badge, green/red coloring) | SP: 2 | Complexity: Low
- Subtask: `RevenueBarChart` component (Recharts) | SP: 2 | Complexity: Low
- Subtask: `TrendLineChart` component (Recharts) | SP: 2 | Complexity: Low
- Subtask: `CustomerPieChart` component (Recharts) | SP: 2 | Complexity: Low
- Subtask: `ProductTable` component | SP: 2 | Complexity: Low
- Subtask: Insight cards | SP: 2 | Complexity: Low
- Subtask: Arabic RTL layout for full report | SP: 3 | Complexity: Medium

**Task: UI-05 Action Confirmation Panel**
- Subtask: Modal overlay component (non-dismissable) | SP: 2 | Complexity: Low
- Subtask: Action summary display (structured, bilingual) | SP: 2 | Complexity: Low
- Subtask: "Confirm & Execute" + "Cancel" buttons with API calls | SP: 2 | Complexity: Low
- Subtask: Success/error toast on completion | SP: 1 | Complexity: Low

---

## Sprint 3 Tasks

### Feature: Procurement Orchestrator & Monitoring

**Task: Procurement Orchestrator (AGENT-2-01)**
- Subtask: LangGraph `ProcurementGraph` state schema | SP: 3 | Complexity: Medium
- Subtask: Scheduling logic: APScheduler or Celery Beat (configurable interval) | SP: 3 | Complexity: Medium
- Subtask: On-demand trigger: `POST /api/v1/procurement/monitoring/run` | SP: 1 | Complexity: Low
- Subtask: Sub-agent coordination: sequential pipeline (Monitor → Forecast → Evaluate → Generate) | SP: 3 | Complexity: Medium

**Task: Inventory Monitor Agent (AGENT-2-02)**
- Subtask: Full product catalog scan from Odoo (all 50 products) | SP: 3 | Complexity: Medium
- Subtask: Risk state computation (CRITICAL / AT RISK / WATCH / HEALTHY formula) | SP: 3 | Complexity: Medium
- Subtask: Alert object generation for state transitions | SP: 2 | Complexity: Low
- Subtask: Alert storage in app DB | SP: 2 | Complexity: Low
- Subtask: `GET /api/v1/procurement/alerts` endpoint | SP: 1 | Complexity: Low
- Subtask: `GET /api/v1/procurement/products` with risk states | SP: 1 | Complexity: Low
- Subtask: Unit tests: verify correct risk states on known mock data | SP: 3 | Complexity: Medium

**Task: Demand Forecaster Agent (AGENT-2-03)**
- Subtask: 90-day sales history fetch per product | SP: 2 | Complexity: Low
- Subtask: Simple moving average implementation | SP: 3 | Complexity: Medium
- Subtask: Projected stockout date computation | SP: 3 | Complexity: Medium
- Subtask: Confidence level logic (HIGH/MEDIUM/LOW thresholds) | SP: 2 | Complexity: Low
- Subtask: MOQ enforcement from `product.supplierinfo` | SP: 2 | Complexity: Low
- Subtask: `GET /api/v1/procurement/products/{product_id}/forecast` endpoint | SP: 1 | Complexity: Low
- Subtask: Unit tests: verify forecast values and stockout dates | SP: 3 | Complexity: Medium

**Task: Supplier Evaluator Agent (AGENT-2-04)**
- Subtask: PO history fetch per supplier per product | SP: 2 | Complexity: Low
- Subtask: Deterministic scoring: price consistency (25%), on-time delivery (35%), fulfillment accuracy (25%), lead time (15%) | SP: 5 | Complexity: Complex
- Subtask: LLM rationale generation (grounded to scoring output only) | SP: 3 | Complexity: Medium
- Subtask: "New Supplier — Limited Data" flag logic | SP: 2 | Complexity: Low
- Subtask: Per-product supplier ranking storage | SP: 2 | Complexity: Low
- Subtask: `GET /api/v1/procurement/suppliers` + `GET .../suppliers/{product_id}/ranking` | SP: 2 | Complexity: Low

**Task: RFQ Generator Agent (AGENT-2-05)**
- Subtask: Draft RFQ object construction (product, qty, supplier, price estimate) | SP: 3 | Complexity: Medium
- Subtask: Shared-supplier detection and combination logic | SP: 3 | Complexity: Medium
- Subtask: Draft RFQ storage in app DB (`rfq_draft` table) | SP: 2 | Complexity: Low
- Subtask: `GET /api/v1/procurement/rfq/drafts` endpoint | SP: 1 | Complexity: Low
- Subtask: `POST /api/v1/procurement/rfq/generate` (manual trigger) | SP: 1 | Complexity: Low

**Task: Procurement Confirmation Gate**
- Subtask: `POST /rfq/drafts/{draft_id}/approve`: token validation → Odoo `purchase.order` create → audit log | SP: 5 | Complexity: Complex
- Subtask: `POST /rfq/drafts/{draft_id}/reject`: discard draft → audit log with reason | SP: 2 | Complexity: Low
- Subtask: Batch approval support | SP: 3 | Complexity: Medium

**Task: Procurement Dashboard UI**
- Subtask: UI-06 Procurement Dashboard: health score gauge, alert panel, risk summary widgets | SP: 5 | Complexity: Complex
- Subtask: UI-07 Product Risk List: table with risk badges, stockout dates, forecast links | SP: 3 | Complexity: Medium
- Subtask: UI-08 RFQ Review Panel: draft cards, supplier badges, AI rationale, approval bar | SP: 5 | Complexity: Complex

---

## Sprint 4 Tasks

### Feature: OCR Supplier Quote Processing

**Task: OCR Agent (AGENT-2-06)**
- Subtask: GPT-4o Vision integration for PDF → structured JSON extraction | SP: 5 | Complexity: Complex
- Subtask: Confidence scoring per extracted field | SP: 3 | Complexity: Medium
- Subtask: Tesseract fallback implementation | SP: 3 | Complexity: Medium
- Subtask: Arabic PDF handling | SP: 2 | Complexity: Medium

**Task: File Upload Infrastructure**
- Subtask: `POST /api/v1/procurement/quotes/upload` with PDF validation (type, size) | SP: 3 | Complexity: Medium
- Subtask: Quote storage in app DB | SP: 2 | Complexity: Low
- Subtask: `GET /api/v1/procurement/quotes/{quote_id}` | SP: 1 | Complexity: Low

**Task: UI-10 Quote Upload & Review**
- Subtask: PDF drag-and-drop upload component | SP: 3 | Complexity: Medium
- Subtask: Editable extraction result table with confidence highlighting | SP: 3 | Complexity: Medium

### Feature: Supplier Comparison & Remaining UI

**Task: UI-09 Supplier Comparison Panel**
- Subtask: Side-by-side supplier comparison table | SP: 3 | Complexity: Medium
- Subtask: Radar chart (Recharts `RadarChart`) | SP: 3 | Complexity: Medium
- Subtask: Supplier override button with re-draft RFQ trigger | SP: 2 | Complexity: Low

**Task: UI-11 Audit Log Viewer**
- Subtask: Paginated audit log table (admin only) | SP: 2 | Complexity: Low
- Subtask: Filter by action type, date range, user | SP: 2 | Complexity: Low

### Feature: Polish & Hardening

**Task: Proactive Alerts Push**
- Subtask: WebSocket or polling endpoint for real-time alert notifications | SP: 3 | Complexity: Medium
- Subtask: Alert notification component in UI (dismiss, link to product) | SP: 2 | Complexity: Low

**Task: Performance & Reliability**
- Subtask: Analytics pipeline latency audit + optimization | SP: 3 | Complexity: Medium
- Subtask: LangSmith `@traceable` verification on all agent nodes | SP: 2 | Complexity: Low
- Subtask: Max tool call limiter (hard limit 10 per agent invocation) | SP: 2 | Complexity: Low
- Subtask: LLM API timeout fallback (30s → graceful error message) | SP: 2 | Complexity: Low
- Subtask: Odoo API failure retry + graceful error | SP: 2 | Complexity: Low

**Task: Demo Preparation**
- Subtask: Full demo scenario dry-run (all 5 scenarios) | SP: 3 | Complexity: Medium
- Subtask: Bug triage from dry-run (P0/P1/P2 classification) | SP: 2 | Complexity: Low
- Subtask: `DEMO_SCRIPT.md` draft | SP: 2 | Complexity: Low

---

## Sprint 5 Tasks

**Task: Acceptance Criterion Verification**
- All 8 quality gates from PRD Section 20.4 verified and documented | SP: 5 | Complexity: Complex

**Task: Final Demo Hardening**
- Docker Compose clean-start test on fresh machine | SP: 2 | Complexity: Low
- Odoo Docker volume snapshot committed | SP: 1 | Complexity: Low
- `DEMO_SETUP.md` written | SP: 2 | Complexity: Low
- `DEMO_SCRIPT.md` finalized | SP: 3 | Complexity: Medium
- ≥3 full rehearsals | SP: 3 | Complexity: Medium

**Task: Documentation**
- `README.md` complete | SP: 2 | Complexity: Low
- Architecture diagram | SP: 2 | Complexity: Low
- LangSmith trace screenshots documented | SP: 1 | Complexity: Low

---

# PART 4 — Development Order & Dependency Graph

---

## Strict Dependency Chain (Cannot Be Parallelized)

```
[1] Docker Compose + Odoo Running (Epic 1)
        │
        ▼
[2] Mock Data Seeded + Schema Validated (Epic 1)
        │
        ▼
[3] OdooClient Foundation (Epic 3)
        │
        ├──────────────────────┐
        ▼                      ▼
[4a] Authentication +     [4b] Schema Registry +
     Session (Epic 2)          Entity Resolver (Epic 3)
        │                      │
        └──────────┬───────────┘
                   ▼
[5] Copilot Orchestrator + ERP Query Agent (Epic 4)
        │
        ├─────────────────────────────┐
        ▼                             ▼
[6a] Analytics Pipeline          [6b] ERP Action Agent +
     (Epic 6)                         Confirmation Gate (Epic 5)
        │                             │
        └──────────┬──────────────────┘
                   ▼
[7] Procurement Orchestrator + Core Agents (Epic 7)
        │
        ▼
[8] OCR Agent (Epic 8)
        │
        ▼
[9] Full UI (Epic 9) — parallelized with 6a, 6b, 7
        │
        ▼
[10] Observability + Hardening (Epic 10)
```

---

## What Can Be Parallelized

After Sprint 0 is complete (items 1–2 above), the following work streams can run in parallel:

**Stream A — Backend AI (Engineers A + B):** Copilot Orchestrator → ERP Query Agent → Analytics Pipeline → ERP Action Agent → Confirmation Gate

**Stream B — Procurement (Engineers C + D):** Procurement Orchestrator → Inventory Monitor → Demand Forecaster → Supplier Evaluator → RFQ Generator

**Stream C — Frontend (Engineer E):** Basic Chat UI (Sprint 1) → Streaming UI + Analytics View + Confirmation Panel (Sprint 2) → Procurement Dashboard (Sprint 3) → OCR + Supplier UI + Audit Log (Sprint 4)

**Stream D — Data + DevOps (Engineer F):** Mock data (Sprint 0) → OdooClient hardening → Data validation → Performance testing → Docker snapshot → Demo environment

Streams A and B can run in parallel starting Sprint 1 because both depend only on the OdooClient and Schema Registry (Sprint 0 outputs), not on each other.

Stream C (Frontend) depends on API contracts from Streams A and B but can proceed with mock API responses before backend completion.

---

## What Should Be Delayed

- OCR Agent (Epic 8): Delay until Sprint 4. Depends on Procurement core being stable (Epic 7). High OCR failure risk — keep at the end where it is deferrable.
- Module 3 Customer Support: Delay indefinitely until Modules 1 and 2 are complete and demo-tested. Per PRD: this is a stretch goal only.
- Supplier Intelligence Profile pages (separate supplier CRM view): Not in MVP. Rank in RFQ panel only.
- Scenario Simulation ("What If" analysis): Nice to Have. Only consider in Sprint 4 if all Must Have items are complete.
- Voice-to-text input: Removed from MVP per PRD Section 20.2.
- Cross-session memory: Removed from MVP per PRD Section 20.3.

---

## Critical Path

The critical path runs through:

**Odoo Up → OdooClient → Orchestrator → ERP Query Agent → Analytics Pipeline → Confirmation Gate → Procurement Core → Full UI → Demo Hardening**

Any delay on this path delays the demo. Procurement (Stream B) is the second-longest chain and becomes the new critical path from Sprint 3 onward if the analytics pipeline slips.

---

# PART 5 — Engineer Allocation

---

## Engineer A — Agent Systems Lead

**Primary Role:** LangGraph architecture, Copilot Orchestrator, Analytics Supervisor, overall agent coordination

**Owned Components:**
- LangGraph `CopilotGraph` state machine design and implementation
- Copilot Orchestrator (AGENT-1-01): intent classifier, session context, routing logic
- Analytics Supervisor (AGENT-1-04): sub-agent coordination, report assembly
- KPI Computation Agent (AGENT-1-06): code-only computation logic
- Insight Generation Agent (AGENT-1-08): prompt engineering, grounding constraints
- Cross-agent typing: shared Pydantic models for all agent inputs/outputs
- LangSmith integration: `@traceable` wrappers on all agent nodes
- **Sprint 0 contribution:** LangGraph environment validation, agent communication patterns established

**Does Not Own:** OdooClient, Frontend, Procurement agents

**Pairing:** Works closely with Engineer B (ERP Integration) on agent-to-Odoo interface design

---

## Engineer B — ERP Integration Engineer

**Primary Role:** OdooClient, Schema Registry, Entity Resolver, ERP Query Agent, ERP Action Agent

**Owned Components:**
- `OdooClient` class: full implementation (authenticate, search_read, create, write, execute_action, rate limiter, retry, logging)
- `schema_registry.yaml` authorship and maintenance
- `schema_validate.py`
- Entity Resolver service
- Domain Filter Builder
- ERP Query Agent (AGENT-1-02): entity resolution, query construction, result formatting
- ERP Action Agent (AGENT-1-03): field extraction, entity validation, confirmation summary, write execution
- Confirmation Gate backend: token generation, confirm/reject endpoints, replay protection
- Audit log entries for all write operations
- **Sprint 0 contribution:** OdooClient foundation, schema registry, schema validation

**Does Not Own:** Analytics sub-agents (except data retrieval), Procurement agents, Frontend

**Pairing:** Works with Engineer A on agent integration; works with Engineer D on data seeding and OdooClient testing

---

## Engineer C — Procurement AI Engineer

**Primary Role:** Demand Forecasting, Supplier Scoring, RFQ Generation, Procurement Orchestrator

**Owned Components:**
- Procurement Orchestrator (AGENT-2-01): scheduling, sub-agent pipeline coordination
- Demand Forecaster Agent (AGENT-2-03): SMA implementation, stockout projection, confidence levels, MOQ enforcement
- Supplier Evaluator Agent (AGENT-2-04): deterministic scoring model, rationale generation, product-specific rankings
- RFQ Generator Agent (AGENT-2-05): draft RFQ construction, shared-supplier detection, combination logic
- Procurement Confirmation Gate: approve/reject endpoints, Odoo PO creation, audit log
- All Module 2 API endpoints
- **Sprint 0 contribution:** Helps with mock data design (supplier performance profiles, demand patterns)

**Does Not Own:** Inventory Monitor (Engineer D), OCR Agent, Frontend

**Pairing:** Works with Engineer D on Inventory Monitor outputs (inputs to forecasting); works with Engineer E on procurement UI API contracts

---

## Engineer D — DevOps / Data / Inventory Monitor Engineer

**Primary Role:** Mock data generation, infrastructure, Inventory Monitor Agent, performance testing

**Owned Components:**
- `seed_mock_data.py`: complete implementation, idempotency, all entity types
- `demo_data_guide.md`
- Docker Compose stack: all services configured, health checks, volume mounts
- Inventory Monitor Agent (AGENT-2-02): full product catalog scan, risk state computation, alert generation and storage
- APScheduler/scheduling infrastructure for procurement monitoring cycles
- Chroma setup (for Schema Registry semantic search if implemented)
- Performance testing: response time measurement, concurrent load test (5 users)
- Demo environment: Docker volume snapshot, clean-start verification
- `DEMO_SETUP.md`
- **Sprint 0 contribution:** Primary owner of all Sprint 0 deliverables

**Does Not Own:** Agent logic, Frontend, Procurement algorithms

**Pairing:** Works with Engineer C on Inventory Monitor → Procurement Orchestrator interface; works with Engineer B on OdooClient testing

---

## Engineer E — Frontend Engineer

**Primary Role:** All React/Next.js UI components, WebSocket client, RTL Arabic layout

**Owned Components:**
- Next.js project setup, Tailwind configuration, Arabic font loading
- UI-01 Login Page
- UI-02 Main Dashboard
- UI-03 Copilot Chat Interface (basic → streaming → Agent Reasoning Panel)
- UI-04 Analytics Report View (all Recharts components)
- UI-05 Action Confirmation Panel
- UI-06 Procurement Dashboard
- UI-07 Product Risk List
- UI-08 RFQ Review Panel (all sub-components)
- UI-09 Supplier Comparison Panel (table + radar chart)
- UI-10 Quote Upload & Review
- UI-11 Audit Log Viewer
- WebSocket client implementation + streaming display
- RTL layout system (global AR/EN toggle, direction-aware components)
- Design system: color tokens, typography, shared components (badges, cards, empty states, skeleton loaders, toasts)
- **Sprint 0 contribution:** Next.js skeleton, Tailwind + fonts configured

**Does Not Own:** Backend, agents, data

**Pairing:** Works closely with Engineers A, B, C, D to align on API contracts; can start with mock API responses when backend is in progress

---

## Engineer F — NLP & LLM Engineer

**Primary Role:** Arabic NLP, prompt engineering across all agents, Data Retrieval Agent, structured output validation

**Owned Components:**
- Arabic NLP validation test set (30 queries, expected intents, expected languages)
- Intent classifier prompt engineering (primary responsibility in Sprint 1)
- Arabic response formatting (RTL, number formatting, business terminology)
- Prompt engineering for all agents: Orchestrator, ERP Query, ERP Action, Analytics Insight, Procurement rationale
- Data Retrieval Agent (AGENT-1-05): multi-period data fetching logic
- Structured output validation: Pydantic models for all LLM outputs
- GPT-4o-mini vs GPT-4o routing logic (cost optimization: mini for simple queries)
- OCR Agent (AGENT-2-06): GPT-4o Vision integration, prompt engineering for extraction, confidence scoring
- LLM prompt library maintenance (`prompts/` directory)
- **Sprint 0 contribution:** NLP environment setup, first Arabic test query validation

**Does Not Own:** Frontend, OdooClient, Procurement algorithms (scoring is code-only)

**Pairing:** Works with Engineer A on all agent prompts; works with Engineer C on OCR agent; works with Engineer E on Arabic UI formatting requirements

---

## Allocation Summary Table

| Component | Owner | Sprint |
|---|---|---|
| Docker Compose + Infrastructure | D | 0 |
| Mock Data + Data Guide | D | 0 |
| OdooClient | B | 0–1 |
| Schema Registry + Validation | B | 0 |
| Authentication + JWT | B | 1 |
| Session Context (Redis) | A | 1 |
| Audit Log | B | 1 |
| Copilot Orchestrator | A | 1 |
| ERP Query Agent | B | 1 |
| LangGraph CopilotGraph | A | 1 |
| Arabic NLP + Intent Classifier | F | 1–2 |
| Chat UI (Basic → Streaming) | E | 1–2 |
| Analytics Supervisor | A | 2 |
| Data Retrieval Agent | F | 2 |
| KPI Computation Agent | A | 2 |
| Visualization Agent | A | 2 |
| Insight Generation Agent | F | 2 |
| ERP Action Agent | B | 2 |
| Confirmation Gate (Backend) | B | 2 |
| WebSocket Streaming | A+B | 2 |
| Analytics UI + Report View | E | 2 |
| Confirmation Panel UI | E | 2 |
| Procurement Orchestrator | C | 3 |
| Inventory Monitor | D | 3 |
| Demand Forecaster | C | 3 |
| Supplier Evaluator | C | 3 |
| RFQ Generator | C | 3 |
| Procurement Confirmation Gate | C+B | 3 |
| Procurement Dashboard UI | E | 3 |
| OCR Agent | F | 4 |
| Supplier Comparison UI | E | 4 |
| Audit Log UI | E | 4 |
| Performance Testing | D | 4 |
| Demo Environment | D | 4–5 |
| Demo Script + Rehearsals | A (lead) | 5 |

---

# PART 6 — MVP Reduction Strategy

*Applied when time pressure forces scope reduction. Use in order: cut Level 3 features first, then Level 2, never Level 1.*

---

## Level 1 MVP — Absolute Minimum (Never Remove)

**These features must exist for the demo to be credible. Removing any of these makes the demo fail.**

**Module 1:**
- Conversational chat interface (web, English + Arabic language toggle)
- Language detection (AR/EN) with correct RTL response formatting
- Intent classification routing (query → ERP Query Agent, analytics → Analytics Supervisor, action → Action Agent)
- ERP Query Agent: customer queries, sales order queries, stock level queries
- ERP Action Agent: create sales quotation with Confirmation Gate
- Confirmation Gate (enforced at API layer — non-negotiable security signal)
- Analytics pipeline: all 4 sub-agents working, generates report with ≥3 KPIs and ≥2 charts
- Session context within session (10-turn window)
- Agent Reasoning Panel in UI (collapsible, shows agent steps)

**Module 2:**
- Inventory Monitor: risk state classification for all mock products
- Demand Forecast: projected stockout date for CRITICAL products
- RFQ Draft Generation: ≥3 draft RFQs visible in procurement dashboard
- Procurement Confirmation Gate: approve creates Odoo PO, reject discards and logs

**Infrastructure:**
- Odoo instance with mock data
- Docker Compose stack
- LangSmith traces visible
- Audit log capturing all write actions and cancellations

---

## Level 2 MVP — Demo Quality (Remove If Timeline Critical)

**These features make the demo significantly better but the system functions without them.**

- Supplier Evaluator Agent (full scoring model) — can simplify to: pick first available supplier from `product.supplierinfo`, skip scoring
- Supplier Comparison Panel (UI-09) — the RFQ can list the recommended supplier without a full comparison view
- Proactive alert push notifications — the dashboard can show alerts on page load without real-time push
- Combined RFQ suggestion (shared supplier) — generate separate RFQs instead
- Period-over-period comparison in analytics — show current period only
- Audit Log Viewer (UI-11) — the log exists in DB; removing the UI doesn't break the security model
- Arabic RTL full report formatting — Arabic response text in RTL is sufficient; full report layout can be deferred

**Reduction Logic:** If Sprint 3 is behind schedule, drop Supplier Evaluator to basic lookup, drop UI-09 entirely, and proceed. The core procurement pipeline still works and the demo still shows proactive RFQ generation.

---

## Level 3 MVP — Should Have Features (Cut First Under Time Pressure)

**These are Should Have features that enhance the demo but are not required for the core narrative.**

- OCR Supplier Quote Processing (Epic 8) — complex, fragile, high failure risk. Cut entirely if Sprint 4 is tight.
- Procurement Health Score (composite) — simplify to a count of CRITICAL + AT RISK items
- Slow-Moving Product Detection — cut entirely (Nice to Have per PRD)
- Expiry Risk Analysis — cut entirely (Prototype per PRD)
- Scenario Simulation — cut entirely (Nice to Have per PRD)
- Voice-to-text input — already removed from MVP (per PRD Section 20.2)
- Module 3 Customer Support — cut entirely until Modules 1 and 2 are demo-perfect

---

## Demo-Critical Features (Never Sacrifice for Scope)

These three moments define demo success (per PRD Section 20.5). Protect them above all else:

1. **The Arabic Business Review:** CEO asks for business review in Arabic → full KPI report in Arabic with charts in ≤30 seconds. This requires: Arabic NLP, Analytics pipeline (all 4 agents), KPI computation, chart rendering, Arabic insight generation.

2. **The Proactive Stockout Alert:** System detects a product will stockout in 3 days → draft RFQ visible, ready to approve with one click. This requires: Inventory Monitor, Demand Forecaster, RFQ Generator, Procurement Dashboard, Procurement Confirmation Gate.

3. **The Multi-Agent Trace:** Judge asks "how is this different from a chatbot?" → LangSmith trace shows 5 agents working in sequence. This requires: LangSmith connected and working, agent step events streaming to Agent Reasoning Panel in UI.

---

# PART 7 — Coding Agent Specifications

*These prompts are production-ready for use with Cursor, Claude Code, OpenAI Agents SDK, and Gemini CLI.*

---

## 7.1 Backend Agent Prompt

```
ROLE: Senior Python Backend Engineer — FastAPI + Async + AI Systems

You are working on AERIE (Agentic ERP Intelligence Engine), a multi-agent AI system 
built on top of Odoo ERP using FastAPI (Python) and LangGraph.

RESPONSIBILITIES:
- Build and maintain FastAPI endpoints in /backend/api/
- Implement async Python services in /backend/services/
- Implement Pydantic models for all request/response types in /backend/models/
- Implement JWT authentication, role-based authorization, and session management
- Implement the audit log system (INSERT-ONLY, all write operations logged)
- Implement the Confirmation Gate (token generation, validation, replay protection)
- Ensure all Odoo write operations go through the OdooClient, never directly

CODING STANDARDS:
- Python 3.11+. Type hints on all functions. No untyped code.
- Async/await throughout (FastAPI async endpoints, async OdooClient calls)
- Pydantic v2 for all data models. No dicts passed between services.
- FastAPI dependency injection for auth, DB sessions, Redis, OdooClient
- structlog for all logging: structured JSON, include request_id, session_id
- All endpoints return typed response models, never raw dicts
- HTTP errors: use FastAPI HTTPException with explicit status codes and detail messages
- All Odoo write operations: validate confirmation token before executing
- Test coverage ≥ 80% for all service classes and utility functions

ARCHITECTURAL CONSTRAINTS:
- Odoo credentials are NEVER exposed to the frontend — server-side only
- Confirmation tokens are single-use, session-scoped, 10-minute TTL — enforce in backend, not just frontend
- Audit log is INSERT-ONLY — no UPDATE or DELETE on the audit_log table
- User roles are enforced at the API layer using the require_role dependency
- All LLM calls go through the agent layer, never directly from API endpoints
- Redis keys must include session_id prefix to avoid cross-session collision
- Chroma and vector operations are only used for schema registry semantic search

FILES ALLOWED TO MODIFY:
- /backend/api/**/*.py
- /backend/services/**/*.py
- /backend/models/**/*.py
- /backend/core/config.py
- /backend/core/auth.py
- /backend/core/audit.py
- /backend/db/migrations/**
- /backend/tests/**

FILES FORBIDDEN TO MODIFY:
- /agents/ (agent logic belongs to AI engineers)
- /frontend/ (separate stream)
- /docker-compose.yml (infrastructure changes require team agreement)
- /backend/services/odoo_client.py (ERP Integration Engineer owns this)

DEFINITION OF DONE:
- Endpoint returns correct response on happy path
- Endpoint returns correct error response on all defined error paths
- All Odoo write paths require valid confirmation token
- All write actions produce an audit log entry with correct fields
- Unit tests cover the service, not just the endpoint
- No unhandled exceptions (all exceptions caught and converted to HTTPException or logged)
- Tested against locally running Docker Compose stack
```

---

## 7.2 Frontend Agent Prompt

```
ROLE: Senior React/Next.js Frontend Engineer — Enterprise UI + Arabic RTL

You are building the AERIE frontend — a professional, enterprise-grade web application 
using Next.js 14 (App Router), Tailwind CSS, and Recharts.

RESPONSIBILITIES:
- Build all screens defined in the PRD Section 17: UI-01 through UI-11
- Implement WebSocket client for streaming agent events and real-time UI updates
- Implement Arabic RTL layout system with language toggle (AR/EN)
- Implement all chart components using Recharts
- Implement all loading states, empty states, error states, and toast notifications
- Integrate with backend API endpoints defined in PRD Section 16

CODING STANDARDS:
- TypeScript throughout. No `any` types. Define interfaces for all API responses.
- Next.js App Router (not Pages Router). Server and client components where appropriate.
- Tailwind CSS only — no inline styles, no CSS modules except for RTL direction utilities
- Recharts for all charts: LineChart, BarChart, PieChart, RadarChart
- React hooks for all state management. No class components.
- WebSocket: implement reconnection logic and fallback to polling if WS fails
- RTL: use `dir="rtl"` on Arabic content containers; `text-right` and `flex-row-reverse` as needed; never hardcode text alignment
- Loading states: skeleton loaders for tables, spinners for agent processing
- Error states: every API call has a caught error path with user-facing message
- Toast notifications: bottom-right, 4-second auto-dismiss, success (green) / error (red)
- Font: IBM Plex Arabic for Arabic content, Inter for English

UI DESIGN CONSTRAINTS:
- Semantic color system: green=#16a34a (healthy/success), yellow=#ca8a04 (watch), orange=#ea580c (at-risk), red=#dc2626 (critical/error)
- 1280px desktop minimum. No mobile optimization in MVP.
- No blank screens during async operations — always show skeleton or spinner
- Agent Reasoning Panel: collapsible sidebar panel, shows real-time step list from WebSocket stream
- Confirmation Panel (UI-05): full-screen modal overlay. CANNOT be dismissed by clicking outside. Only Confirm or Cancel buttons close it.
- All AI-generated content must display the label "AI RECOMMENDATION — Human review required"

FILES ALLOWED TO MODIFY:
- /frontend/app/**
- /frontend/components/**
- /frontend/lib/**
- /frontend/hooks/**
- /frontend/types/**
- /frontend/public/**

FILES FORBIDDEN TO MODIFY:
- /backend/ (separate stream)
- /agents/ (separate stream)
- /docker-compose.yml
- /frontend/next.config.js (requires team discussion)

DEFINITION OF DONE:
- Component renders correctly with real API data and with mock data
- Loading state visible during all async operations
- Error state renders correct user message when API call fails
- Arabic RTL renders correctly when language is set to Arabic
- No TypeScript errors (tsc --noEmit passes)
- Tested in Chrome at 1280px width
- WebSocket streaming: agent steps appear in real-time during chat
- Empty states: all tables/lists have an empty state component (not just a blank table)
```

---

## 7.3 LangGraph Agent Prompt

```
ROLE: Staff AI Engineer — LangGraph Multi-Agent Systems

You are building and maintaining the multi-agent system for AERIE using LangGraph. 
You are responsible for the agent state machines, node implementations, tool definitions, 
and inter-agent communication patterns.

RESPONSIBILITIES:
- Design and implement the LangGraph CopilotGraph (Module 1)
- Design and implement the LangGraph ProcurementGraph (Module 2)
- Implement all agent nodes with well-defined input/output schemas
- Implement all tools used by agents (detect_language, classify_intent, resolve_entity, etc.)
- Ensure all agent nodes are decorated with @traceable for LangSmith observability
- Enforce tool call limits (max 10 tool calls per agent invocation)
- Implement graceful failure handling: agent failure returns error message, never crashes the system

CODING STANDARDS:
- Python 3.11+, full type hints
- LangGraph StateGraph for all agent orchestration — no custom state management
- All agent inputs and outputs defined as Pydantic models, not dicts
- GPT-4o for complex reasoning (Orchestrator, Action Agent, Analytics Insight)
- GPT-4o-mini for simple routing and classification to minimize cost
- KPI Computation Agent: CODE-ONLY, no LLM calls for number generation
- Supplier Scoring Agent: CODE-ONLY for scoring math, LLM only for rationale text
- Insight Generation Agent: prompt must constrain outputs to KPIReport data values only
- All @traceable decorators applied at the node level (not the tool level)
- Tool calls logged via structlog in addition to LangSmith
- Max context window management: 10-turn session window enforced in Orchestrator
- LangChain/LangGraph version pinned in requirements.txt

ARCHITECTURAL CONSTRAINTS:
- Each agent node receives a single typed state object and returns an updated state object
- Agent nodes do NOT call Odoo directly — they call services in /backend/services/
- The Confirmation Gate is enforced at the API layer; agents prepare confirmation payloads but do not execute writes
- Agent graph definitions live in /agents/graphs/; node implementations in /agents/nodes/; tools in /agents/tools/
- No agent imports from /frontend/
- Session context is the single source of truth for conversation history — agents do not maintain their own state between calls

FILES ALLOWED TO MODIFY:
- /agents/graphs/**
- /agents/nodes/**
- /agents/tools/**
- /agents/prompts/**
- /agents/schemas/**
- /agents/tests/**

FILES FORBIDDEN TO MODIFY:
- /backend/api/ (API layer is owned by Backend Engineer)
- /backend/services/odoo_client.py (OdooClient is owned by ERP Integration Engineer)
- /frontend/
- /docker-compose.yml

DEFINITION OF DONE:
- Agent node accepts typed input, returns typed output
- LangSmith trace shows agent node invocation with correct inputs/outputs
- Tool call count never exceeds 10 per agent invocation
- On tool failure: agent returns graceful error, does not retry more than once
- Unit test covers happy path and at least 2 failure modes
- Integration test: agent → service → Odoo works end-to-end on local stack
- No LLM calls produce numbers that are not verifiable from input data (for KPI and scoring agents)
```

---

## 7.4 Database Agent Prompt

```
ROLE: Senior Database Engineer — PostgreSQL + Redis + Schema Design

You are responsible for the application database schema, migrations, query optimization, 
and Redis data management for AERIE.

RESPONSIBILITIES:
- Design and implement all PostgreSQL table schemas in /database/migrations/
- Implement all database models (SQLAlchemy or raw psycopg2)
- Implement Redis key schema and TTL strategy for session context and confirmation tokens
- Ensure audit_log table is INSERT-ONLY (no UPDATE/DELETE operations ever)
- Write database seed scripts for test users and system configuration
- Optimize queries for analytics data retrieval (indexes, query plans)

CODING STANDARDS:
- PostgreSQL 15+. All tables have explicit primary keys.
- Migrations with Alembic. Never modify production data directly.
- UUID primary keys for audit_log, user table, session tokens
- Timestamps: always UTC, timestamptz type
- All JSON fields use JSONB (not JSON) for indexing capability
- Redis key naming convention: {entity_type}:{entity_id}:{field} (e.g., session:abc123:context)
- Redis TTL: session context = 3600s (60min), confirmation tokens = 600s (10min)
- No ORM queries that generate N+1 problems — review all relationship loads

ARCHITECTURAL CONSTRAINTS:
- Application DB (PostgreSQL) and Odoo DB are SEPARATE databases — never query Odoo DB directly
- audit_log table: add a PostgreSQL trigger to REJECT any UPDATE or DELETE on this table
- All database operations go through the service layer, never from agent nodes directly
- Confirmation token table OR Redis — choose one, not both. Redis preferred for TTL management.
- rfq_draft table stores draft RFQs before approval; deleted on approval or rejection

FILES ALLOWED TO MODIFY:
- /database/migrations/**
- /database/models/**
- /database/seeds/**
- /backend/core/database.py

FILES FORBIDDEN TO MODIFY:
- Odoo database directly
- /agents/
- /frontend/

DEFINITION OF DONE:
- Migration runs cleanly on fresh database
- Migration is reversible (down migration implemented)
- audit_log INSERT-ONLY constraint verified (trigger rejects DELETE/UPDATE with a test)
- All indexes documented in migration comments
- Redis key TTL verified in integration test
- No N+1 queries in service layer (verified with query log)
```

---

## 7.5 Odoo Integration Agent Prompt

```
ROLE: ERP Integration Engineer — Odoo JSON-RPC + Schema Registry

You are responsible for the OdooClient singleton, the Schema Registry, the Entity Resolver, 
and all safe patterns for ERP data access and modification.

RESPONSIBILITIES:
- Implement and maintain /backend/services/odoo_client.py
- Implement and maintain /backend/services/entity_resolver.py
- Implement and maintain /backend/services/domain_filter_builder.py
- Author and maintain /agents/schemas/schema_registry.yaml
- Write and maintain schema_validate.py
- Ensure all Odoo write paths enforce the confirmation gate requirement
- Log every Odoo API call with timing, model, method, domain, success/failure

CODING STANDARDS:
- OdooClient is a singleton — import the instance, do not instantiate a new one per request
- All Odoo calls are async (use asyncio.to_thread for blocking xmlrpc calls if needed)
- Rate limiter: token bucket algorithm, 10 calls/sec hard limit
- Retry: 1 retry on connection failure. Second failure raises OdooConnectionError (do not retry indefinitely)
- All write methods (create, write, execute_action) require confirmation_token as mandatory parameter
- Authentication: store uid and password server-side. NEVER return Odoo credentials to any caller.
- schema_registry.yaml format: {concept_name: {model: "odoo.model.name", fields: [list], filters: {}}}
- Entity resolver: fuzzy match on `name` field using Odoo `ilike` operator, return record ID + display name

ARCHITECTURAL CONSTRAINTS:
- OdooClient is the ONLY code in the system that communicates with the Odoo JSON-RPC endpoint
- Agent nodes call services, services call OdooClient — never agent → Odoo directly
- Schema registry is loaded once at startup, cached in memory, reloaded on SIGHUP
- domain_filter_builder.py must validate all input types before constructing domain (prevent injection)
- If Odoo returns an empty list, return an empty list. If Odoo returns an error, raise OdooAPIError with the error detail.

FILES ALLOWED TO MODIFY:
- /backend/services/odoo_client.py
- /backend/services/entity_resolver.py
- /backend/services/domain_filter_builder.py
- /backend/services/schema_registry.py
- /agents/schemas/schema_registry.yaml
- /scripts/schema_validate.py
- /backend/tests/test_odoo_client.py

FILES FORBIDDEN TO MODIFY:
- /frontend/
- /agents/graphs/ (agent state machines)
- /agents/nodes/ (agent business logic)
- /database/migrations/ (DB engineer owns)

DEFINITION OF DONE:
- OdooClient passes full integration test suite against live Odoo instance
- All write methods reject calls without valid confirmation_token
- Rate limiter verified: ≥11 calls/sec causes 429-equivalent delay
- Retry logic verified: simulated network failure triggers 1 retry, then raises OdooConnectionError
- schema_validate.py passes with zero errors on all schema_registry entries
- Every Odoo API call produces a structlog entry with: timestamp, model, method, domain, response_time_ms, success
- Entity resolver correctly resolves both English and Arabic names against mock data
```

---

## 7.6 Testing Agent Prompt

```
ROLE: QA Engineer / Test Automation Lead

You are responsible for the full test suite for AERIE: unit tests, integration tests, 
agent behavior tests, Odoo integration tests, and demo scenario validation.

RESPONSIBILITIES:
- Write unit tests for all service classes (OdooClient, AuditLogger, EntityResolver, KPIComputationAgent)
- Write integration tests for all API endpoints
- Write agent behavior tests: given input → verify output schema and content
- Build and maintain the Arabic NLP test set (30 queries with expected intents and languages)
- Build and maintain the analytics KPI ground truth reference (expected KPI values from mock data)
- Write demo scenario end-to-end tests that simulate all 5 demo scenarios
- Verify the Confirmation Gate cannot be bypassed by direct API calls

CODING STANDARDS:
- pytest for all tests. pytest-asyncio for async tests. httpx for API integration tests.
- Test naming: test_{component}_{scenario}_{expected_outcome}
- Tests must be runnable in the Docker Compose environment
- No test should modify the shared mock Odoo data permanently (use Odoo test database or rollback)
- Agent tests: inject mock OdooClient responses — do not hit real Odoo in unit tests
- KPI tests: hard-code expected values from demo_data_guide.md and verify computation matches

CRITICAL TEST AREAS:
1. Confirmation Gate bypass attempts: confirm that `POST /actions/{id}/confirm` with wrong session, expired token, or already-used token returns 401/403
2. KPI accuracy: all KPI values match manually computed values from mock dataset
3. Arabic NLP: ≥18/20 test queries correctly classified (intent + language)
4. Audit log completeness: every write action and cancellation produces a log entry
5. Agent failure graceful degradation: injected tool failures return user-friendly error, system does not crash

FILES ALLOWED TO MODIFY:
- /tests/**
- /backend/tests/**
- /agents/tests/**
- /frontend/tests/**
- /scripts/validate_demo.py

FILES FORBIDDEN TO MODIFY:
- Any production source files — tests only read/call them, never modify

DEFINITION OF DONE:
- All unit tests pass in CI (pytest --tb=short returns exit 0)
- Integration tests pass against locally running Docker Compose stack
- ≥18/20 Arabic NLP test queries pass
- All 5 demo scenario validation tests pass
- Confirmation Gate bypass tests all return 401/403 as expected
- KPI ground truth tests pass (all computed values match expected values)
- No test relies on test execution order (tests are independent)
```

---

## 7.7 Code Review Agent Prompt

```
ROLE: Staff Engineer — Code Reviewer + Architecture Guardian

You are reviewing code changes for AERIE. Your job is to ensure every pull request 
meets the quality standards, does not violate architectural constraints, and does not 
introduce security vulnerabilities.

RESPONSIBILITIES:
- Review all PRs for correctness, security, performance, and style
- Block any PR that violates architectural constraints
- Ensure no Odoo write path bypasses the Confirmation Gate
- Ensure no LLM call is used where code-only computation is required (KPI, scoring)
- Ensure no agent node directly imports from frontend or database migration code

REVIEW CHECKLIST:
Security:
- [ ] No Odoo credentials in any response or log
- [ ] Confirmation gate enforced: all OdooClient write methods called with confirmation_token
- [ ] No user input directly concatenated into LLM system prompt (injection risk)
- [ ] JWT stored in httpOnly cookie, not localStorage

Correctness:
- [ ] KPI computation agent uses no LLM calls for number generation
- [ ] Supplier scoring uses no LLM calls for scoring math
- [ ] Insight generation agent prompt includes grounding constraint
- [ ] Agent failure returns graceful error message, not unhandled exception

Architecture:
- [ ] Agent nodes do not import from /backend/api/ or /frontend/
- [ ] OdooClient is imported as singleton, not re-instantiated
- [ ] All new API endpoints use require_role dependency
- [ ] New Pydantic models defined in /backend/models/, not inline in endpoint files

Quality:
- [ ] Type hints present on all new functions
- [ ] structlog used (not print() or logging.info())
- [ ] Tests added for new service methods
- [ ] LangSmith @traceable on all new agent nodes
- [ ] No TODO comments in merged code (convert to GitHub issues)

BLOCKING CRITERIA (PR cannot merge with these present):
- Any Odoo write without confirmation_token validation
- Unhandled exception that could crash the agent loop
- Hardcoded credentials or API keys in source code
- LLM generating KPI numbers without code-side computation
- Any modification to the audit_log table's schema that adds update/delete capability

DEFINITION OF DONE FOR REVIEWS:
- All checklist items verified
- At least 1 inline comment explaining the most important architectural decision in the PR
- Approval given within 4 hours of PR submission during active sprint
```

---

# PART 8 — Repository Structure

```
aerie/
│
├── README.md                          # Project overview, setup, architecture diagram
├── DEMO_SCRIPT.md                     # Step-by-step demo script, fallbacks, talking points
├── DEMO_SETUP.md                      # Environment setup guide for demo day
├── docker-compose.yml                 # Full stack: Odoo, PostgreSQL×2, Redis, FastAPI, Next.js, Chroma
├── .env.example                       # All required environment variables documented
├── .gitignore
│
├── backend/                           # FastAPI Python backend
│   ├── main.py                        # FastAPI app entry point, middleware, router registration
│   ├── requirements.txt
│   ├── Dockerfile
│   │
│   ├── api/                           # API route definitions
│   │   ├── auth.py                    # POST /auth/login, /refresh, /logout
│   │   ├── copilot.py                 # POST /api/v1/copilot/chat, WebSocket, session endpoints
│   │   ├── actions.py                 # POST /api/v1/copilot/actions/{id}/confirm|reject
│   │   ├── reports.py                 # GET /api/v1/copilot/reports/{report_id}
│   │   ├── procurement.py             # All /api/v1/procurement/* endpoints
│   │   └── admin.py                   # GET /api/v1/admin/audit-log
│   │
│   ├── models/                        # Pydantic request/response models
│   │   ├── auth.py                    # LoginRequest, TokenResponse, UserProfile
│   │   ├── chat.py                    # ChatRequest, ChatResponse, AgentStepEvent
│   │   ├── analytics.py               # KPIReport, ChartConfig, AnalyticsReport
│   │   ├── action.py                  # ConfirmationSummary, ActionResult
│   │   ├── procurement.py             # ProductRisk, DemandForecast, SupplierScore, RFQDraft
│   │   ├── ocr.py                     # QuoteExtraction, ExtractedField
│   │   └── audit.py                   # AuditLogEntry
│   │
│   ├── services/                      # Business logic services
│   │   ├── odoo_client.py             # OdooClient singleton (authenticate, search_read, create, write)
│   │   ├── entity_resolver.py         # resolve_entity(name, model_type) → record ID
│   │   ├── domain_filter_builder.py   # build_domain_filter(entities, time_range) → Odoo domain
│   │   ├── schema_registry.py         # Schema registry loader and lookup service
│   │   ├── session_service.py         # Redis session context management
│   │   ├── audit_service.py           # AuditLogger INSERT-ONLY service
│   │   ├── confirmation_service.py    # Token generation, validation, replay protection
│   │   ├── report_service.py          # Analytics report storage and retrieval
│   │   ├── procurement_service.py     # RFQ draft CRUD, procurement state management
│   │   └── ocr_service.py             # PDF upload handling, OCR result storage
│   │
│   ├── core/                          # Cross-cutting infrastructure
│   │   ├── config.py                  # Settings (pydantic-settings, reads from .env)
│   │   ├── auth.py                    # JWT issuing, validation, require_role dependency
│   │   ├── database.py                # SQLAlchemy async engine, session factory
│   │   ├── redis_client.py            # Redis connection pool
│   │   └── logging.py                 # structlog configuration
│   │
│   └── tests/
│       ├── test_auth.py
│       ├── test_odoo_client.py
│       ├── test_entity_resolver.py
│       ├── test_confirmation_gate.py
│       ├── test_audit_log.py
│       ├── test_kpi_computation.py
│       ├── test_demand_forecaster.py
│       └── test_supplier_scorer.py
│
├── agents/                            # LangGraph agent system
│   ├── requirements.txt
│   │
│   ├── graphs/                        # LangGraph state machine definitions
│   │   ├── copilot_graph.py           # CopilotGraph: Orchestrator → Query/Action/Analytics
│   │   └── procurement_graph.py       # ProcurementGraph: Monitor → Forecast → Evaluate → Generate
│   │
│   ├── nodes/                         # Agent node implementations
│   │   ├── orchestrator_node.py       # AGENT-1-01: Copilot Orchestrator
│   │   ├── erp_query_node.py          # AGENT-1-02: ERP Query Agent
│   │   ├── erp_action_node.py         # AGENT-1-03: ERP Action Agent
│   │   ├── analytics_supervisor_node.py # AGENT-1-04: Analytics Supervisor
│   │   ├── data_retrieval_node.py     # AGENT-1-05: Data Retrieval Agent
│   │   ├── kpi_computation_node.py    # AGENT-1-06: KPI Computation (code-only)
│   │   ├── visualization_node.py      # AGENT-1-07: Visualization Agent
│   │   ├── insight_generation_node.py # AGENT-1-08: Insight Generation Agent
│   │   ├── procurement_orchestrator_node.py # AGENT-2-01
│   │   ├── inventory_monitor_node.py  # AGENT-2-02: Inventory Monitor
│   │   ├── demand_forecaster_node.py  # AGENT-2-03: Demand Forecaster
│   │   ├── supplier_evaluator_node.py # AGENT-2-04: Supplier Evaluator
│   │   ├── rfq_generator_node.py      # AGENT-2-05: RFQ Generator
│   │   └── ocr_agent_node.py          # AGENT-2-06: OCR Agent
│   │
│   ├── tools/                         # Tool implementations used by agent nodes
│   │   ├── language_tools.py          # detect_language, classify_intent
│   │   ├── odoo_tools.py              # odoo_search_read, build_domain_filter, resolve_entity
│   │   ├── formatting_tools.py        # format_data_response (EN/AR, table/list/summary)
│   │   ├── analytics_tools.py         # compute_kpis, generate_chart_config
│   │   ├── procurement_tools.py       # compute_risk_state, forecast_demand, score_supplier
│   │   └── ocr_tools.py               # extract_quote_pdf, score_confidence
│   │
│   ├── schemas/                       # Typed agent state and IO schemas
│   │   ├── copilot_state.py           # CopilotState, IntentClassification, EntitySet
│   │   ├── analytics_state.py         # AnalyticsState, KPIReport, ChartConfig
│   │   ├── procurement_state.py       # ProcurementState, ProductRisk, DemandForecast, RFQDraft
│   │   ├── supplier_schema.py         # SupplierScore, SupplierRanking
│   │   └── schema_registry.yaml       # NLP concept → Odoo model/field mapping
│   │
│   ├── prompts/                       # Prompt templates (versioned, NOT hardcoded in nodes)
│   │   ├── orchestrator_system.md
│   │   ├── erp_query_system.md
│   │   ├── erp_action_system.md
│   │   ├── analytics_supervisor_system.md
│   │   ├── insight_generation_system.md
│   │   ├── procurement_rationale_system.md
│   │   └── ocr_extraction_system.md
│   │
│   └── tests/
│       ├── test_copilot_graph.py
│       ├── test_orchestrator_node.py
│       ├── test_erp_query_node.py
│       ├── test_analytics_pipeline.py
│       ├── test_confirmation_gate.py
│       ├── test_procurement_graph.py
│       ├── test_inventory_monitor.py
│       ├── test_demand_forecaster.py
│       ├── test_supplier_evaluator.py
│       └── nlp_test_set/
│           ├── arabic_queries.json    # 30 Arabic test queries with expected intent + language
│           └── english_queries.json   # 30 English test queries
│
├── frontend/                          # Next.js React frontend
│   ├── package.json
│   ├── Dockerfile
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   │
│   ├── app/                           # Next.js App Router pages
│   │   ├── layout.tsx                 # Root layout, font loading, global styles
│   │   ├── page.tsx                   # Root redirect to /login or /dashboard
│   │   ├── login/
│   │   │   └── page.tsx               # UI-01: Login page
│   │   ├── dashboard/
│   │   │   └── page.tsx               # UI-02: Main dashboard
│   │   ├── copilot/
│   │   │   └── page.tsx               # UI-03: Copilot chat + UI-04 Analytics report
│   │   ├── procurement/
│   │   │   ├── page.tsx               # UI-06: Procurement dashboard
│   │   │   ├── products/
│   │   │   │   └── page.tsx           # UI-07: Product risk list
│   │   │   ├── rfq/
│   │   │   │   └── page.tsx           # UI-08: RFQ review panel
│   │   │   ├── suppliers/
│   │   │   │   └── page.tsx           # UI-09: Supplier comparison panel
│   │   │   └── quotes/
│   │   │       └── page.tsx           # UI-10: Quote upload and review
│   │   └── admin/
│   │       └── audit/
│   │           └── page.tsx           # UI-11: Audit log viewer
│   │
│   ├── components/
│   │   ├── ui/                        # Shared design system components
│   │   │   ├── Badge.tsx              # Risk state badge (CRITICAL/AT RISK/WATCH/HEALTHY)
│   │   │   ├── Card.tsx
│   │   │   ├── LoadingSkeleton.tsx
│   │   │   ├── EmptyState.tsx
│   │   │   ├── Toast.tsx              # Toast notification system
│   │   │   ├── Modal.tsx              # Base modal (non-dismissable variant for Confirmation)
│   │   │   └── RTLWrapper.tsx         # Direction-aware layout wrapper
│   │   │
│   │   ├── chat/
│   │   │   ├── ChatInterface.tsx      # Main chat layout
│   │   │   ├── MessageList.tsx        # Scrollable message history
│   │   │   ├── MessageBubble.tsx      # Individual message (user / assistant)
│   │   │   ├── ChatInput.tsx          # Text input + submit
│   │   │   ├── AgentReasoningPanel.tsx # Collapsible step-by-step reasoning panel
│   │   │   └── LanguageToggle.tsx     # AR / EN toggle
│   │   │
│   │   ├── analytics/
│   │   │   ├── AnalyticsReport.tsx    # Full report layout
│   │   │   ├── KPIGrid.tsx            # KPI metric grid with delta badges
│   │   │   ├── RevenueBarChart.tsx    # Recharts bar chart
│   │   │   ├── TrendLineChart.tsx     # Recharts line chart
│   │   │   ├── CustomerPieChart.tsx   # Recharts pie chart
│   │   │   ├── ProductTable.tsx       # Top products table
│   │   │   └── InsightCard.tsx        # Narrative insight with data reference
│   │   │
│   │   ├── confirmation/
│   │   │   └── ConfirmationPanel.tsx  # Action confirmation modal
│   │   │
│   │   ├── procurement/
│   │   │   ├── ProcurementDashboard.tsx
│   │   │   ├── HealthScoreGauge.tsx
│   │   │   ├── AlertPanel.tsx
│   │   │   ├── ProductRiskTable.tsx
│   │   │   ├── RFQDraftCard.tsx
│   │   │   ├── SupplierScoreBadge.tsx
│   │   │   ├── AIRationaleNote.tsx
│   │   │   ├── ApprovalBar.tsx
│   │   │   ├── SupplierComparisonTable.tsx
│   │   │   ├── SupplierRadarChart.tsx
│   │   │   ├── QuoteUpload.tsx
│   │   │   └── QuoteReviewTable.tsx
│   │   │
│   │   └── layout/
│   │       ├── Sidebar.tsx
│   │       ├── Header.tsx
│   │       └── Navigation.tsx
│   │
│   ├── hooks/
│   │   ├── useWebSocket.ts            # WebSocket client with reconnection
│   │   ├── useChat.ts                 # Chat state management
│   │   ├── useProcurement.ts          # Procurement data fetching
│   │   └── useAuth.ts                 # Auth state, token refresh
│   │
│   ├── lib/
│   │   ├── api.ts                     # Typed API client (fetch wrapper)
│   │   └── rtl.ts                     # RTL direction utilities
│   │
│   └── types/
│       ├── chat.ts
│       ├── analytics.ts
│       ├── procurement.ts
│       └── auth.ts
│
├── database/
│   ├── migrations/                    # Alembic migrations
│   │   ├── 001_create_users.py
│   │   ├── 002_create_audit_log.py
│   │   ├── 003_create_sessions.py
│   │   ├── 004_create_rfq_drafts.py
│   │   ├── 005_create_product_risk_cache.py
│   │   ├── 006_create_reports.py
│   │   └── 007_create_ocr_quotes.py
│   └── seeds/
│       └── seed_users.py              # 5 test users (one per role)
│
├── scripts/
│   ├── seed_mock_data.py              # Generates and loads all Odoo mock data
│   ├── schema_validate.py             # Validates schema_registry.yaml against live Odoo
│   └── validate_demo.py              # End-to-end demo scenario validation script
│
└── tests/
    ├── e2e/                           # End-to-end demo scenario tests
    │   ├── test_scenario_1_ceo_brief.py
    │   ├── test_scenario_2_arabic_query.py
    │   ├── test_scenario_3_action_confirmation.py
    │   ├── test_scenario_4_procurement_alert.py
    │   └── test_scenario_5_supplier_comparison.py
    └── nlp/
        └── test_arabic_accuracy.py    # 30-query Arabic NLP validation
```

---

# PART 9 — Testing Strategy

---

## 9.1 Unit Testing Plan

**Framework:** pytest + pytest-asyncio

**Scope and Targets:**

**OdooClient (`test_odoo_client.py`)**
- Test `authenticate()` returns valid UID
- Test `search_read()` returns correct records for known domain filters
- Test `search_read()` pagination (offset parameter)
- Test rate limiter: >10 calls/sec triggers delay
- Test retry logic: simulated connection failure triggers exactly 1 retry, then raises OdooConnectionError
- Test write methods reject calls without confirmation_token
- Test all calls produce structlog entries

**Entity Resolver (`test_entity_resolver.py`)**
- Test English name resolution to correct Odoo record ID
- Test Arabic name resolution to correct Odoo record ID
- Test partial name matching (fuzzy)
- Test resolution failure returns None (not exception)

**KPI Computation Agent (`test_kpi_computation.py`)**
- For each KPI: verify computed value matches manually calculated value from `demo_data_guide.md`
- Test period-over-period delta calculation (positive, negative, zero cases)
- Test empty data handling (no orders in period → zero revenue, not error)

**Demand Forecaster (`test_demand_forecaster.py`)**
- Test SMA computation on known input data → expected output
- Test confidence level assignment (HIGH/MEDIUM/LOW thresholds)
- Test MOQ enforcement: recommended quantity rounds up to MOQ
- Test sparse data handling: <30 days → LOW confidence, includes warning text

**Supplier Scorer (`test_supplier_scorer.py`)**
- Test scoring math for each criterion (price consistency, on-time delivery, fulfillment, lead time)
- Test composite score computation
- Test "New Supplier — Limited Data" flag triggers for suppliers with <2 POs
- Test per-product ranking: different rankings for different products

**Audit Logger (`test_audit_log.py`)**
- Test INSERT creates a record with all required fields
- Test UPDATE on audit_log raises an exception (INSERT-ONLY enforcement)
- Test DELETE on audit_log raises an exception
- Test audit log contains entries for: approved action, rejected action, cancelled action

**Confirmation Gate (`test_confirmation_gate.py`)**
- Test token generation creates a unique, session-scoped token
- Test token validation succeeds for valid, unexpired, unused token
- Test token validation fails for expired token (>10 min)
- Test token validation fails for wrong session
- Test replay protection: second use of same token returns 403

---

## 9.2 Integration Testing Plan

**Framework:** pytest + httpx (async HTTP client)

**Scope:** All API endpoints tested against a live Docker Compose stack

**Authentication Integration Tests:**
- `POST /auth/login` with valid credentials → 200, JWT cookie set
- `POST /auth/login` with invalid credentials → 401
- `GET /api/v1/copilot/chat` without token → 401
- `GET /api/v1/copilot/chat` with role that lacks permission → 403
- `POST /auth/refresh` with valid refresh token → 200, new access token

**Copilot API Integration Tests:**
- `POST /copilot/session` → session_id returned, Redis key created
- `POST /copilot/chat` with ERP query → response contains formatted data
- `POST /copilot/chat` in Arabic → response language is Arabic, RTL indicated
- `POST /copilot/chat` with analytics intent → response contains KPIs and charts
- `POST /copilot/chat` with write intent → response contains pending_action, no Odoo write yet
- `POST /copilot/actions/{id}/confirm` → Odoo record created, audit log entry written
- `POST /copilot/actions/{id}/reject` → no Odoo record, audit log entry with cancelled_by_user
- `POST /copilot/actions/{id}/confirm` with wrong session → 403
- `POST /copilot/actions/{id}/confirm` twice → second call returns 403 (replay protection)

**Procurement API Integration Tests:**
- `POST /procurement/monitoring/run` → triggers full scan, returns risk states for all products
- `GET /procurement/alerts` → returns current alerts
- `GET /procurement/products` → all products with risk states
- `GET /procurement/products/{id}/forecast` → forecast with stockout date and confidence
- `GET /procurement/suppliers/{product_id}/ranking` → ranked suppliers with scores
- `GET /procurement/rfq/drafts` → draft RFQs pending approval
- `POST /procurement/rfq/drafts/{id}/approve` → Odoo purchase.order created, audit log entry
- `POST /procurement/rfq/drafts/{id}/reject` → draft deleted, audit log entry

---

## 9.3 Agent Testing Plan

**Approach:** Agent node tests inject mock services (MockOdooClient, MockRedis) to test agent logic in isolation.

**Copilot Orchestrator Tests:**
- Arabic text input → language detected as "ar"
- English text input → language detected as "en"
- Query intent → routed to ERP Query node
- Analytics intent → routed to Analytics Supervisor node
- Write intent → routed to ERP Action node
- Low confidence (<0.70) → clarification request returned, no routing

**ERP Query Agent Tests:**
- "Show top 5 customers" → returns formatted customer table with correct data
- "Current stock of [product]" → returns correct quantity from mock OdooClient
- Non-existent entity → "No record found for [name]" message (not error)
- Empty result set → "No records found matching your criteria" message

**Analytics Pipeline Tests:**
- Analytics intent → LangSmith trace shows ≥4 agent invocations
- KPI output contains all required fields: revenue, delta, top_customers, order_count
- Chart config output is valid Recharts-compatible JSON for all 4 chart types
- Insight output: verify each insight references a value present in KPIReport
- End-to-end time: <30 seconds (timed integration test)

**ERP Action Agent Tests:**
- Write intent with all fields → Confirmation Summary displayed, no Odoo write
- Write intent with missing field → clarification question returned
- Non-existent entity in write intent → error before Confirmation Summary, no Odoo write

**Procurement Agent Tests:**
- Inventory monitor: CRITICAL products correctly identified from mock data
- Demand forecaster: stockout date within ±3 days of manually computed date
- Supplier evaluator: supplier with high on-time delivery scores higher than supplier with low on-time delivery
- RFQ generator: shared-supplier products generate combined RFQ option

---

## 9.4 Odoo Integration Testing

**Environment:** Tests run against the mock-data-seeded Odoo instance in Docker Compose

**Schema Validation:**
- `python schema_validate.py` passes with zero errors
- All Odoo models referenced in schema_registry.yaml exist in running Odoo instance
- All fields listed in schema_registry.yaml exist on their respective models

**Data Integrity Tests:**
- All 50 products have stock quantities in `stock.quant`
- All 50 products have reorder rules in `stock.warehouse.orderpoint`
- All purchase order lines link to valid products and valid suppliers
- All sales order lines link to valid products and valid customers
- The 10 CRITICAL products have stock ≤ (lead_time × avg_daily_consumption) [verified against formula]

**Write Operation Tests:**
- `OdooClient.create('purchase.order', {...})` with valid confirmation_token → creates record in Odoo
- `OdooClient.create('sale.order', {...})` with valid confirmation_token → creates record in Odoo
- `OdooClient.create('purchase.order', {...})` without confirmation_token → raises ConfirmationRequiredError
- Created records appear in Odoo UI (manual verification)

---

## 9.5 End-to-End Demo Testing

*Each scenario tested against the full Docker Compose stack with LangSmith observability enabled.*

**Demo Scenario 1 — "The Monday Morning CEO Briefing" (Arabic)**
- Trigger: Arabic query "أعطني مراجعة أعمال الشهر الماضي"
- Assertions: Response language is Arabic, RTL layout active, ≥3 KPIs present, ≥2 charts rendered, ≥3 insights in Arabic, total time ≤30s, LangSmith shows ≥4 agent invocations

**Demo Scenario 2 — "The Sales Query" (English)**
- Trigger: "Who are our top customers this quarter?"
- Assertions: Correct customer list from Odoo mock data, formatted table, response time ≤5s, entity matches Odoo records exactly

**Demo Scenario 3 — "The Write Action + Confirmation" (English)**
- Trigger: "Create a quotation for [Customer from mock data]"
- Assertions: Confirmation Panel displayed before any Odoo write, cancellation produces audit log entry, confirmation creates sale.order in Odoo with correct customer, audit log contains "success" entry with record ID

**Demo Scenario 4 — "The Proactive Procurement Alert" (English)**
- Trigger: Manual monitoring cycle trigger
- Assertions: CRITICAL products identified, demand forecast with stockout date displayed, ≥3 RFQ drafts in procurement dashboard, approving one creates purchase.order in Odoo in RFQ state, audit log entry written

**Demo Scenario 5 — "Supplier Comparison" (English)**
- Trigger: Open supplier comparison for a CRITICAL product
- Assertions: ≥2 suppliers shown with scores, radar chart renders, supplier with high on-time delivery ranked #1, AI rationale explains scoring, user can override recommended supplier

**Demo Quality Gates (`validate_demo.py`):**
```python
# All 8 quality gates run automatically
assert arabic_nlp_accuracy >= 0.90           # ≥18/20 test queries
assert analytics_latency <= 30               # seconds
assert simple_query_latency <= 5             # seconds
assert confirmation_gate_enforced == True    # write without token → error
assert audit_log_entries_complete == True    # all demo actions logged
assert rfq_drafts_visible >= 3              # before demo starts
assert kpi_values_match_ground_truth == True # from demo_data_guide.md
assert docker_clean_start == True            # fresh machine test
```

---

# PART 10 — Final Delivery Plan

---

## 10.1 Critical Path

The following sequence is the critical path. Any slip on these items delays demo day. Every other task can slip without affecting the critical path as long as it is completed before its first dependent task.

```
Week 1 (Sprint 0):
  → Docker Compose + Odoo running [D]
  → Mock data seeded [D]
  → OdooClient foundation [B]
  → Schema Registry validated [B]

Week 2–3 (Sprint 1):
  → Authentication + Session (prerequisite for all protected endpoints) [B]
  → Copilot Orchestrator: language detection + intent classifier [A+F]
  → ERP Query Agent: entity resolution + Odoo read [B]
  → Basic chat UI [E]

Week 4–5 (Sprint 2):
  → Analytics Pipeline (all 4 sub-agents) [A+F] ← HIGHEST PRIORITY SPRINT 2
  → ERP Action Agent + Confirmation Gate [B]
  → Streaming UI + Agent Reasoning Panel [E]

Week 6–7 (Sprint 3):
  → Inventory Monitor [D]
  → Demand Forecaster [C]
  → Supplier Evaluator [C]
  → RFQ Generator + Procurement Confirmation Gate [C+B]
  → Procurement Dashboard UI [E]

Week 8 (Sprint 4):
  → OCR Agent [F]
  → Remaining UI (Supplier Comparison, Audit Log) [E]
  → Demo dry-run #1

Week 9 (Sprint 5):
  → All quality gate verifications
  → Demo rehearsals ×3
  → Docker snapshot
  → Final bug fixes
```

---

## 10.2 Biggest Risks (Ranked by Threat Level)

**Risk 1 — Analytics pipeline latency (CRITICAL)**
The analytics report has a 30-second target. With 4 sequential LLM calls + multiple Odoo reads, this is genuinely tight. Mitigation: parallelize Odoo reads in the Data Retrieval Agent using `asyncio.gather`. Use GPT-4o-mini for the Insight Generation Agent (it generates text, not complex reasoning). Cache the raw data payload in Redis for 5 minutes to avoid repeated Odoo reads.

**Risk 2 — Arabic NLP accuracy on business domain vocabulary (HIGH)**
GPT-4o is strong on Arabic, but domain-specific business language (ERP terminology, MENA product names) requires prompt iteration. Mitigation: Engineer F must build the 30-query test set by the end of Sprint 0 and run it against the intent classifier every time the system prompt changes. Target 80% on first pass, iterate to ≥90% by Sprint 2 end.

**Risk 3 — Mock data relationships broken at demo (HIGH)**
Orphaned foreign keys crash agent queries silently. Mitigation: `seed_mock_data.py` must validate all relationships before completing. Run `schema_validate.py` every time Odoo is reseeded. `demo_data_guide.md` documents every key relationship used in demo scenarios so they can be manually verified in Odoo UI before demo day.

**Risk 4 — Confirmation Gate edge cases failing under demo conditions (HIGH)**
If the gate can be bypassed or throws an unexpected error during demo, it is catastrophic — both as a security failure and as a demo failure. Mitigation: Confirmation Gate tests must cover all bypass paths (wrong session, expired token, replay). Gate must be tested against all 5 demo scenarios specifically.

**Risk 5 — Procurement module underestimated (MEDIUM)**
The procurement pipeline (Monitor → Forecast → Evaluate → Generate → Gate) is the longest agent chain in the system. If Sprint 3 overruns, OCR (Sprint 4) cannot be delivered. Mitigation: Supplier Evaluator can be simplified to basic lookup (no scoring model) and still produce a working RFQ pipeline. Define this simplification threshold before Sprint 3 starts so the team knows when to apply it.

**Risk 6 — WebSocket streaming instability (MEDIUM)**
Network issues, proxy configurations, or browser incompatibilities can cause WebSocket failures that make the Agent Reasoning Panel appear blank during demo. Mitigation: Build the REST polling fallback in Sprint 2 before polishing the WebSocket. Verify WebSocket works on the actual demo machine ≥24 hours before demo day.

**Risk 7 — LLM API cost overrun during development (LOW)**
Unguarded development queries at GPT-4o rates accumulate quickly. Mitigation: Set a monthly spend cap on the development API key. Route all non-critical classification tasks through GPT-4o-mini. Never stream raw Odoo database dumps to the LLM.

---

## 10.3 Recommended Build Order

**Priority 1 (Sprint 0 — Week 1):** Foundation only. No AI code. Odoo up, data seeded, schema validated, OdooClient working. This is the single most important week. If Sprint 0 slips into Sprint 1, every subsequent sprint is at risk.

**Priority 2 (Sprint 1 — Weeks 2–3):** End-to-end pipeline for a single query type. The moment "Show me our top customers" returns correct data from real Odoo through LangGraph → chat UI is the first working demo. This proves the architecture. Everything else builds on this moment.

**Priority 3 (Sprint 2 — Weeks 4–5):** Analytics pipeline first. This is harder and more impressive than the action agent. Build the KPI computation agent (code-only, no hallucination risk) before the insight generation agent. Confirm Recharts renders correctly in the frontend before connecting real data. Build the Confirmation Gate in parallel (Engineer B) — it is needed for the demo but is architecturally simpler than the analytics pipeline.

**Priority 4 (Sprint 3 — Weeks 6–7):** Procurement core. The Inventory Monitor must be validated against mock data before the Forecaster is built — the Monitor's output is the Forecaster's input. Supplier Evaluator can run in parallel with Forecaster (they share the same Odoo data but have independent logic).

**Priority 5 (Sprint 4 — Week 8):** Polish and OCR. OCR is the most failure-prone feature — restrict it to a single controlled PDF template in demo. If OCR is not ready by Day 2 of Sprint 4, cut it and document as future work. Use the time for demo rehearsal instead.

**Priority 6 (Sprint 5 — Week 9):** Hardening only. No new features. Every hour of this sprint is worth more as rehearsal time than as feature development.

---

## 10.4 Recommended MVP Scope

*The following scope, if delivered at high quality, wins the demo.*

**Deliver these at full quality:**

1. Bilingual chat interface (AR + EN) with correct RTL
2. ERP Query Agent: customer, order, stock, invoice queries in both languages
3. Analytics pipeline (4 agents): KPIs + charts + insights in ≤30 seconds
4. ERP Action Agent: sales quotation creation with Confirmation Gate
5. Inventory Monitor: CRITICAL/AT RISK classification for all products
6. Demand Forecaster: stockout date + confidence for at-risk products
7. Supplier Evaluator: per-product ranking (even basic version)
8. RFQ Generator: draft RFQs in procurement dashboard, approval creates Odoo record
9. Agent Reasoning Panel in UI: live steps visible during agent execution
10. LangSmith traces: all multi-agent workflows visible

**Deliver these at good quality (not perfect):**

11. Supplier Comparison Panel (UI-09) — side-by-side table + radar chart
12. Audit Log Viewer (UI-11)
13. Proactive alert notifications

**Deliver if capacity allows:**

14. OCR Quote Processing — controlled PDF only
15. Combined RFQ suggestion (shared supplier)
16. Procurement Health Score (composite)

**Do not deliver in MVP:**

- Module 3 Customer Support
- Voice-to-text
- Scenario simulation
- Cross-session memory
- Slow-moving product detection
- Expiry risk analysis

---

## 10.5 Recommended Demo Scope

*Five scenarios, scripted, rehearsed ≥3 times, with fallback plans.*

**Scenario 1 — Arabic CEO Briefing (3 minutes)**
Query: Arabic text → "أعطني مراجعة أعمال الشهر الماضي" (Give me a business review for last month)
Payoff: Full report in Arabic with charts in ≤30 seconds. Agent Reasoning Panel shows 4 agents.
Business narrative: "This took our operations manager half a day. It now takes 20 seconds."
Technical narrative: "Four specialized agents — data retrieval, computation, visualization, and insight generation — collaborated to produce this."

**Scenario 2 — Sales Query + Context Retention (1 minute)**
Query 1 (English): "Who are our top 3 customers this quarter?"
Query 2: "What is their total outstanding invoice balance?"
Payoff: Second query uses session context ("their" resolves correctly).
Business narrative: "No menus. No training. Any employee can get this information instantly."

**Scenario 3 — Write Action with Confirmation Gate (1 minute)**
Query: "Create a quotation for [Customer] for 10 units of [Product]"
Payoff: Confirmation Panel appears. "This will create a record in Odoo." User clicks Confirm. Record ID appears. Audit log captures it.
Business narrative: "AI acts — but humans decide. The gate is always enforced."
Technical narrative: "The confirmation token is validated at the API layer. The UI cannot bypass this."

**Scenario 4 — Proactive Procurement Alert (2 minutes)**
Start: Trigger monitoring cycle. Dashboard shows 3 CRITICAL products.
Show: Forecast for top CRITICAL product — "Stockout in 3 days. Confidence: HIGH."
Show: Draft RFQs ready for approval. Supplier ranked by score, rationale displayed.
Click: Approve one RFQ → Odoo purchase.order created, audit log entry shown.
Business narrative: "The system found the problem, did the analysis, and had the solution waiting. The manager spent 2 minutes, not 2 hours."

**Scenario 5 — Supplier Comparison (1 minute)**
Show: Supplier comparison panel for a CRITICAL product.
Highlight: Radar chart. One supplier with high on-time delivery vs. one with poor history.
Highlight: AI rationale text references the historical PO data.
Business narrative: "Supplier selection stops being a gut call. It becomes a data-driven decision."

**Total demo time:** ~8 minutes + Q&A

**Opening (1 minute before demo):** Show architecture diagram. State: "This is not a chatbot. It is a multi-agent AI workforce. Let me show you what that means in practice."

**Fallback plans:**
- If LangSmith is down: the demo still runs. Skip the "show the trace" narrative. Focus on the user experience.
- If WebSocket fails: the polling fallback kicks in. Agent Reasoning Panel may not be real-time. Acknowledge and continue.
- If a specific scenario fails: skip to the next. Never retry a failed scenario on stage — move on confidently.
- If Odoo is unreachable: have a recorded video backup of the 5 scenarios.

---

## Final Principal Engineering Manager Statement

This delivery plan is built to produce three things above all else:

**The three demo moments that define success:**

1. A CEO types a request in Arabic and receives a complete, accurate business review with charts in 20 seconds.
2. The system says: "Product X will stockout in 3 days. Here is the draft RFQ, ready for your approval."
3. A judge asks "how is this different from a chatbot?" and the LangSmith trace shows five specialized agents working in sequence.

Every task in this plan is in service of those three moments. Every cut in the MVP reduction strategy is designed to protect them.

The architecture is sound. The scope is calibrated. The risk register is honest. The team is structured for parallel delivery.

**The only variable now is execution discipline:**
- Do not add features after Week 3.
- Do not skip the Arabic NLP test set.
- Do not skip the Confirmation Gate bypass tests.
- Do not skip the demo dry-run.
- Do not demo on a machine you have not tested.

Ship the features defined here, ship them well, and the demo will speak for itself.

---

*End of AERIE Engineering Delivery Plan — Version 1.0*

*Document prepared by: Principal Engineering Manager · Staff AI Engineer · Technical Program Manager · Senior Scrum Master · Agentic AI Delivery Lead*

*Next action: Sprint 0 kickoff. Assign Engineer D to Docker Compose + mock data. Assign Engineer B to OdooClient + schema registry. All engineers verify local Docker environment on Day 1.*

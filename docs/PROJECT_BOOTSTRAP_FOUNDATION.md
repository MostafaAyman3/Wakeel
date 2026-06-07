# AERIE Project Bootstrap Foundation

This document is the Sprint 0 repository foundation generated from the Vision & Discovery Document, Master PRD, System Architecture Document, and Engineering Delivery Plan.

Priority rule: the System Architecture Document and Engineering Delivery Plan are highest priority. Where they conflict, this foundation follows the System Architecture Document. One important conflict: the delivery plan's older tree mentions Chroma, but the architecture explicitly removes vector DB / Chroma / Qdrant from MVP. This foundation excludes Chroma.

## Part 1 - Repository Structure

```text
aerie/
|-- README.md
|-- .env.example
|-- .gitignore
|-- docker-compose.yml
|-- .github/
|   `-- workflows/
|       `-- ci.yml
|-- backend/
|   |-- Dockerfile
|   |-- requirements.txt
|   |-- main.py
|   |-- api/v1/
|   |   |-- auth.py
|   |   |-- copilot.py
|   |   |-- actions.py
|   |   |-- reports.py
|   |   |-- procurement.py
|   |   `-- admin.py
|   |-- core/
|   |   |-- config.py
|   |   |-- auth.py
|   |   |-- database.py
|   |   |-- redis_client.py
|   |   `-- logging.py
|   |-- dependencies/
|   |   |-- auth.py
|   |   |-- database.py
|   |   `-- services.py
|   |-- middleware/
|   |   |-- request_id.py
|   |   |-- error_handler.py
|   |   `-- timing.py
|   |-- schemas/
|   |   |-- auth.py
|   |   |-- chat.py
|   |   |-- analytics.py
|   |   |-- action.py
|   |   |-- procurement.py
|   |   |-- websocket.py
|   |   |-- rfq.py
|   |   `-- audit.py
|   |-- models/
|   |   |-- user.py
|   |   |-- session.py
|   |   |-- confirmation_token.py
|   |   |-- audit_log.py
|   |   |-- analytics_report.py
|   |   |-- procurement_state.py
|   |   |-- rfq_draft.py
|   |   `-- ocr_quote.py
|   |-- repositories/
|   |   |-- users.py
|   |   |-- sessions.py
|   |   |-- audit_logs.py
|   |   |-- reports.py
|   |   |-- procurement.py
|   |   |-- rfq_drafts.py
|   |   `-- ocr_quotes.py
|   |-- services/
|   |   |-- odoo_client.py
|   |   |-- schema_registry.py
|   |   |-- entity_resolver.py
|   |   |-- domain_filter_builder.py
|   |   |-- session_service.py
|   |   |-- audit_service.py
|   |   |-- confirmation_service.py
|   |   |-- report_service.py
|   |   |-- procurement_service.py
|   |   `-- scheduler_service.py
|   `-- tests/
|-- agents/
|   |-- requirements.txt
|   |-- registry/
|   |   |-- README.md
|   |   `-- graph_registry.py
|   |-- graphs/
|   |   |-- copilot_graph.py
|   |   |-- analytics_graph.py
|   |   `-- procurement_graph.py
|   |-- nodes/
|   |   |-- orchestrator_node.py
|   |   |-- erp_query_node.py
|   |   |-- erp_action_node.py
|   |   |-- analytics_supervisor_node.py
|   |   |-- data_retrieval_node.py
|   |   |-- kpi_computation_node.py
|   |   |-- visualization_node.py
|   |   |-- insight_generation_node.py
|   |   |-- procurement_orchestrator_node.py
|   |   |-- inventory_monitor_node.py
|   |   |-- demand_forecaster_node.py
|   |   |-- supplier_evaluator_node.py
|   |   |-- rfq_generator_node.py
|   |   `-- ocr_agent_node.py
|   |-- tools/
|   |   |-- language_tools.py
|   |   |-- odoo_tools.py
|   |   |-- analytics_tools.py
|   |   |-- procurement_tools.py
|   |   `-- formatting_tools.py
|   |-- schemas/
|   |   |-- schema_registry.yaml
|   |   |-- copilot_state.py
|   |   |-- analytics_state.py
|   |   |-- procurement_state.py
|   |   `-- supplier_schema.py
|   |-- prompts/
|   `-- tests/
|-- frontend/
|   |-- Dockerfile
|   |-- package.json
|   |-- tsconfig.json
|   |-- tailwind.config.ts
|   |-- app/
|   |   |-- layout.tsx
|   |   |-- page.tsx
|   |   |-- login/page.tsx
|   |   |-- dashboard/page.tsx
|   |   |-- copilot/page.tsx
|   |   |-- procurement/page.tsx
|   |   |-- procurement/products/page.tsx
|   |   |-- procurement/rfq/page.tsx
|   |   |-- procurement/suppliers/page.tsx
|   |   |-- procurement/quotes/page.tsx
|   |   `-- admin/audit/page.tsx
|   |-- components/
|   |   |-- ui/
|   |   |-- chat/
|   |   |-- analytics/
|   |   |-- confirmation/
|   |   |-- procurement/
|   |   `-- layout/
|   |-- hooks/
|   |-- lib/
|   `-- types/
|-- database/
|   |-- migrations/
|   |-- models/
|   `-- seeds/
|-- deployment/
|   |-- docker/
|   `-- nginx/
|-- scripts/
|   |-- seed_mock_data.py
|   |-- schema_validate.py
|   `-- validate_demo.py
|-- shared/
|   |-- schemas/
|   |-- contracts/
|   |-- events/
|   `-- types/
`-- tests/
    |-- e2e/
    |-- integration/
    |-- nlp/
    |-- playwright/
    `-- fixtures/
```

## Part 2 - Backend Foundation

FastAPI is organized around API routers, core infrastructure, dependencies, middleware, schemas, ORM models, repositories, and services.

- `backend/main.py`: app factory entry point, middleware registration, router registration, health endpoint.
- `backend/api/v1/auth.py`: login, refresh, logout.
- `backend/api/v1/copilot.py`: session creation/deletion, REST chat, WebSocket chat streaming.
- `backend/api/v1/actions.py`: confirmation and rejection endpoints for Module 1 write actions.
- `backend/api/v1/reports.py`: analytics report retrieval.
- `backend/api/v1/procurement.py`: procurement health, alerts, products, forecasts, supplier rankings, RFQ draft approval/rejection, monitoring run, quote upload.
- `backend/api/v1/admin.py`: audit log query surface for admin users.
- `backend/core/config.py`: pydantic-settings configuration.
- `backend/core/auth.py`: JWT, bcrypt, role enforcement primitives.
- `backend/core/database.py`: SQLAlchemy async engine/session.
- `backend/core/redis_client.py`: Redis pool.
- `backend/core/logging.py`: structlog JSON logging.
- `backend/dependencies/*.py`: request-scoped dependency injection for auth, database, Redis, and service singletons.
- `backend/middleware/request_id.py`: request correlation IDs.
- `backend/middleware/error_handler.py`: standard error response and internal logging.
- `backend/middleware/timing.py`: duration metrics for responses.
- `backend/schemas/*.py`: Pydantic contracts for requests, responses, WebSocket events, analytics, procurement, RFQs, and audit logs.
- `backend/models/*.py`: SQLAlchemy ORM models for app database tables.
- `backend/repositories/*.py`: persistence adapters only; no business logic.
- `backend/services/odoo_client.py`: sole Odoo JSON-RPC access point.
- `backend/services/schema_registry.py`: YAML registry loader and validator hooks.
- `backend/services/entity_resolver.py`: natural-language entity to Odoo record resolution.
- `backend/services/domain_filter_builder.py`: validated Odoo domain construction.
- `backend/services/session_service.py`: Redis session context and TTL.
- `backend/services/audit_service.py`: INSERT-only audit logger.
- `backend/services/confirmation_service.py`: single-use, session-bound confirmation token lifecycle.
- `backend/services/report_service.py`: persisted analytics report storage/retrieval.
- `backend/services/procurement_service.py`: app DB procurement state and RFQ draft coordination.
- `backend/services/scheduler_service.py`: APScheduler bootstrap for monitoring cycles.

Backend invariants: all protected endpoints use role dependencies; all Odoo writes require confirmation token validation at the API layer; agents never call Odoo directly; raw exceptions are never returned to clients.

## Part 3 - LangGraph Foundation

Graph files are declarations of typed state machines. Node files receive a typed state object and return state updates. Tools wrap deterministic services and external calls. Prompts are versioned separately and are intentionally empty during bootstrap.

Module 1 graph structure:

```text
CopilotGraph
  start -> orchestrator_node
  orchestrator_node -> erp_query_node when intent=query.data/action.search
  orchestrator_node -> erp_action_node when intent=action.create/action.update
  orchestrator_node -> analytics_graph when intent=query.analytics
  orchestrator_node -> clarification/terminal when confidence < 0.70
  downstream nodes -> response_assembly -> end

AnalyticsGraph
  analytics_supervisor_node -> data_retrieval_node
  data_retrieval_node -> kpi_computation_node
  kpi_computation_node -> visualization_node and insight_generation_node
  visualization_node + insight_generation_node -> analytics_supervisor_node
  analytics_supervisor_node -> end
```

Module 2 graph structure:

```text
ProcurementGraph
  start -> procurement_orchestrator_node
  procurement_orchestrator_node -> inventory_monitor_node
  inventory_monitor_node -> demand_forecaster_node when risk exists
  demand_forecaster_node -> supplier_evaluator_node
  supplier_evaluator_node -> rfq_generator_node
  rfq_generator_node -> persist_drafts -> end
```

Agent registration strategy:

- `agents/registry/graph_registry.py` will map graph keys to graph factories: `copilot`, `analytics`, `procurement`.
- Agent IDs are canonical: `AGENT-1-01` through `AGENT-1-08`, `AGENT-2-01` through `AGENT-2-06`.
- Registry metadata includes module, node path, agent ID, graph membership, LLM policy, and whether the node is deterministic.
- LangSmith tags must include module, graph, intent code, session ID, and agent ID.

## Part 4 - Database Foundation

Application PostgreSQL is separate from Odoo PostgreSQL.

Initial tables:

- `users`: application users, roles, password hashes.
- `sessions`: app session metadata and active/inactive status.
- `confirmation_tokens`: token hash, session ID, action ID, expiry, consumed timestamp.
- `audit_log`: INSERT-only ERP write, confirmation, rejection, and failure records.
- `analytics_reports`: persisted report payloads and metadata.
- `procurement_alerts`: active and historical inventory risk alerts.
- `product_risk_cache`: latest risk state per product.
- `demand_forecasts`: latest forecast snapshots.
- `supplier_scores`: latest supplier ranking snapshots.
- `rfq_drafts`: pending/rejected/approved RFQ draft payloads.
- `monitoring_cycles`: scheduled and manual procurement cycle runs.
- `ocr_quotes`: uploaded quote metadata and extraction result summary.

Initial indexes:

- `users.username` unique.
- `sessions.session_id`.
- `confirmation_tokens.token_hash` unique and `action_id`.
- `audit_log.timestamp`, `audit_log.session_id`, `audit_log.user_id`, `audit_log.action_type`.
- `analytics_reports.report_id`.
- `procurement_alerts.product_id`, `procurement_alerts.risk_state`, `procurement_alerts.created_at`.
- `product_risk_cache.product_id` unique.
- `rfq_drafts.status`, `rfq_drafts.created_at`, `rfq_drafts.odoo_purchase_order_id`.
- `monitoring_cycles.started_at`, `monitoring_cycles.status`.

Constraints:

- Role enum: `admin`, `manager`, `analyst`, `procurement`, `sales`.
- Audit log is insert-only; update/delete blocked by database trigger in migration.
- Confirmation tokens are single use.
- RFQ draft status enum: `pending`, `approved`, `rejected`, `expired`.
- Risk state enum: `HEALTHY`, `WATCH`, `AT_RISK`, `CRITICAL`, `STOCKOUT`.

Migrations:

- `001_create_users`
- `002_create_sessions`
- `003_create_confirmation_tokens`
- `004_create_audit_log`
- `005_create_reports`
- `006_create_procurement_state`
- `007_create_rfq_drafts`
- `008_create_monitoring_cycles`
- `009_create_ocr_quotes`

No SQL is included in this bootstrap.

## Part 5 - Odoo Integration Foundation

Folder responsibilities:

- `backend/services/odoo_client.py`: singleton JSON-RPC client; authenticate, refresh, `search_read`, `create`, `write`, `execute_action`, `fields_get`; rate limit 10 calls/sec; retry once; structured logs.
- `agents/schemas/schema_registry.yaml`: NLP concept to Odoo model/field mapping. Covers customers, suppliers, products, stock, sales, invoices, purchase orders, supplier pricelists, reorder rules.
- `backend/services/schema_registry.py`: load, cache, and expose schema lookup; startup validation hook.
- `backend/services/entity_resolver.py`: resolve names to Odoo IDs using registry-defined models and ranking rules.
- `backend/services/domain_filter_builder.py`: convert entities, time ranges, and filters to validated Odoo domains.
- `scripts/schema_validate.py`: validate registry models and fields against live Odoo.
- `scripts/seed_mock_data.py`: idempotent Odoo mock data loader.

Invariant: no backend API route, agent node, or tool constructs raw JSON-RPC calls directly.

## Part 6 - Frontend Foundation

Next.js App Router structure:

- `app/login/page.tsx`: UI-01 login.
- `app/dashboard/page.tsx`: UI-02 dashboard.
- `app/copilot/page.tsx`: UI-03 chat and UI-04 analytics report surface.
- `app/procurement/page.tsx`: UI-06 procurement dashboard.
- `app/procurement/products/page.tsx`: UI-07 product risk list.
- `app/procurement/rfq/page.tsx`: UI-08 RFQ review.
- `app/procurement/suppliers/page.tsx`: UI-09 supplier comparison.
- `app/procurement/quotes/page.tsx`: UI-10 quote upload/review.
- `app/admin/audit/page.tsx`: UI-11 audit log viewer.

Component groups:

- `components/ui`: base primitives, badges, modal, skeleton, empty state, toast, RTL wrapper.
- `components/chat`: chat shell, messages, input, agent reasoning panel, language toggle.
- `components/analytics`: KPI grid, charts, report, insight cards.
- `components/confirmation`: non-dismissable confirmation panel.
- `components/procurement`: health score, alerts, risk table, RFQ cards, supplier comparison, quote upload/review.
- `components/layout`: sidebar, header, navigation.

Hooks and state:

- `useAuth`: session/user state and refresh lifecycle.
- `useChat`: chat session state, optimistic message updates, REST fallback.
- `useWebSocket`: streaming with reconnect and fallback signal.
- `useProcurement`: procurement dashboard fetching and mutations.

API layer:

- `frontend/lib/api.ts`: typed fetch wrapper using shared response contracts.
- `frontend/lib/rtl.ts`: language and direction helpers.

RTL strategy:

- Arabic detection sets `dir="rtl"` at the app shell or response container.
- Arabic font is IBM Plex Arabic or Noto Kufi Arabic; English uses Inter/system.
- Direction-aware components avoid absolute left/right assumptions.

## Part 7 - Shared Types

Contracts must exist in both backend Pydantic schemas and frontend TypeScript types.

Response contracts:

- `ApiResponse<T>`: `data`, `metadata`, `error`.
- `ErrorResponse`: `error_code`, `message`, `request_id`.
- `PerformanceMetadata`: request, agent, Odoo, and LLM duration fields.

Agent event contracts:

- `AgentStepEvent`: step name, agent ID, status, elapsed time, optional metadata.
- `AgentTraceSummary`: graph, node count, tool call count, LangSmith trace URL.

WebSocket contracts:

- `agent_step`, `text_token`, `chart_ready`, `action_required`, `complete`, `error`.

Analytics contracts:

- `KPIReport`, `KPIValue`, `ChartConfig`, `AnalyticsReport`, `Insight`, `DataBasis`.

RFQ contracts:

- `RFQDraft`, `RFQDraftLine`, `SupplierScore`, `ApprovalRequest`, `ApprovalResult`, `RejectionRequest`.

Procurement contracts:

- `ProductRisk`, `DemandForecast`, `ProcurementAlert`, `ProcurementHealthSummary`, `MonitoringCycleResult`.

## Part 8 - Environment Configuration

Required config groups:

- Application metadata: app env, name, version, frontend/backend URLs.
- Security: JWT secret, algorithm, token expiry, confirmation token TTL.
- App PostgreSQL: host, port, DB, user, password.
- Odoo PostgreSQL: host, port, DB, user, password.
- Odoo JSON-RPC: base URL, username, password, rate limit.
- Redis: URL and session TTL.
- OpenAI: API key, primary model, fast model.
- LangSmith: tracing flag, API key, project.
- Scheduler: procurement monitoring interval.
- Frontend: public API and WebSocket URLs.

Strategy:

- `.env.example` documents all variables.
- `.env` is never committed.
- Backend config is centralized in `backend/core/config.py`.
- Frontend only receives `NEXT_PUBLIC_*` values.
- Secrets are read from environment only; no defaults for real keys.

## Part 9 - Docker Architecture

Services:

- `postgres`: application database.
- `odoo-db`: Odoo database.
- `redis`: session and cache store.
- `odoo`: Odoo 17 Community.
- `backend`: FastAPI.
- `frontend`: Next.js.

Volumes:

- `app_postgres_data`
- `odoo_postgres_data`
- `redis_data`
- `odoo_data`

Network:

- Single Docker network: `aerie_network`.

Startup order:

- `postgres` and `redis` before `backend`.
- `odoo-db` before `odoo`.
- `odoo` before `backend`.
- `backend` before `frontend`.

Health checks:

- PostgreSQL: `pg_isready`.
- Redis: `redis-cli ping`.
- Odoo: `/web/health`.
- Backend: `/health`.
- Frontend: `/`.

## Part 10 - Testing Foundation

Pytest structure:

- `backend/tests`: API, service, repository, auth, confirmation gate, audit log, Odoo client.
- `agents/tests`: graph, node, deterministic computation, routing, failure handling.
- `tests/integration`: API against Docker Compose stack.
- `tests/e2e`: five demo scenarios.
- `tests/nlp`: Arabic and English intent test sets.

Playwright structure:

- `tests/playwright`: login, copilot chat, streaming fallback, analytics report, procurement dashboard, RFQ review, audit log.

Agent testing:

- Mock `OdooClient`, Redis, and LLM calls for node tests.
- Deterministic nodes tested with fixed fixtures.
- Graph tests assert transitions, terminal states, and maximum tool calls.

Mock Odoo strategy:

- `scripts/seed_mock_data.py` creates the required synthetic Odoo dataset.
- `scripts/schema_validate.py` validates registry model/field paths against live Odoo.
- Integration tests use seeded Odoo, never direct Odoo database writes.

## Part 11 - CI/CD Foundation

GitHub Actions workflows:

- `ci.yml`: backend lint/test, agent lint/test, frontend typecheck/build.
- Future `docker.yml`: Docker Compose build validation.
- Future `e2e.yml`: Playwright smoke tests after stack bootstraps.

Pull request validation:

- Backend: `ruff check`, `pytest`.
- Frontend: `npm install`, `tsc --noEmit`, `next build`.
- Agents: graph/node unit tests and deterministic computation tests.
- No deployment from CI in MVP.

## Part 12 - Coding Standards

Python:

- Python 3.11+.
- Type hints on all public functions.
- Pydantic schemas for API contracts.
- SQLAlchemy repositories isolate persistence.
- `structlog`, not `print`.
- Async I/O for API, Odoo, Redis, and database paths.

TypeScript:

- Strict TypeScript.
- Shared API contracts mirrored in `frontend/types`.
- No `any` for API responses.
- Feature components are small and domain-named.
- RTL behavior is component-level, not ad hoc CSS overrides.

LangGraph:

- Every node receives and returns typed state.
- Deterministic business math does not use LLMs.
- Odoo access is through services/tools only.
- Confirmation gate is API-enforced.
- Max 10 tool calls per agent invocation.
- LangSmith tracing is required for all graph runs.

Testing:

- Unit tests for services and deterministic nodes.
- Integration tests for confirmation gate, OdooClient, schema validation, and key APIs.
- E2E tests cover all five demo scenarios.
- Arabic NLP test set is created in Sprint 0.

Git:

- Branch strategy: `main`, `develop`, `feature/<epic>-<slug>`, `fix/<slug>`.
- Commit convention: Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`).
- PRs require passing CI and owner review for touched areas.

## Part 13 - Sprint 0 Bootstrap Checklist

- [ ] Repository structure exists and is committed.
- [ ] `.env.example` contains all required variables.
- [ ] Docker Compose starts app DB, Odoo DB, Redis, Odoo, backend, and frontend.
- [ ] Backend `/health` returns `{"status":"ok"}`.
- [ ] Next.js dev server starts.
- [ ] PostgreSQL migrations directory exists with migration plan.
- [ ] OdooClient contract is finalized before agents implement against it.
- [ ] Schema registry placeholder exists and validation script path is reserved.
- [ ] Mock data script path is reserved.
- [ ] Arabic and English NLP test set paths exist.
- [ ] Shared contracts are defined before endpoint implementation begins.
- [ ] Confirmation token protocol is documented and owned.
- [ ] Audit log schema plan is documented as insert-only.
- [ ] LangSmith environment variables are documented.
- [ ] CI workflow is present.
- [ ] Team ownership boundaries match the delivery plan.


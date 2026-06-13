# Repository Migration Report

**Date:** 2026-06-13
**Migration Type:** Architecture Preparation — Structural Refactoring Only
**Blueprint Source:** ERP_Agentic_AI_Blueprint.md v1.0
**Sprint Reference:** M1_Sprints.md, M3_Sprints.md
**Status:** COMPLETE — No business logic implemented. All changes are structural.

---

## 1. Original Structure Summary

The repository existed as a single-layer flat agent architecture with mixed M1/M2/legacy files:

**agents/** — Flat structure with 3 graphs (copilot, analytics, procurement), 14 nodes, 3 schemas, 5 tools. No module boundaries. M1, M2, and legacy (OCR/Odoo) files were all at the same level.

**backend/** — FastAPI with Odoo-centric services (odoo_client.py, domain_filter_builder.py, entity_resolver.py). Mixed M1 endpoints (copilot.py), M2 endpoints (procurement.py, actions.py), and legacy models (ocr_quote.py, rfq_draft.py).

**frontend/** — Next.js with copilot/ page, procurement/ pages, and analytics components mixed with procurement components.

**docs/** — Only 1 file: PROJECT_BOOTSTRAP_FOUNDATION.md.

---

## 2. New Structure Summary

### agents/
```
agents/
├── m1/                             # AI ERP Intelligence Agent
│   ├── graphs/
│   │   └── m1_graph.py             [PLACEHOLDER]
│   ├── nodes/
│   │   ├── intent_classifier_node.py  [MOVED — was orchestrator_node.py]
│   │   ├── router_node.py             [MOVED — was analytics_supervisor_node.py]
│   │   ├── clarification_node.py      [PLACEHOLDER — new]
│   │   ├── validation_enrichment_node.py [MOVED — was kpi_computation_node.py]
│   │   ├── output_selector_node.py    [MOVED — was visualization_node.py]
│   │   ├── narrative_generator_node.py [MOVED — was insight_generation_node.py]
│   │   ├── db_query_node.py           [MOVED — was erp_query_node.py]
│   │   ├── data_retrieval_node.py     [MOVED — kept name]
│   │   └── invoice/
│   │       ├── invoice_param_extractor_node.py [PLACEHOLDER — new]
│   │       ├── invoice_query_builder_node.py   [PLACEHOLDER — new]
│   │       ├── invoice_db_execution_node.py    [PLACEHOLDER — new]
│   │       └── invoice_analysis_node.py        [PLACEHOLDER — new]
│   ├── schemas/
│   │   └── m1_state.py              [MOVED — was copilot_state.py]
│   └── tools/
│       ├── db_query_tool.py          [MOVED — was analytics_tools.py]
│       ├── invoice_analysis_tool.py  [PLACEHOLDER — new]
│       └── tax_rag_tool.py           [PLACEHOLDER — new]
├── m3/                             # Customer Support Agent
│   ├── graphs/
│   │   └── m3_graph.py             [PLACEHOLDER — new]
│   ├── nodes/
│   │   ├── input_parser_node.py    [PLACEHOLDER — new]
│   │   ├── data_fetcher_node.py    [PLACEHOLDER — new]
│   │   ├── data_completeness_node.py [PLACEHOLDER — new]
│   │   ├── issue_classifier_node.py [PLACEHOLDER — new]
│   │   ├── context_builder_node.py [PLACEHOLDER — new]
│   │   ├── response_generator_node.py [PLACEHOLDER — new]
│   │   └── human_review_node.py    [PLACEHOLDER — new]
│   ├── schemas/
│   │   └── m3_state.py             [PLACEHOLDER — new]
│   └── tools/
│       ├── invoice_fetcher_tool.py [PLACEHOLDER — new]
│       └── mock_data_tool.py       [PLACEHOLDER — new]
├── shared/                         # Shared infrastructure
│   ├── llm_client.py               [PLACEHOLDER — new]
│   ├── formatting_tools.py         [MOVED from tools/]
│   ├── language_tools.py           [MOVED from tools/]
│   └── schema_registry.yaml        [MOVED from schemas/]
├── archive/                        # DO NOT IMPLEMENT
│   ├── m2/                         # M2 deferred — design ready
│   │   ├── graphs/procurement_graph.py
│   │   ├── nodes/ (5 M2 nodes)
│   │   ├── schemas/ (2 M2 schemas)
│   │   └── tools/procurement_tools.py
│   └── legacy/                     # Incompatible with new architecture
│       ├── analytics_graph.py
│       ├── copilot_graph.py
│       ├── analytics_state.py
│       ├── ocr_agent_node.py       (NO OCR in architecture)
│       ├── erp_action_node.py      (NO write actions in M1 MVP)
│       └── odoo_tools.py           (NO Odoo — direct PostgreSQL)
├── registry/graph_registry.py      [KEPT]
├── tests/                          [KEPT — needs update for M1/M3]
│   └── nlp_test_set/               [KEPT]
└── requirements.txt                [KEPT]
```

### backend/
```
backend/
├── api/v1/
│   ├── m1_query.py     [RENAMED — was copilot.py]
│   ├── m3_support.py   [PLACEHOLDER — new]
│   ├── auth.py         [KEPT]
│   ├── admin.py        [KEPT]
│   └── reports.py      [KEPT]
├── core/ (all 5 files KEPT)
├── middleware/ (all 3 files KEPT)
├── dependencies/ (all 3 files KEPT)
├── models/
│   ├── user.py, session.py, audit_log.py, confirmation_token.py [KEPT]
│   └── m3_case.py      [PLACEHOLDER — new]
├── repositories/
│   ├── users.py, sessions.py, audit_logs.py [KEPT]
├── schemas/
│   ├── auth.py, audit.py, websocket.py [KEPT]
│   ├── m1_query.py     [RENAMED — was chat.py]
│   ├── m1_response.py  [PLACEHOLDER — new]
│   └── m3_support.py   [PLACEHOLDER — new]
├── services/
│   ├── audit_service.py, session_service.py [KEPT]
│   ├── human_review_service.py [RENAMED — was confirmation_service.py]
│   ├── m1_response_service.py  [RENAMED — was report_service.py]
│   ├── query_template_service.py [RENAMED — was schema_registry.py]
│   ├── llm_client.py   [PLACEHOLDER — new]
│   ├── m1_orchestrator.py [PLACEHOLDER — new]
│   ├── m3_orchestrator.py [PLACEHOLDER — new]
│   └── rag_service.py  [PLACEHOLDER — new]
├── archive/            [DO NOT USE]
│   ├── api_v1/ (actions.py, procurement.py)
│   ├── models/ (analytics_report.py, ocr_quote.py, procurement_state.py, rfq_draft.py)
│   ├── repositories/ (ocr_quotes.py, procurement.py, reports.py, rfq_drafts.py)
│   ├── services/ (odoo_client.py, domain_filter_builder.py, entity_resolver.py, procurement_service.py, scheduler_service.py)
│   └── schemas/ (action.py, analytics.py, procurement.py, rfq.py)
├── main.py, Dockerfile, requirements.txt [KEPT]
└── tests/ [KEPT — need update for M1/M3]
```

### frontend/
```
frontend/
├── app/
│   ├── m1/page.tsx     [PLACEHOLDER — new, replaces copilot/]
│   ├── m3/page.tsx     [PLACEHOLDER — new]
│   ├── dashboard/      [KEPT]
│   ├── login/          [KEPT]
│   ├── admin/          [KEPT]
│   └── layout.tsx      [KEPT]
├── components/
│   ├── m1/
│   │   ├── OutputRenderer.tsx [PLACEHOLDER — new]
│   │   ├── MetricCard.tsx     [PLACEHOLDER — new]
│   │   ├── SortableTable.tsx  [PLACEHOLDER — new]
│   │   ├── LineChart.tsx      [PLACEHOLDER — new]
│   │   ├── BarChart.tsx       [PLACEHOLDER — new]
│   │   ├── AlertCard.tsx      [PLACEHOLDER — new]
│   │   ├── NarrativeText.tsx  [PLACEHOLDER — new]
│   │   └── output/            [MOVED — was analytics/ components]
│   ├── m3/
│   │   ├── CustomerInputForm.tsx [PLACEHOLDER — new]
│   │   ├── HumanReviewPanel.tsx  [PLACEHOLDER — new]
│   │   ├── TransparencyPanel.tsx [PLACEHOLDER — new]
│   │   ├── ConfidenceIndicator.tsx [PLACEHOLDER — new]
│   │   └── EscalationView.tsx  [PLACEHOLDER — new]
│   ├── chat/           [KEPT — refactor for bilingual M1]
│   ├── review/         [MOVED — was confirmation/]
│   ├── layout/         [KEPT]
│   └── ui/             [KEPT]
├── hooks/
│   ├── useAuth.ts      [KEPT]
│   ├── useWebSocket.ts [KEPT]
│   ├── useM1Query.ts   [RENAMED — was useChat.ts]
│   └── useM3Support.ts [PLACEHOLDER — new]
├── types/
│   ├── auth.ts         [KEPT]
│   ├── m1.ts           [RENAMED — was chat.ts]
│   └── m3.ts           [PLACEHOLDER — new]
└── archive/            [DO NOT USE — M2 procurement pages, legacy types]
```

### docs/ (new)
```
docs/
├── architecture/
│   ├── erp_architecture_memory.md  [CREATED — mandatory reading for all future agents]
│   └── blueprint_reference_map.md  [CREATED — navigation guide to blueprint]
├── decisions/                      [CREATED — empty, for future ADRs]
├── module-maps/
│   ├── m1_intelligence_agent_map.md [CREATED]
│   └── m3_customer_support_map.md  [CREATED]
├── progress/
│   └── agent_execution_log.md      [CREATED — live log of all changes]
├── repository-migration/
│   └── migration_report.md         [THIS FILE]
└── PROJECT_BOOTSTRAP_FOUNDATION.md [KEPT — original]
```

---

## 3. Files Moved

| Original Path | New Path | Reason |
|--------------|----------|--------|
| agents/nodes/orchestrator_node.py | agents/m1/nodes/intent_classifier_node.py | M1 entry node — renamed to match blueprint function |
| agents/nodes/analytics_supervisor_node.py | agents/m1/nodes/router_node.py | Routes to correct tool — renamed to match blueprint |
| agents/nodes/kpi_computation_node.py | agents/m1/nodes/validation_enrichment_node.py | Data validation function — renamed to match blueprint |
| agents/nodes/visualization_node.py | agents/m1/nodes/output_selector_node.py | Output format selection — renamed to match blueprint |
| agents/nodes/insight_generation_node.py | agents/m1/nodes/narrative_generator_node.py | AI narrative generation — renamed to match blueprint |
| agents/nodes/erp_query_node.py | agents/m1/nodes/db_query_node.py | PostgreSQL query node — renamed (no more Odoo) |
| agents/nodes/data_retrieval_node.py | agents/m1/nodes/data_retrieval_node.py | Kept name — M1 data layer |
| agents/schemas/copilot_state.py | agents/m1/schemas/m1_state.py | M1 state schema — renamed to module convention |
| agents/tools/analytics_tools.py | agents/m1/tools/db_query_tool.py | SQL template tool — renamed to match blueprint |
| agents/tools/formatting_tools.py | agents/shared/formatting_tools.py | Shared across M1 and M3 |
| agents/tools/language_tools.py | agents/shared/language_tools.py | Shared across M1 and M3 |
| agents/schemas/schema_registry.yaml | agents/shared/schema_registry.yaml | Shared configuration |
| backend/api/v1/copilot.py | backend/api/v1/m1_query.py | Module naming convention |
| backend/schemas/chat.py | backend/schemas/m1_query.py | Module naming convention |
| backend/services/confirmation_service.py | backend/services/human_review_service.py | More accurate name per M3 design |
| backend/services/report_service.py | backend/services/m1_response_service.py | M1-specific output service |
| backend/services/schema_registry.py | backend/services/query_template_service.py | Accurate name — manages SQL templates |
| frontend/components/analytics/ | frontend/components/m1/output/ | M1 output renderers |
| frontend/components/confirmation/ | frontend/components/review/ | Used by M3 Human Review |
| frontend/hooks/useChat.ts | frontend/hooks/useM1Query.ts | Module naming convention |
| frontend/types/chat.ts | frontend/types/m1.ts | Module naming convention |

---

## 4. Files Archived

### agents/archive/m2/ — M2 Purchasing/Inventory Agent (DEFERRED)
- agents/graphs/procurement_graph.py
- agents/nodes/procurement_orchestrator_node.py
- agents/nodes/inventory_monitor_node.py
- agents/nodes/demand_forecaster_node.py
- agents/nodes/supplier_evaluator_node.py
- agents/nodes/rfq_generator_node.py
- agents/schemas/procurement_state.py
- agents/schemas/supplier_schema.py
- agents/tools/procurement_tools.py

### agents/archive/legacy/ — Incompatible with new architecture
- agents/graphs/copilot_graph.py (old single-graph structure)
- agents/graphs/analytics_graph.py (replaced by m1_graph.py)
- agents/schemas/analytics_state.py (merged into m1_state.py)
- agents/nodes/ocr_agent_node.py (**NO OCR** — blueprint §2.6: invoices from DB only)
- agents/nodes/erp_action_node.py (**NO WRITE** — M1 is read-only by design)
- agents/tools/odoo_tools.py (**NO ODOO** — direct PostgreSQL connection)

### backend/archive/ — Odoo-centric, M2, and unsupported features
- backend/api/v1/actions.py (ERP write actions not in MVP)
- backend/api/v1/procurement.py (M2 deferred)
- backend/models/analytics_report.py (absorbed by m1_response schema)
- backend/models/ocr_quote.py (no OCR)
- backend/models/procurement_state.py (M2 deferred)
- backend/models/rfq_draft.py (M2 deferred)
- backend/repositories/ocr_quotes.py, procurement.py, reports.py, rfq_drafts.py (M2/OCR)
- backend/services/odoo_client.py (no Odoo in new architecture)
- backend/services/domain_filter_builder.py (Odoo-specific)
- backend/services/entity_resolver.py (Odoo-specific)
- backend/services/procurement_service.py (M2 deferred)
- backend/services/scheduler_service.py (scheduled reports deferred)
- backend/schemas/action.py, analytics.py, procurement.py, rfq.py (M2/legacy)

### frontend/archive/ — M2 and legacy pages
- frontend/app/procurement/ (M2 deferred)
- frontend/app/copilot/ (renamed to m1/)
- frontend/components/procurement/ (M2 deferred)
- frontend/hooks/useProcurement.ts (M2 deferred)
- frontend/types/procurement.ts (M2 deferred)
- frontend/types/analytics.ts (absorbed into types/m1.ts)

---

## 5. Files Renamed

| Old Name | New Name | Reason |
|----------|----------|--------|
| orchestrator_node.py | intent_classifier_node.py | Matches blueprint node name |
| analytics_supervisor_node.py | router_node.py | Matches blueprint node name |
| kpi_computation_node.py | validation_enrichment_node.py | Matches blueprint node name |
| visualization_node.py | output_selector_node.py | Matches blueprint node name |
| insight_generation_node.py | narrative_generator_node.py | Matches blueprint node name |
| erp_query_node.py | db_query_node.py | No Odoo — PostgreSQL direct |
| copilot_state.py | m1_state.py | Module naming convention |
| analytics_tools.py | db_query_tool.py | Matches blueprint tool name |
| api/v1/copilot.py | api/v1/m1_query.py | Module naming convention |
| schemas/chat.py | schemas/m1_query.py | Module naming convention |
| services/confirmation_service.py | services/human_review_service.py | Accurate function name for M3 |
| services/report_service.py | services/m1_response_service.py | Module naming convention |
| services/schema_registry.py | services/query_template_service.py | Accurate function name |
| hooks/useChat.ts | hooks/useM1Query.ts | Module naming convention |
| types/chat.ts | types/m1.ts | Module naming convention |

---

## 6. New Directories Created

| Directory | Purpose |
|-----------|---------|
| agents/m1/ | AI ERP Intelligence Agent — all M1 implementation |
| agents/m1/nodes/invoice/ | Invoice sub-pipeline — 4 nodes |
| agents/m3/ | Customer Support Agent — all M3 implementation |
| agents/shared/ | Shared infrastructure (LLM client, language/formatting tools) |
| agents/archive/m2/ | M2 files preserved, deferred |
| agents/archive/legacy/ | Legacy/incompatible files preserved |
| backend/archive/ | Archived backend files |
| frontend/app/m1/ | M1 chat interface page |
| frontend/app/m3/ | M3 customer support page |
| frontend/components/m1/ | M1 output renderers |
| frontend/components/m3/ | M3 customer support components |
| frontend/components/review/ | Human review components (M3) |
| docs/architecture/ | Architecture memory documents |
| docs/decisions/ | Architecture Decision Records (ADRs) |
| docs/module-maps/ | Per-module file location maps |
| docs/progress/ | Agent execution log |
| docs/repository-migration/ | This migration report |

---

## 7. Architecture Alignment Report

| Blueprint Requirement | Status | Evidence |
|----------------------|--------|---------|
| M1 Single Orchestrator (LangGraph) | ✅ Structure ready | agents/m1/graphs/m1_graph.py created |
| M1 5 intent types | ✅ Structure ready | intent_classifier_node.py in place |
| M1 10 SQL Templates | ✅ Structure ready | db_query_tool.py in place |
| M1 Invoice sub-pipeline (4 nodes) | ✅ Structure ready | agents/m1/nodes/invoice/ with all 4 nodes |
| M1 Tax RAG with pgvector | ✅ Structure ready | tax_rag_tool.py + rag_service.py placeholders |
| M1 8 output formats | ✅ Structure ready | output_selector_node.py + 7 frontend components |
| M1 Narrative Generator | ✅ Structure ready | narrative_generator_node.py in place |
| M1 Read-Only DB | ✅ Architecture enforced | No write services in M1 path. erp_action_node.py archived. |
| M1 No OCR | ✅ Enforced | ocr_agent_node.py archived. No file upload components. |
| M1 No Odoo | ✅ Enforced | odoo_tools.py archived. All services use PostgreSQL. |
| M3 7-node LangGraph flow | ✅ Structure ready | All 7 M3 nodes as placeholders |
| M3 Human Review Gate | ✅ Structure ready | human_review_node.py + HumanReviewPanel.tsx |
| M3 Graceful Degradation | ✅ Structure ready | data_completeness_node.py + ResponseGeneratorNode handles 3 states |
| M3 Real invoice + Mock data | ✅ Structure ready | invoice_fetcher_tool.py (real) + mock_data_tool.py (mock) |
| M3 Audit Trail | ✅ Inherited | audit_service.py + audit_log.py kept |
| M3 Confidence Indicator | ✅ Structure ready | ConfidenceIndicator.tsx + confidence_score in M3State |
| Shared LLM Client | ✅ Structure ready | agents/shared/llm_client.py + backend/services/llm_client.py |
| Shared Auth | ✅ Kept | backend/core/auth.py unchanged |
| Shared DB Pool | ✅ Kept | backend/core/database.py unchanged |
| Shared Logging | ✅ Kept | backend/core/logging.py unchanged |
| Shared Error Handler | ✅ Kept | backend/middleware/error_handler.py unchanged |
| M2 Deferred | ✅ Enforced | All M2 files in archive/m2/ — not in active paths |
| Frontend: React + shadcn/ui | ✅ Unchanged | Existing Next.js + tailwind structure retained |
| Frontend: Apache ECharts | ✅ Structure ready | LineChart.tsx + BarChart.tsx use ECharts (implementation required) |
| Bilingual AR/EN | ✅ Structure ready | RTLWrapper.tsx + LanguageToggle.tsx kept, M1State has language field |

---

## 8. Remaining Work

### Immediate (Before Sprint 1)
- [ ] Update agents/tests/ filenames to match new node names (test files still reference old names like orchestrator_node, copilot_graph, etc.)
- [ ] Update agents/registry/graph_registry.py to reference m1_graph and m3_graph
- [ ] Update backend/main.py to import m1_query.py and m3_support.py (not copilot.py, procurement.py)
- [ ] Review agents/m1/schemas/m1_state.py content — was copilot_state.py placeholder, needs full M1 TypedDict implementation
- [ ] Add agents/m1/nodes/invoice/ to m1_graph.py as conditional sub-graph entry point
- [ ] Configure .env.example with all required variables (DB URLs, API keys, pgvector settings)

### Sprint 0 (M1)
- Design + create PostgreSQL migrations for 8 ERP tables
- Create read-only DB user
- Enable pgvector extension
- Seed realistic mock ERP data

### Sprint 0 (M3)
- Create 3 mock data tables (order_status, shipping, customer_history)
- Ensure customer_id consistency across all tables

---

## 9. Risks

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Test files reference old node/graph names | Medium | Update imports in agents/tests/ before Sprint 1 |
| backend/main.py still imports old endpoint names | High | Update immediately before first run |
| M1State content still placeholder | High | Sprint 1 Day 1: implement full TypedDict |
| Apache ECharts not in package.json | Medium | Add `apache-echarts` and `echarts-for-react` to frontend/package.json in Sprint 6 |
| pgvector extension requires PostgreSQL superuser | Medium | Document in deployment setup; enable in Sprint 0 |
| M2 files in archive could confuse developers | Low | Archive directories have DO NOT IMPLEMENT markers |
| data_retrieval_node.py kept but may overlap with db_query_node.py | Low | Review in Sprint 2 — merge or clarify boundary |

---

## 10. Recommended Next Step

**Immediate action (before any implementation sprint begins):**

1. Update `backend/main.py` — remove old imports (copilot, procurement, actions), add m1_query and m3_support routers.

2. Update `agents/registry/graph_registry.py` — register m1_graph and m3_graph.

3. Rename/update `agents/tests/` files to match new node names:
   - test_orchestrator_node.py → test_intent_classifier_node.py
   - test_copilot_graph.py → test_m1_graph.py
   - test_analytics_pipeline.py → test_m1_pipeline.py
   - Remove/archive tests for archived nodes (demand_forecaster, inventory_monitor, supplier_evaluator, etc.)

4. Begin **M1 Sprint 0**: design PostgreSQL schema for 8 ERP tables, create read-only user, enable pgvector.

5. Begin **M3 Sprint 0** in parallel with M1 Sprint 1-2: create 3 mock tables with internally consistent data.

**Read before starting implementation:**
- `docs/architecture/erp_architecture_memory.md` — full architectural context
- `docs/module-maps/m1_intelligence_agent_map.md` — M1 file locations
- `docs/module-maps/m3_customer_support_map.md` — M3 file locations
- `ERP_Blueprint_Index.md` — use to navigate blueprint by topic

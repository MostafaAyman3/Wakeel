# ERP Agentic AI Platform — Architecture Memory

> MANDATORY: Any AI agent working on this repository MUST read this file before making any changes.
> This file is the authoritative architectural reference for the current repository state.

---

## Platform Identity

**Name:** ERP Agentic AI Platform (codename: Wakeel)
**Type:** Agentic Intelligence Layer — NOT a chatbot added on top of ERP
**Version:** Blueprint 1.0 | Team: 6 people | Context: Graduation project / enterprise demo

---

## Module Map

| Module | Priority | Purpose | Status |
|--------|----------|---------|--------|
| M1 — AI ERP Intelligence Agent | CRITICAL | NL queries → ERP insights + financial analysis | Implement Now |
| M3 — Customer Support Agent | CRITICAL | Customer issue resolution with human review | Implement Now |
| M2 — Purchasing/Inventory Agent | DEFERRED | Procurement automation | Design ready, implement after M1+M3 |

**Rule:** Do NOT touch M2 implementation until M1 and M3 are demo-ready.

---

## M1 — AI ERP Intelligence Agent

### Purpose
Convert any natural language business question (Arabic/English) into a complete analytical insight extracted from real ERP data, presented in the most appropriate format for the query type and user level — without the user writing a single SQL query.

### LangGraph State Schema (M1)
```python
class M1State(TypedDict):
    query: str
    language: Literal["ar", "en"]
    intent: Literal["financial_query", "operational_query", "invoice_analysis", "tax_reasoning", "clarification_needed"]
    extracted_params: dict
    raw_data: list
    data_confidence: float
    output_format: Literal["direct_text", "metric_card", "formatted_list", "table", "bar_chart", "line_chart", "narrative_text", "alert_card"]
    narrative: str
    final_response: dict
```

### Agent Workflow (M1)
```
User Query (AR/EN)
  → IntentClassifierNode (GPT-4o-mini)
  → ClarificationNode (if params incomplete)
  → RouterNode → one of:
      - db_query_tool (financial/operational → PostgreSQL templates)
      - invoice_analysis_tool (invoice_analysis → invoice sub-pipeline)
      - tax_rag_tool (tax_reasoning → pgvector retrieval)
  → ValidationEnrichmentNode
  → OutputSelectorNode (8 output types)
  → NarrativeGeneratorNode (GPT-4o)
  → Response to User
```

### Invoice Sub-Pipeline (within M1)
```
invoice_analysis intent
  → InvoiceParamExtractorNode
  → InvoiceQueryBuilderNode (template or SQL)
  → InvoiceDBExecutionNode (READ-ONLY PostgreSQL)
  → InvoiceAnalysisNode (GPT-4o — pattern detection)
  → Output: Metric Card + Pattern Insights + Chart
```

### M1 Nodes (file locations)
| Node | File | Purpose |
|------|------|---------|
| IntentClassifierNode | agents/m1/nodes/intent_classifier_node.py | Classify intent, detect language |
| RouterNode | agents/m1/nodes/router_node.py | Route to correct tool |
| ClarificationNode | agents/m1/nodes/clarification_node.py | Ask for missing params |
| ValidationEnrichmentNode | agents/m1/nodes/validation_enrichment_node.py | Verify data completeness |
| OutputSelectorNode | agents/m1/nodes/output_selector_node.py | Choose output format |
| NarrativeGeneratorNode | agents/m1/nodes/narrative_generator_node.py | GPT-4o text analysis |
| InvoiceParamExtractorNode | agents/m1/nodes/invoice/invoice_param_extractor_node.py | Extract invoice params |
| InvoiceQueryBuilderNode | agents/m1/nodes/invoice/invoice_query_builder_node.py | Build invoice SQL |
| InvoiceDBExecutionNode | agents/m1/nodes/invoice/invoice_db_execution_node.py | Execute invoice query |
| InvoiceAnalysisNode | agents/m1/nodes/invoice/invoice_analysis_node.py | Pattern detection |

### M1 Tools (file locations)
| Tool | File | Purpose |
|------|------|---------|
| db_query_tool | agents/m1/tools/db_query_tool.py | 10 SQL templates + validation |
| invoice_analysis_tool | agents/m1/tools/invoice_analysis_tool.py | Invoice-specific queries |
| tax_rag_tool | agents/m1/tools/tax_rag_tool.py | pgvector RAG for tax rules |

### M1 Use Case Groups
1. **Financial Intelligence** — revenue reports, aging analysis, product performance, executive summaries
2. **Operational Intelligence** — order status, sales trends, anomaly detection
3. **Invoice Intelligence** — invoice analysis from DB (NO OCR, NO PDF), batch pattern detection
4. **Tax Reasoning (limited)** — RAG-based, always includes disclaimer

### M1 Output Format Decision Logic
```
row=1, col=1           → Direct Text / Metric Card
has_time_column        → Line Chart + Narrative
intent=comparison      → Bar Chart (≤12 items) or Table
row>5 AND col>2        → Sortable Table
intent=explanation     → Narrative Text only
anomaly_detected       → Alert Card (colored) + explanation + recommendation
```

### M1 Database Requirements
Tables: `clients, invoices, invoice_items, orders, products, transactions, payments, vendors`
- Read-Only DB user (SELECT only — mandatory security layer)
- pgvector extension enabled (for Tax RAG)
- Mock data: realistic, internally consistent (not random)

### M1 10 SQL Templates (Sprint 2)
1. Revenue for a time period
2. Product/category performance vs. prior period
3. Late-paying customers — Aging Buckets (30/60/90+ days)
4. Vendor invoices (period / amount / status)
5. Total VAT for a period
6. Top/Bottom N customers or products
7. Expense anomaly detection (vs. average → triggers Alert)
8. Sales performance time series (for Line Chart)
9. Product category revenue comparison
10. Executive summary (sales + expenses + net for period)

---

## M3 — Customer Support Agent

### Purpose
Understand a customer's issue, fetch their complete data from ERP in seconds, and generate an accurate response — while maintaining a human review checkpoint for sensitive cases.

### LangGraph State Schema (M3)
```python
class M3State(TypedDict):
    customer_identifier: dict  # { type: "order_id"|"invoice_id"|"customer_id", value: str }
    issue_description: str
    issue_type: Literal["status_inquiry", "billing_dispute", "shipping_issue", "refund_request", "general_complaint"]
    fetched_data: dict  # { invoice, order, shipping, history }
    data_completeness: float  # 0.0 → 1.0
    confidence_score: float
    draft_response: str
    review_required: bool
    escalation_needed: bool
    final_response: str
```

### Agent Workflow (M3)
```
Customer Input (issue + identifier)
  → InputParserNode (GPT-4o-mini) — extract identifier_type, identifier_value, issue_description
  → DataFetcherNode — fetch from 4 sources:
      - invoice_data: REAL from PostgreSQL
      - order_status: MOCK data
      - shipping_status: MOCK data
      - customer_history: MOCK data
  → DataCompletenessCheckNode — calculate data_completeness score
  → IssueClassifierNode (GPT-4o-mini) — classify issue_type + priority
  → ContextBuilderNode — merge all data into structured context for LLM
  → ResponseGeneratorNode (GPT-4o) — generate draft_response + confidence_score
  → HumanReviewGateNode — decide: mandatory review / optional / escalate
  → Final Response to Customer
```

### M3 Human Review Gate Logic
| Condition | Decision |
|-----------|----------|
| issue_type == billing_dispute | review_required = True (mandatory) |
| issue_type == refund_request | review_required = True (mandatory) |
| confidence_score < 0.70 | review_required = True (mandatory) |
| escalation_needed == True | Skip review → direct escalation |
| issue_type == status_inquiry | review_required = False (optional, configurable) |

### M3 Nodes (file locations)
| Node | File | Purpose |
|------|------|---------|
| InputParserNode | agents/m3/nodes/input_parser_node.py | Extract identifier + issue from free text |
| DataFetcherNode | agents/m3/nodes/data_fetcher_node.py | Fetch from 4 sources |
| DataCompletenessCheckNode | agents/m3/nodes/data_completeness_node.py | Score data completeness |
| IssueClassifierNode | agents/m3/nodes/issue_classifier_node.py | Classify issue type + priority |
| ContextBuilderNode | agents/m3/nodes/context_builder_node.py | Merge data into LLM context |
| ResponseGeneratorNode | agents/m3/nodes/response_generator_node.py | Generate draft + confidence score |
| HumanReviewGateNode | agents/m3/nodes/human_review_node.py | Route: auto-send / review / escalate |

### M3 Tools (file locations)
| Tool | File | Purpose |
|------|------|---------|
| invoice_fetcher_tool | agents/m3/tools/invoice_fetcher_tool.py | Real invoice lookup from PostgreSQL |
| mock_data_tool | agents/m3/tools/mock_data_tool.py | Mock order/shipping/history lookup |

### M3 Mock Data Tables (Sprint 0)
```sql
order_status:     (order_id, customer_id, status, created_at, estimated_delivery, items)
shipping:         (tracking_id, order_id, status, carrier, location, last_update)
customer_history: (customer_id, interaction_type, issue_type, resolution, date)
```
**Critical:** customer_id must be consistent across all mock tables and real invoice data.

### M3 Graceful Degradation
| Data State | Response Strategy |
|------------|-------------------|
| Complete (1.0) | Full detailed response |
| Partial (0.5) | Available data + "Support team will contact you within 24h for [missing info]" |
| None (0.0) | "Could not find [identifier]. Please verify the number or contact support at [channel]" |

### M3 Confidence Indicator (internal — shown to employee, not customer)
- confidence >= 0.8 → 🟢 High
- 0.5 ≤ confidence < 0.8 → 🟡 Medium
- confidence < 0.5 → 🔴 Low

---

## Shared Services (between M1 and M3)

| Service | File | Purpose |
|---------|------|---------|
| LLM Client | agents/shared/llm_client.py | Single GPT-4o + GPT-4o-mini instance for all modules |
| Language Tools | agents/shared/language_tools.py | AR/EN detection and handling |
| Formatting Tools | agents/shared/formatting_tools.py | Shared output formatting utilities |
| Schema Registry | agents/shared/schema_registry.yaml | Shared schema definitions |
| JWT Auth | backend/core/auth.py | Authentication layer |
| DB Pool | backend/core/database.py | SQLAlchemy async PostgreSQL pool |
| Logging | backend/core/logging.py | Observability for all tool + LLM calls |
| Error Handler | backend/middleware/error_handler.py | Convert technical errors to user messages |
| Audit Service | backend/services/audit_service.py | Audit trail for all agent decisions |
| Session Service | backend/services/session_service.py | User session management |
| Human Review Service | backend/services/human_review_service.py | M3 human-in-the-loop coordination |

---

## Tech Stack Decisions

| Layer | Technology | Reason |
|-------|-----------|--------|
| Frontend | React + TypeScript | Flexibility, TypeScript prevents runtime errors |
| UI Components | shadcn/ui | Enterprise-grade appearance, fully customizable |
| Charts | Apache ECharts | Richer than Recharts for complex visualizations, Arabic support |
| Backend | FastAPI (Python) | Native LangGraph/LangChain integration, async support |
| Agent Orchestration | LangGraph + LangChain | Best for stateful agentic flows with human-in-the-loop |
| Primary Database | PostgreSQL | Relational strength + JSON support + transaction safety |
| Vector Search | pgvector extension | Unified relational + vector in one DB — simpler deployment |
| LLM Complex Tasks | GPT-4o | Best multilingual + reasoning |
| LLM Simple Tasks | GPT-4o-mini | Faster, cheaper for classification and routine responses |
| Embeddings | text-embedding-3-small | Low cost + excellent quality |
| Auth | python-jose (JWT) | Simple, sufficient for MVP |

### LLM Usage Strategy
- **GPT-4o:** Deep analysis, Narrative Generation, Tax Reasoning, complex queries
- **GPT-4o-mini:** Intent Classification, Issue Classification, simple status responses

---

## Critical Architecture Rules

1. **Read-Only DB** — M1 agent ONLY has SELECT permission on PostgreSQL. No INSERT/UPDATE/DELETE.
2. **No OCR** — Invoice data comes from DB tables, not PDF files. `ocr_agent_node.py` is archived.
3. **No Odoo** — Integration is with PostgreSQL directly, not Odoo JSON-RPC. `odoo_client.py` is archived.
4. **Single LLM Client** — One instance shared across all modules. See `agents/shared/llm_client.py`.
5. **Human Review is mandatory** for billing disputes, refund requests, and low-confidence responses.
6. **M2 is deferred** — All M2 files are in `agents/archive/m2/` and `backend/archive/`. Do not implement.
7. **pgvector must be enabled** on PostgreSQL from Sprint 0 — required for Tax RAG in Sprint 4.

---

## Repository Structure (Post-Migration)

```
agents/
├── m1/           # AI ERP Intelligence Agent (implement now)
├── m3/           # Customer Support Agent (implement now)
├── shared/       # Shared LLM client, language tools, formatting
├── archive/      # M2 (deferred) + legacy files (OCR, Odoo, old graphs)
├── registry/     # LangGraph graph registry
└── tests/        # Agent tests

backend/
├── api/v1/       # m1_query.py, m3_support.py, auth.py, admin.py, reports.py
├── core/         # auth, config, database, logging
├── services/     # llm_client, m1/m3 orchestrators, audit, session, human_review
├── models/       # user, session, audit_log, confirmation_token, m3_case
├── repositories/ # users, sessions, audit_logs
├── schemas/      # m1_query, m1_response, m3_support, auth, audit
├── middleware/   # error_handler, request_id, timing
├── dependencies/ # auth, database, services
└── archive/      # Odoo-centric, M2, legacy backend files

frontend/
├── app/m1/       # M1 chat interface
├── app/m3/       # M3 customer support interface
├── app/dashboard/# Main dashboard
├── components/m1/# M1 output renderers (table, chart, card, alert, narrative)
├── components/m3/# M3 interfaces (customer input, human review)
├── components/chat/    # Shared chat components
├── components/ui/      # Shared UI primitives
├── components/layout/  # Navigation, header, sidebar
├── hooks/        # useAuth, useM1Query, useM3Support, useWebSocket
├── types/        # auth, m1, m3
└── archive/      # procurement (M2), old analytics types

database/
├── migrations/   # Schema migrations
├── models/       # SQLAlchemy models
└── seeds/        # Mock data seeders (M1 ERP data + M3 mock tables)
```

---

## Implementation Priority Order

1. **Sprint 0 (M1)** — DB schema + shared services + infrastructure
2. **Sprint 1 (M1)** — LangGraph skeleton + Intent Classifier
3. **Sprint 2 (M1)** — 10 SQL Templates + Query Builder
4. **Sprint 0 (M3)** — Mock data tables (can run in parallel with M1 Sprint 1-2)
5. **Sprint 3 (M1)** — Invoice Analysis Tool
6. **Sprint 4 (M1)** — Tax RAG
7. **Sprint 1-2 (M3)** — M3 agent skeleton
8. **Sprint 5 (M1)** — Output Selector + Narrative Generator
9. **Sprint 3-4 (M3)** — Response Generator + Human Review Gate
10. **Sprint 6 (M1) + Sprint 5-6 (M3)** — Frontend + Integration + Demo Scenarios

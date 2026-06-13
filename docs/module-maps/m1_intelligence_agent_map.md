# M1 — AI ERP Intelligence Agent: Module Map

> Quick reference for developers working on M1. All file locations post-migration.
> Read docs/architecture/erp_architecture_memory.md §M1 for full context.

---

## Sprint 0 — Files to Create/Configure (Infrastructure)

| Task | File Location | Notes |
|------|--------------|-------|
| DB Schema (clients, invoices, etc.) | database/migrations/ | 8 tables — see Sprint 0 in M1_Sprints.md |
| Read-Only DB User | database/migrations/ | SELECT-only on PostgreSQL |
| pgvector Extension | database/migrations/ | Required for Sprint 4 Tax RAG |
| Mock Data Seeder | database/seeds/ | Realistic, internally consistent |
| .env Configuration | .env.example → .env | API keys, DB URL, pgvector settings |

---

## LangGraph Graph

| File | Status | Implements |
|------|--------|-----------|
| agents/m1/graphs/m1_graph.py | PLACEHOLDER | Full LangGraph StateGraph — wire all nodes |

---

## M1 State Schema

| File | Status | Content |
|------|--------|---------|
| agents/m1/schemas/m1_state.py | MOVED (was copilot_state.py) | Update with M1 TypedDict per blueprint §2.5 |

Fields required:
```python
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

---

## M1 Nodes

| Node | File | Status | LLM | Sprint |
|------|------|--------|-----|--------|
| IntentClassifierNode | agents/m1/nodes/intent_classifier_node.py | MOVED (was orchestrator_node.py) | GPT-4o-mini | 1 |
| RouterNode | agents/m1/nodes/router_node.py | MOVED (was analytics_supervisor_node.py) | None | 1 |
| ClarificationNode | agents/m1/nodes/clarification_node.py | PLACEHOLDER | GPT-4o-mini | 1 |
| ValidationEnrichmentNode | agents/m1/nodes/validation_enrichment_node.py | MOVED (was kpi_computation_node.py) | None | 1 |
| OutputSelectorNode | agents/m1/nodes/output_selector_node.py | MOVED (was visualization_node.py) | None | 5 |
| NarrativeGeneratorNode | agents/m1/nodes/narrative_generator_node.py | MOVED (was insight_generation_node.py) | GPT-4o | 5 |

### Invoice Sub-Pipeline Nodes

| Node | File | Status | LLM | Sprint |
|------|------|--------|-----|--------|
| InvoiceParamExtractorNode | agents/m1/nodes/invoice/invoice_param_extractor_node.py | PLACEHOLDER | GPT-4o-mini | 3 |
| InvoiceQueryBuilderNode | agents/m1/nodes/invoice/invoice_query_builder_node.py | PLACEHOLDER | None | 3 |
| InvoiceDBExecutionNode | agents/m1/nodes/invoice/invoice_db_execution_node.py | PLACEHOLDER | None | 3 |
| InvoiceAnalysisNode | agents/m1/nodes/invoice/invoice_analysis_node.py | PLACEHOLDER | GPT-4o | 3 |

---

## M1 Tools

| Tool | File | Status | Sprint |
|------|------|--------|--------|
| db_query_tool | agents/m1/tools/db_query_tool.py | MOVED (was analytics_tools.py) | 2 |
| invoice_analysis_tool | agents/m1/tools/invoice_analysis_tool.py | PLACEHOLDER | 3 |
| tax_rag_tool | agents/m1/tools/tax_rag_tool.py | PLACEHOLDER | 4 |

### db_query_tool — 10 Required SQL Templates (Sprint 2)
1. Revenue for time period
2. Product/category performance vs. prior period
3. Late-paying customers — Aging Buckets (30/60/90+)
4. Vendor invoices (period / amount / status)
5. Total VAT for period
6. Top/Bottom N customers or products
7. Expense anomaly detection (vs. average → Alert trigger)
8. Sales performance time series (Line Chart data)
9. Product category revenue comparison (Bar Chart data)
10. Executive summary (sales + expenses + net)

---

## M1 Backend Files

| File | Status | Purpose |
|------|--------|---------|
| backend/api/v1/m1_query.py | RENAMED (was copilot.py) | POST /query endpoint |
| backend/api/v1/reports.py | KEPT | Report output endpoint |
| backend/services/m1_orchestrator.py | PLACEHOLDER | Invokes m1_graph |
| backend/services/m1_response_service.py | RENAMED (was report_service.py) | Format M1 response |
| backend/services/query_template_service.py | RENAMED (was schema_registry.py) | SQL template registry |
| backend/services/rag_service.py | PLACEHOLDER | pgvector RAG for tax |
| backend/services/llm_client.py | PLACEHOLDER | Shared GPT-4o instance |
| backend/schemas/m1_query.py | RENAMED (was chat.py) | Request/response Pydantic models |
| backend/schemas/m1_response.py | PLACEHOLDER | Output format schema |

---

## M1 Frontend Files

| File | Status | Purpose |
|------|--------|---------|
| frontend/app/m1/page.tsx | PLACEHOLDER | M1 chat interface page |
| frontend/components/m1/OutputRenderer.tsx | PLACEHOLDER | Smart output format router |
| frontend/components/m1/MetricCard.tsx | PLACEHOLDER | KPI display (scalar output) |
| frontend/components/m1/SortableTable.tsx | PLACEHOLDER | Large dataset display |
| frontend/components/m1/LineChart.tsx | PLACEHOLDER | Time series (Apache ECharts) |
| frontend/components/m1/BarChart.tsx | PLACEHOLDER | Category comparison |
| frontend/components/m1/AlertCard.tsx | PLACEHOLDER | Anomaly alert display |
| frontend/components/m1/NarrativeText.tsx | PLACEHOLDER | AI narrative analysis |
| frontend/components/m1/output/ | MOVED (was analytics/) | Analytics chart components (refactor to use ECharts) |
| frontend/components/chat/ | KEPT | Chat UI — refactor for bilingual M1 |
| frontend/hooks/useM1Query.ts | RENAMED (was useChat.ts) | M1 query state management |
| frontend/types/m1.ts | RENAMED (was chat.ts) | M1 TypeScript types |

---

## M1 Demo Scenarios (Sprint 6)

| # | Query | Expected Output |
|---|-------|----------------|
| 1 | "إيه أداء المبيعات في الربع الثاني مقارنة بالأول؟" | Line Chart + Narrative |
| 2 | "مين العملاء المتأخرين في السداد أكتر من 30 يوم؟" | Aging Bucket Table |
| 3 | "حللّي فواتير الموردين في الربع الأول" | Pattern Detection + Metric Card |
| 4 | "فاتورتي بـ 50,000 جنيه، القيمة المضافة إيه؟" | Narrative + Legal Reference |
| 5 | Automatic anomaly: 340% increase in maintenance | Alert Card (auto-triggered) |

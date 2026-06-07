
---

## 10. Agent Definitions

### 10.1 Module 1 Agents

---

#### AGENT-1-01: Copilot Orchestrator

| Field | Detail |
|---|---|
| **Agent ID** | AGENT-1-01 |
| **Name** | Copilot Orchestrator |
| **Module** | Module 1 |
| **Role in Framework** | Supervisor / Router |
| **LLM Model** | GPT-4o |

**Purpose:**
The central routing and coordination agent for Module 1. Receives all user messages, classifies intent, manages session context, and dispatches tasks to the appropriate specialized agent or agent pipeline. The Orchestrator never performs ERP operations itself.

**Responsibilities:**
- Receive and pre-process all user input (language detection, sanitization)
- Classify user intent into defined intent categories (see FR-1-02)
- Maintain and update session context in Redis
- Route tasks to: ERP Query Agent, ERP Action Agent, Analytics Supervisor
- Receive outputs from downstream agents and assemble the final response
- Handle clarification requests when intent confidence is low
- Enforce the confirmation gate requirement before passing to ERP Action Agent

**Inputs:**
- User message (text string, max 2,000 chars)
- Session context object (from Redis)
- System configuration (tool list, routing rules)

**Outputs:**
- Routed task specification to the appropriate agent
- Direct response for `system.greeting` and `system.unknown` intents
- Final assembled user response

**Tools:**
- `detect_language(text)` → returns ISO 639-1 language code
- `classify_intent(text, context)` → returns intent code + confidence score + extracted entities
- `get_session_context(session_id)` → retrieves context from Redis
- `update_session_context(session_id, update)` → updates context in Redis
- `route_to_agent(agent_id, task_payload)` → dispatches task to sub-agent

**Memory Requirements:**
- Session context window: last 10 turns, stored in Redis
- No cross-session memory in MVP

**Trigger Conditions:**
- Every user message to the Copilot interface
- System initialization (on session start, creates empty context)

**Failure Handling:**
- If intent classification fails: ask user to rephrase
- If routing fails: return generic error, log failure in LangSmith
- If context retrieval fails: restart with empty context, inform user session was reset
- Maximum retries: 1 per failure type before returning user-facing error

---

#### AGENT-1-02: ERP Query Agent

| Field | Detail |
|---|---|
| **Agent ID** | AGENT-1-02 |
| **Name** | ERP Query Agent |
| **Module** | Module 1 |
| **Role in Framework** | Executor (Read-Only) |
| **LLM Model** | GPT-4o-mini (simple queries) / GPT-4o (complex, multi-model queries) |

**Purpose:**
Executes read-only queries against Odoo ERP. Translates natural language data requests (enriched with structured intent from the Orchestrator) into Odoo JSON-RPC calls, retrieves data, and formats results for human consumption.

**Responsibilities:**
- Resolve entity references (e.g., "Al-Mustaqbal" → `res.partner` ID 42)
- Construct Odoo domain filters from extracted query parameters
- Execute Odoo API read calls (search_read, read, search)
- Handle pagination (default limit 50 records per call)
- Format raw Odoo data into structured, human-readable output
- Return both data payload and display-formatted response

**Inputs:**
- Structured task from Orchestrator: `{intent, entities, filters, time_range, language}`
- Odoo schema registry (YAML — maps concepts to Odoo model/field paths)

**Outputs:**
- Raw data payload (JSON) for downstream processing
- Formatted display response (table, list, or summary, in user's language)
- Record count and pagination metadata

**Tools:**
- `resolve_entity(name, model_type)` → resolves natural language name to Odoo record ID
- `build_domain_filter(entities, time_range, filters)` → constructs Odoo domain list
- `odoo_search_read(model, domain, fields, limit, offset)` → executes Odoo read operation
- `format_data_response(raw_data, format_type, language)` → formats for display
- `lookup_schema(concept)` → retrieves field paths from schema registry

**Memory Requirements:**
- Stateless between calls (context provided by Orchestrator)
- Schema registry loaded at startup from YAML file

**Trigger Conditions:**
- Routed from Orchestrator on `query.data` or `action.search` intents

**Failure Handling:**
- Entity resolution failure: return "I could not find [entity] in the system. Please check the name and try again."
- Odoo API error: retry once, then return graceful error
- Empty result set: return "No records found matching your criteria. Try adjusting your filters."

---

#### AGENT-1-03: ERP Action Agent

| Field | Detail |
|---|---|
| **Agent ID** | AGENT-1-03 |
| **Name** | ERP Action Agent |
| **Module** | Module 1 |
| **Role in Framework** | Executor (Write — Gated) |
| **LLM Model** | GPT-4o |

**Purpose:**
Executes write operations in Odoo. NEVER executes an operation without first presenting the Confirmation Gate to the user and receiving explicit approval. This agent is responsible for the highest-stakes interactions with the ERP.

**Responsibilities:**
- Extract all required fields for the requested action
- Ask follow-up questions for any missing required fields
- Validate all entity references against Odoo before building the confirmation
- Construct the human-readable Confirmation Summary (see FR-1-05)
- On user approval: execute Odoo write operation and confirm success
- On user rejection: acknowledge, discard the draft, log the event
- Write all actions to the audit log

**Inputs:**
- Structured action task from Orchestrator: `{action_type, entities, parameters, language}`
- User confirmation response (approve / reject / modify)

**Outputs:**
- Confirmation Summary panel (pre-execution)
- Post-execution confirmation message
- Audit log entry
- Updated session context (with reference to the created/modified record)

**Tools:**
- `resolve_entity(name, model_type)` → same as ERP Query Agent
- `validate_action_fields(action_type, fields)` → validates all required fields present and valid
- `build_confirmation_summary(action_type, fields, language)` → generates human-readable confirmation panel
- `odoo_create(model, values)` → creates a new record in Odoo
- `odoo_write(model, record_id, values)` → updates an existing record
- `odoo_action(model, record_id, action_name)` → executes a workflow action (e.g., confirm order)
- `write_audit_log(entry)` → writes immutable audit log entry

**Memory Requirements:**
- Stateless between calls; confirmation state held in session context during the approval flow

**Trigger Conditions:**
- Routed from Orchestrator on `action.create` or `action.update` intents
- Never triggered directly by user; always via Orchestrator

**Failure Handling:**
- If required fields are missing: ask user for clarification before building confirmation
- If entity validation fails: return specific error (e.g., "Customer 'ABC Corp' was not found in Odoo")
- If Odoo write fails after user confirmation: return error, log failure, inform user the action did not complete and to try again or contact support
- NEVER mark an action as successful unless the Odoo API confirms the write

---

#### AGENT-1-04: Analytics Supervisor

| Field | Detail |
|---|---|
| **Agent ID** | AGENT-1-04 |
| **Name** | Analytics Supervisor |
| **Module** | Module 1 |
| **Role in Framework** | Supervisor (Analytics Sub-System) |
| **LLM Model** | GPT-4o |

**Purpose:**
Orchestrates the four-agent analytics pipeline. Receives analytics requests from the Copilot Orchestrator, decomposes them into tasks for each sub-agent, coordinates the pipeline (sequential with partial parallelism), assembles the final report, and returns it to the Orchestrator.

**Responsibilities:**
- Parse analytics request into a structured analytics plan
- Define the scope: time range, metrics, dimensions, output format
- Spawn and coordinate: Data Retrieval Agent, KPI Computation Agent, Visualization Agent, Insight Generation Agent
- Assemble outputs from all sub-agents into a cohesive report
- Ensure report completeness before returning to Orchestrator
- Handle partial failures (e.g., if one sub-agent fails, assemble partial report and flag gap)

**Inputs:**
- Analytics task from Orchestrator: `{analytics_type, time_range, scope, language}`

**Analytics Types:**
- `executive_review` — full business performance summary
- `sales_performance` — sales KPIs and trends
- `inventory_status` — stock health overview
- `customer_analysis` — customer revenue and behavior analysis
- `product_performance` — product sales and inventory analysis

**Outputs:**
- Fully assembled report object: `{sections[], charts[], insights[], metadata}`

**Tools:**
- `create_analytics_plan(request)` → returns structured task list for sub-agents
- `orchestrate_pipeline(plan)` → runs sub-agents in defined sequence
- `assemble_report(data, kpis, charts, insights)` → compiles final report
- `validate_report_completeness(report)` → checks all required sections are present

**Trigger Conditions:**
- Routed from Copilot Orchestrator on `query.analytics` intent

**Failure Handling:**
- Sub-agent failure: log failure, continue with remaining sub-agents, flag missing section in report
- Total pipeline failure: return partial data with message "Analytics report incomplete. Some data could not be retrieved."

---

#### AGENT-1-05: Data Retrieval Agent (Analytics Sub-Agent)

| Field | Detail |
|---|---|
| **Agent ID** | AGENT-1-05 |
| **Name** | Data Retrieval Agent |
| **Module** | Module 1 — Analytics Sub-System |
| **Role in Framework** | Sub-Agent (Executor) |
| **LLM Model** | GPT-4o-mini |

**Purpose:**
Fetches all raw data from Odoo required to compute the analytics plan defined by the Analytics Supervisor. Acts as the data layer for the analytics pipeline — does computation but retrieves data efficiently.

**Responsibilities:**
- Execute Odoo queries for: sales data, invoice data, stock data, purchase data
- Apply time range and scope filters
- Return raw structured data (no formatting, no computation)
- Aggregate data at appropriate granularity (daily, weekly, monthly totals)

**Inputs:**
- Analytics plan from Supervisor: `{data_requirements[], time_range, filters}`

**Outputs:**
- Raw data payload: `{sales_data, invoice_data, stock_data, purchase_data}` — all as structured JSON

**Tools:**
- `odoo_search_read(model, domain, fields, limit)` — multiple calls per data type
- `aggregate_by_period(data, period)` — groups data by day/week/month

**Trigger Conditions:**
- Invoked by Analytics Supervisor as Step 1 of the pipeline

---

#### AGENT-1-06: KPI Computation Agent (Analytics Sub-Agent)

| Field | Detail |
|---|---|
| **Agent ID** | AGENT-1-06 |
| **Name** | KPI Computation Agent |
| **Module** | Module 1 — Analytics Sub-System |
| **Role in Framework** | Sub-Agent (Computation) |
| **LLM Model** | No LLM — Pure computation (Python functions) |

**Purpose:**
Computes all business KPIs from the raw data provided by the Data Retrieval Agent. This agent is deterministic and does NOT use an LLM — all computations are defined Python functions.

**Responsibilities:**
- Compute: total revenue, period-over-period growth, gross margin estimate
- Compute: top N customers by revenue, top N products by units and revenue
- Compute: inventory turnover rate, stock coverage days per product
- Compute: procurement spend totals, pending PO value
- Return structured KPI object

**KPI Library:**

| KPI | Formula |
|---|---|
| Total Revenue | SUM(sale.order.amount_total) where state = 'sale' or 'done' |
| Revenue Growth | (Current Period Revenue - Prior Period Revenue) / Prior Period Revenue × 100 |
| Top Customers | GROUP BY partner_id, SUM(amount_total) ORDER BY DESC LIMIT N |
| Top Products | GROUP BY product_id, SUM(qty) and SUM(revenue) |
| Stock Coverage Days | current_stock / avg_daily_consumption |
| Inventory Turnover | COGS / Average Inventory Value (simplified) |
| Procurement Spend | SUM(purchase.order.amount_total) where state = 'purchase' |

**Inputs:**
- Raw data payload from Data Retrieval Agent

**Outputs:**
- Structured KPI object: `{kpis: {name, value, unit, prior_period_value, change_pct}[]}`

**Tools:**
- No external tools. Pure Python computation using Pandas.

**Trigger Conditions:**
- Invoked by Analytics Supervisor as Step 2, after Data Retrieval completes

---

#### AGENT-1-07: Visualization Agent (Analytics Sub-Agent)

| Field | Detail |
|---|---|
| **Agent ID** | AGENT-1-07 |
| **Name** | Visualization Agent |
| **Module** | Module 1 — Analytics Sub-System |
| **Role in Framework** | Sub-Agent (Chart Configuration) |
| **LLM Model** | GPT-4o-mini |

**Purpose:**
Selects the most appropriate chart type for each KPI or dataset and generates the chart configuration objects (JSON) that the frontend renders using Recharts.

**Chart Selection Logic:**

| Data Type | Chart Type Selected |
|---|---|
| Trend over time (single metric) | Line chart |
| Ranked comparison (top customers, products) | Horizontal bar chart |
| Composition (product mix, revenue by category) | Donut/Pie chart |
| Multi-metric comparison | Grouped bar chart |
| Single value KPI with trend | KPI card with sparkline |
| Tabular data with no clear visual pattern | Styled data table |

**Inputs:**
- KPI object from KPI Computation Agent
- Report type (determines which charts are mandatory vs. optional)

**Outputs:**
- Chart configuration array: `{chart_type, title, data, x_axis, y_axis, colors, labels}`
- These configs are passed directly to Recharts components in the frontend

**Trigger Conditions:**
- Invoked by Analytics Supervisor as Step 3, after KPI Computation completes

---

#### AGENT-1-08: Insight Generation Agent (Analytics Sub-Agent)

| Field | Detail |
|---|---|
| **Agent ID** | AGENT-1-08 |
| **Name** | Insight Generation Agent |
| **Module** | Module 1 — Analytics Sub-System |
| **Role in Framework** | Sub-Agent (Narrative Generation) |
| **LLM Model** | GPT-4o |

**Purpose:**
Generates human-readable business narrative insights from the computed KPIs. Produces an executive summary and a set of key insights (observations, anomalies, recommendations).

**Responsibilities:**
- Write a 2–3 sentence executive summary
- Identify 3–5 key business insights from the KPI data
- Highlight positive trends and areas of concern
- Tailor language to the user's language (Arabic or English)
- Ground every insight in the actual computed KPI values — no fabrication

**Strict Grounding Rule:**
The Insight Generation Agent must be prompted to ONLY reference KPI values present in the input data. It must NOT introduce trend claims not supported by the data. If data is insufficient, it must say so.

**Inputs:**
- KPI object from KPI Computation Agent
- Report type and time range
- User language preference

**Outputs:**
- Executive summary (string, 2–3 sentences)
- Key insights array: `{insight_text, insight_type (positive/concern/neutral), referenced_kpi}[]`

**Trigger Conditions:**
- Invoked by Analytics Supervisor as Step 4 (can run in parallel with Visualization Agent)

---

### 10.2 Module 2 Agents

---

#### AGENT-2-01: Procurement Orchestrator

| Field | Detail |
|---|---|
| **Agent ID** | AGENT-2-01 |
| **Name** | Procurement Orchestrator |
| **Module** | Module 2 |
| **Role in Framework** | Supervisor / Scheduler |
| **LLM Model** | GPT-4o |

**Purpose:**
Central coordinator for all Module 2 workflows. Manages the scheduled monitoring cycle, routes user-triggered procurement requests, and orchestrates the full procurement pipeline from detection to RFQ submission.

**Responsibilities:**
- Manage the scheduled inventory monitoring cycle (every 6 hours)
- Receive and route user-triggered procurement queries
- Coordinate the pipeline: Inventory Monitor → Demand Forecaster → Supplier Evaluator → RFQ Generator
- Manage the human approval workflow state
- Collect and present final procurement recommendations
- Trigger the OCR Agent when a PDF is uploaded

**Inputs:**
- Scheduled timer trigger (every 6 hours)
- User action trigger (from Procurement Dashboard)
- Uploaded PDF (for OCR pipeline)

**Outputs:**
- Procurement alerts (pushed to UI)
- Procurement Health Dashboard data
- RFQ draft packages for human review

**Tools:**
- `trigger_monitoring_cycle()` → initiates full inventory scan
- `get_alert_queue()` → retrieves pending alerts
- `route_to_agent(agent_id, payload)` → dispatches to sub-agents
- `assemble_procurement_package(alerts, forecasts, supplier_rankings, rfq_drafts)` → builds recommendation package

**Trigger Conditions:**
- Scheduled: every 6 hours (configurable via environment variable)
- On-demand: user clicks "Run Procurement Check" in dashboard
- Event-driven: user uploads supplier quote PDF

**Failure Handling:**
- If monitoring cycle fails: log error, push alert to admin panel, skip cycle and retry on next schedule
- If sub-agent fails: log error, produce partial report flagging incomplete section

---

#### AGENT-2-02: Inventory Monitor Agent

| Field | Detail |
|---|---|
| **Agent ID** | AGENT-2-02 |
| **Name** | Inventory Monitor Agent |
| **Module** | Module 2 |
| **Role in Framework** | Sub-Agent (Monitor) |
| **LLM Model** | No LLM — Rule-based with Python logic |

**Purpose:**
Scans the full product catalog, computes the risk state for every product, and identifies products requiring procurement action. A deterministic, rule-based agent.

**Responsibilities:**
- Retrieve current stock levels from Odoo `stock.quant`
- Retrieve reorder points from Odoo `product.template`
- Retrieve supplier lead times from Odoo supplier pricelist
- Compute current risk state per product (HEALTHY / WATCH / AT RISK / CRITICAL / STOCKOUT)
- Return list of products in AT RISK or CRITICAL state for further processing

**Inputs:**
- Trigger from Procurement Orchestrator

**Outputs:**
- `{product_id, product_name, current_stock, reorder_point, lead_time_days, risk_state, days_until_stockout_estimate}[]`

**Tools:**
- `odoo_search_read('stock.quant', ...)` → current stock by location
- `odoo_search_read('product.template', ...)` → reorder points
- `odoo_search_read('product.supplierinfo', ...)` → supplier lead times
- `compute_risk_state(stock, reorder_point, lead_time, avg_daily_consumption)` → returns risk state enum

---

#### AGENT-2-03: Demand Forecaster Agent

| Field | Detail |
|---|---|
| **Agent ID** | AGENT-2-03 |
| **Name** | Demand Forecaster Agent |
| **Module** | Module 2 |
| **Role in Framework** | Sub-Agent (Analytics) |
| **LLM Model** | No LLM — Statistical computation (Pandas + Statsmodels) |

**Purpose:**
Computes demand forecasts for at-risk products using historical sales and consumption data. Returns projected demand, recommended order quantities, and forecast confidence levels.

**Inputs:**
- List of at-risk products from Inventory Monitor Agent
- Historical window: 90 days (configurable)

**Outputs:**
- Per-product forecast: `{product_id, avg_daily_demand, 7_day_forecast, 30_day_forecast, recommended_order_qty, stockout_date, confidence_level}`

**Tools:**
- `odoo_search_read('sale.order.line', ...)` → historical sales data
- `compute_weighted_moving_average(data, window, weights)` → WMA calculation
- `compute_exponential_smoothing(data, alpha)` → ETS calculation
- `calculate_eoq(demand, holding_cost, order_cost)` → Economic Order Quantity
- `assess_forecast_confidence(data_points_available)` → returns HIGH/MEDIUM/LOW

---

#### AGENT-2-04: Supplier Evaluator Agent

| Field | Detail |
|---|---|
| **Agent ID** | AGENT-2-04 |
| **Name** | Supplier Evaluator Agent |
| **Module** | Module 2 |
| **Role in Framework** | Sub-Agent (Evaluation + Ranking) |
| **LLM Model** | GPT-4o-mini (for rationale generation) |

**Purpose:**
Evaluates and ranks suppliers for a given product based on historical purchase order data. Returns a ranked supplier list with scores, score breakdowns, and a recommendation rationale.

**Inputs:**
- Product ID(s) requiring procurement action
- Historical PO data from Odoo (fetched by agent)

**Outputs:**
- Per-product ranked supplier list: `{supplier_id, supplier_name, score, score_breakdown, recommendation_rationale, data_confidence}`

**Tools:**
- `odoo_search_read('purchase.order', ...)` → historical PO data
- `odoo_search_read('product.supplierinfo', ...)` → supplier catalog prices
- `compute_supplier_score(price_score, delivery_score, consistency_score, history_score)` → composite score
- `generate_recommendation_rationale(scores, language)` → LLM-generated rationale string

---

#### AGENT-2-05: OCR Agent

| Field | Detail |
|---|---|
| **Agent ID** | AGENT-2-05 |
| **Name** | OCR Agent |
| **Module** | Module 2 |
| **Role in Framework** | Sub-Agent (Document Processing) |
| **LLM Model** | GPT-4o Vision (for layout understanding) |

**Purpose:**
Processes uploaded supplier quotation PDFs using OCR and LLM vision capabilities to extract structured data for supplier comparison.

**Responsibilities:**
- Convert PDF pages to images
- Extract text using pytesseract or equivalent
- Use GPT-4o Vision to interpret layout and extract structured fields
- Return structured extraction with confidence scores
- Flag low-confidence extractions for human review

**Inputs:**
- Uploaded PDF file (base64 or file path)
- Target extraction schema (list of fields to extract)

**Outputs:**
- Extracted data: `{field_name, extracted_value, confidence_score, needs_review_flag}[]`

**Tools:**
- `convert_pdf_to_images(pdf_path)` → returns list of image objects
- `extract_text_ocr(image)` → returns raw text string
- `extract_structured_fields_vision(image, schema)` → GPT-4o Vision call
- `compute_field_confidence(extraction_result)` → returns confidence score

---

#### AGENT-2-06: RFQ Draft Generator

| Field | Detail |
|---|---|
| **Agent ID** | AGENT-2-06 |
| **Name** | RFQ Draft Generator |
| **Module** | Module 2 |
| **Role in Framework** | Sub-Agent (Document Creation — Gated) |
| **LLM Model** | GPT-4o-mini |

**Purpose:**
Generates complete, Odoo-ready RFQ and Purchase Order drafts for at-risk products. Assembles all required fields from upstream agents and presents drafts for human review.

**Responsibilities:**
- Assemble RFQ fields from: Inventory Monitor, Demand Forecaster, Supplier Evaluator outputs
- Generate an AI rationale note for each draft (why this product, why this quantity, why this supplier)
- Present draft package in the Procurement Review Panel for human approval
- On approval: execute Odoo `purchase.order` create call
- On rejection: discard draft, log event

**Inputs:**
- At-risk product list with forecasts (from Demand Forecaster)
- Supplier rankings (from Supplier Evaluator)

**Outputs:**
- Draft RFQ package: `{product, quantity, supplier, unit_price_estimate, expected_delivery, ai_rationale_note}`
- Post-approval: Odoo RFQ ID confirming successful creation

**Tools:**
- `assemble_rfq_draft(product, forecast, supplier_ranking)` → builds RFQ draft object
- `generate_rfq_rationale(product, forecast, supplier, language)` → LLM-generated rationale
- `odoo_create('purchase.order', rfq_values)` → creates RFQ in Odoo (POST-APPROVAL ONLY)
- `write_audit_log(entry)` → logs approval/rejection event

---

## 11. Agent Interaction Flows

### 11.1 Module 1 — Standard ERP Query Flow

```
User: "What are our top 5 customers this month?"
        ↓
[AGENT-1-01 Copilot Orchestrator]
  → detect_language() → EN
  → classify_intent() → query.data | confidence 0.95
  → extract_entities() → {metric: "top_customers", limit: 5, time_range: "this_month"}
  → route_to_agent(AGENT-1-02, task)
        ↓
[AGENT-1-02 ERP Query Agent]
  → lookup_schema("top customers") → res.partner + sale.order
  → build_domain_filter() → [('date_order', '>=', '2026-06-01')]
  → odoo_search_read('sale.order', domain, fields)
  → aggregate by partner_id, sum amount_total
  → format_data_response() → ranked table, EN
        ↓
[AGENT-1-01 Copilot Orchestrator]
  → receive formatted response
  → update_session_context() → entity="customers", time_range="this_month"
  → return response to UI
        ↓
User sees: Ranked table of top 5 customers with revenue totals
Agent Thinking panel shows: 3 steps taken, 1 Odoo API call, 0.8s data retrieval
```

---

### 11.2 Module 1 — Analytics Executive Review Flow

```
User: "Give me a business performance review for last quarter"
        ↓
[AGENT-1-01 Copilot Orchestrator]
  → classify_intent() → query.analytics | executive_review
  → extract time_range → last_quarter
  → route_to_agent(AGENT-1-04, analytics_task)
        ↓
[AGENT-1-04 Analytics Supervisor]
  → create_analytics_plan(executive_review, last_quarter)
  → Step 1: invoke AGENT-1-05 (Data Retrieval)
  → Step 2: invoke AGENT-1-06 (KPI Computation)
  → Steps 3+4 (parallel): invoke AGENT-1-07 (Visualization) + AGENT-1-08 (Insight Generation)
  → assemble_report()
        ↓
[AGENT-1-05 Data Retrieval Agent]
  → Fetches: sales, invoices, stock, purchases for Q period
  → Returns structured data payload
        ↓
[AGENT-1-06 KPI Computation Agent]
  → Computes: revenue, growth, top customers, top products, stock coverage
  → Returns KPI object
        ↓ (parallel execution)
[AGENT-1-07 Visualization Agent]          [AGENT-1-08 Insight Generation Agent]
  → Selects chart types per KPI             → Writes executive summary
  → Generates Recharts configs              → Generates 5 key insights
        ↓ (both complete)
[AGENT-1-04 Analytics Supervisor]
  → assembles full report object
  → returns to Orchestrator
        ↓
UI renders: Full report with KPI cards, 4 charts, narrative insights panel
Timeline: 15–25 seconds total
```

---

### 11.3 Module 1 — ERP Write Action Flow (with Confirmation Gate)

```
User: "Create a sales quotation for Al-Mustaqbal for 50 units of Product A and 20 units of Product B"
        ↓
[AGENT-1-01 Copilot Orchestrator]
  → classify_intent() → action.create | sales_quotation
  → extract entities: {customer: "Al-Mustaqbal", products: [{name: "Product A", qty: 50}, {name: "Product B", qty: 20}]}
  → check all required fields present → YES
  → route_to_agent(AGENT-1-03, action_task)
        ↓
[AGENT-1-03 ERP Action Agent]
  → resolve_entity("Al-Mustaqbal", "res.partner") → partner_id: 42
  → resolve_entity("Product A", "product.product") → product_id: 17, price: 25 EGP
  → resolve_entity("Product B", "product.product") → product_id: 31, price: 80 EGP
  → validate_action_fields() → PASS
  → build_confirmation_summary() → renders Confirmation Panel in UI
        ↓
UI shows Confirmation Panel to user (see FR-1-05 format)
USER MUST CLICK: [✅ Confirm & Execute] or [❌ Cancel]
        ↓ (if Confirmed)
[AGENT-1-03 ERP Action Agent]
  → odoo_create('sale.order', {partner_id: 42, order_line: [...]})
  → Odoo returns: sale.order ID 187
  → write_audit_log({action: "create_sale_order", record_id: 187, outcome: "success"})
  → return success message to Orchestrator
        ↓
User sees: "✅ Quotation SO-187 has been created in Odoo for Al-Mustaqbal. Total: 2,850 EGP."
        ↓ (if Cancelled)
[AGENT-1-03 ERP Action Agent]
  → write_audit_log({action: "create_sale_order", outcome: "cancelled_by_user"})
  → return cancellation acknowledgement
User sees: "Action cancelled. No changes were made to Odoo."
```

---

### 11.4 Module 2 — Proactive Procurement Pipeline Flow

```
[SCHEDULED TRIGGER — every 6 hours]
        ↓
[AGENT-2-01 Procurement Orchestrator]
  → trigger_monitoring_cycle()
  → invoke AGENT-2-02 (Inventory Monitor)
        ↓
[AGENT-2-02 Inventory Monitor Agent]
  → Scans 200 products in catalog
  → Identifies: Product X (CRITICAL), Product Y (AT RISK), Product Z (AT RISK)
  → Returns: risk_products[] with state and lead_time data
        ↓
[AGENT-2-01 Procurement Orchestrator]
  → Receives 3 at-risk products
  → Pushes alert to UI: "⚠️ 3 products require procurement attention"
  → invoke AGENT-2-03 (Demand Forecaster) for 3 products
        ↓
[AGENT-2-03 Demand Forecaster Agent]
  → Fetches 90 days sales history for each product
  → Computes forecasts + recommended order quantities
  → Returns forecast objects with confidence levels
        ↓
[AGENT-2-01 Procurement Orchestrator]
  → invoke AGENT-2-04 (Supplier Evaluator) for 3 products
        ↓
[AGENT-2-04 Supplier Evaluator Agent]
  → Fetches historical PO data for each product's suppliers
  → Scores and ranks suppliers per product
  → Returns ranked supplier lists with rationales
        ↓
[AGENT-2-01 Procurement Orchestrator]
  → invoke AGENT-2-06 (RFQ Draft Generator)
        ↓
[AGENT-2-06 RFQ Draft Generator]
  → Assembles 3 RFQ drafts (one per at-risk product)
  → Groups by supplier where possible (Product Y and Z same supplier → combined RFQ)
  → Returns 2 RFQ draft packages for review
        ↓
UI Procurement Dashboard updates:
  → Risk panel: 3 products flagged
  → Forecast panel: demand charts and stockout dates
  → Supplier comparison panel: ranked supplier tables
  → RFQ Review panel: 2 draft RFQs awaiting approval
        ↓
USER REVIEWS AND APPROVES/REJECTS EACH RFQ
        ↓ (on approval)
[AGENT-2-06 RFQ Draft Generator]
  → odoo_create('purchase.order', rfq_values) for each approved RFQ
  → write_audit_log() for each
        ↓
User sees: "✅ 2 RFQs created in Odoo: RFQ-045 (Supplier A), RFQ-046 (Supplier B)"
```

---

### 11.5 Escalation Logic

| Scenario | Escalation Action |
|---|---|
| Intent confidence < 0.70 | Orchestrator asks user to rephrase |
| Required action fields missing | ERP Action Agent asks follow-up questions |
| Entity resolution fails after 2 attempts | Agent returns error, suggests the user verify the record in Odoo |
| Analytics sub-agent fails | Analytics Supervisor delivers partial report with gap flagged |
| LLM API timeout | System returns "AI service temporarily unavailable. Please retry." |
| Odoo API error after 1 retry | Agent returns graceful error with support context |
| User rejects RFQ | Draft discarded, audit logged, Orchestrator asks "Would you like to adjust this recommendation?" |

---

## 12. User Stories

### Module 1 — ERP AI Copilot

**US-1-01**
As a Sales Representative,
I want to query customer order history in Arabic,
So that I can prepare for customer calls quickly without navigating Odoo manually.

**US-1-02**
As a Sales Representative,
I want the AI to maintain context within a conversation,
So that I can ask follow-up questions without restating the customer or product name.

**US-1-03**
As a Sales Representative,
I want to create a draft sales quotation using natural language,
So that I can generate quotations faster without navigating Odoo's order creation screens.

**US-1-04**
As a Sales Representative,
I want to review and confirm all AI-generated ERP actions before they are executed,
So that I have control over all changes made to the system.

**US-1-05**
As a Warehouse Supervisor,
I want to query current stock levels in Arabic using plain language,
So that I can get inventory information independently without calling IT.

**US-1-06**
As a Warehouse Supervisor,
I want to see stock alerts when inventory falls below reorder points,
So that I am informed proactively rather than discovering stockouts during fulfillment.

**US-1-07**
As an Operations Manager,
I want to generate a full business performance report with KPIs and charts on demand,
So that I can review operational performance without spending hours on manual data compilation.

**US-1-08**
As an Operations Manager,
I want the analytics report to compare current performance against the prior period,
So that I can identify trends and improvements without additional analysis.

**US-1-09**
As a CEO,
I want to ask for a business review in Arabic and receive a complete executive report,
So that I can make strategic decisions based on real-time data without needing analyst support.

**US-1-10**
As a CEO,
I want the system to show me key business insights, not just raw numbers,
So that I can quickly understand the most important business signals without interpreting charts myself.

**US-1-11**
As any user,
I want to see what steps the AI took to answer my question,
So that I can trust the output and understand where the data came from.

**US-1-12**
As any user,
I want all AI responses in my input language (Arabic or English),
So that I can work naturally without switching languages.

**US-1-13**
As an Operations Manager,
I want to query sales data for a specific customer segment or region,
So that I can analyze performance for specific business areas.

**US-1-14**
As a Sales Representative,
I want to see outstanding invoices for a customer during a conversation,
So that I can address payment status during client calls.

**US-1-15**
As any user,
I want the system to ask me to clarify my request when it is ambiguous,
So that I receive accurate information rather than a guess.

---

### Module 2 — Procurement Intelligence

**US-2-01**
As a Procurement Manager,
I want to receive automatic alerts when products are projected to reach zero stock before they can be restocked,
So that I can act before a stockout occurs rather than after.

**US-2-02**
As a Procurement Manager,
I want to see demand forecasts for at-risk products with confidence indicators,
So that I can make informed decisions about order quantities.

**US-2-03**
As a Procurement Manager,
I want the system to automatically generate RFQ drafts for at-risk products,
So that I can start the procurement process with minimal manual effort.

**US-2-04**
As a Procurement Manager,
I want to review, edit, and approve AI-generated RFQs before they are submitted to Odoo,
So that I retain full control over procurement decisions.

**US-2-05**
As a Procurement Manager,
I want to see a ranked list of suppliers for each at-risk product with scores and rationale,
So that I can select the best supplier based on objective criteria.

**US-2-06**
As a Procurement Manager,
I want to upload supplier quotation PDFs and have the system extract the key data automatically,
So that I can compare suppliers without manually transcribing quote details.

**US-2-07**
As a Procurement Manager,
I want to see a single Procurement Health Score for my portfolio,
So that I can quickly assess overall procurement risk without reviewing individual products.

**US-2-08**
As a Supply Chain Manager,
I want to see products grouped by risk state (Critical, At Risk, Watch, Healthy),
So that I can prioritize my attention on the highest-risk items first.

**US-2-09**
As a Procurement Manager,
I want rejected RFQ drafts to be logged with a reason,
So that there is a record of procurement decisions for compliance and review.

**US-2-10**
As a Procurement Manager,
I want to trigger a manual procurement check at any time,
So that I can get a fresh analysis when I expect inventory changes (e.g., after a large sale).

**US-2-11**
As a Procurement Manager,
I want to see which pending RFQs are already in Odoo for a given product,
So that I can avoid creating duplicate orders.

**US-2-12**
As a Supply Chain Manager,
I want to see the AI's rationale for every procurement recommendation,
So that I can assess whether the recommendation makes business sense before approving.

---

### Module 3 — Customer Support (Stretch)

**US-3-01**
As a Customer,
I want to query the status of my orders in Arabic or English,
So that I can get order updates without calling a support agent.

**US-3-02**
As a Customer,
I want to see my outstanding invoice balance when I ask about it,
So that I can reconcile my accounts without waiting for a manual response.

**US-3-03**
As a Support Manager,
I want unresolvable customer queries to be automatically flagged and summarized for human agents,
So that my team handles complex issues efficiently without redundant data gathering.

---

## 13. Acceptance Criteria

### AC-1-01: Bilingual NLP Interface

- **GIVEN** a user types a query in Arabic, **WHEN** submitted, **THEN** the system correctly identifies the language as Arabic within 500ms.
- **GIVEN** a user types a query in English, **WHEN** submitted, **THEN** the response is returned in English.
- **GIVEN** a user types a query in Arabic, **WHEN** the full response is returned, **THEN** all text, labels, and numbers in the response are in Arabic with RTL formatting applied.
- **GIVEN** a user submits a query in an unsupported language, **WHEN** processed, **THEN** the system returns a polite message in English explaining it supports only Arabic and English.
- **GIVEN** a test set of 20 Arabic business queries, **WHEN** processed, **THEN** intent is correctly classified for ≥ 18 of 20 queries (90% accuracy).

---

### AC-1-02: Intent Classification

- **GIVEN** the query "Show me our top customers this month," **WHEN** classified, **THEN** intent is `query.data` with entity `top_customers` and time range `current_month`.
- **GIVEN** the query "Create a quotation for Customer X," **WHEN** classified, **THEN** intent is `action.create` with entity type `sale.order`.
- **GIVEN** a query with intent confidence below 0.70, **WHEN** processed, **THEN** the system responds with a clarifying question and does NOT route to any agent.
- **GIVEN** a query with two intents ("show sales and create a report"), **WHEN** classified, **THEN** both intents are identified and sequenced appropriately.

---

### AC-1-03: ERP Data Query

- **GIVEN** the query "What is the current stock of Product X?", **WHEN** processed, **THEN** the response includes the exact quantity returned by Odoo's `stock.quant` for that product, matching the Odoo UI value.
- **GIVEN** a query returning more than 50 results, **WHEN** processed, **THEN** the system displays the top 50 and informs the user that more results are available.
- **GIVEN** a query with a relative date ("last month"), **WHEN** processed, **THEN** the correct absolute date range is used in the Odoo API call.
- **GIVEN** a query for a non-existent customer, **WHEN** processed, **THEN** the system returns "No record found for [name]" — not an error or empty response.

---

### AC-1-04: ERP Action Execution

- **GIVEN** a user requests to create a sales quotation with all required fields, **WHEN** processed, **THEN** a Confirmation Panel is displayed BEFORE any Odoo API write call is made.
- **GIVEN** a user requests an action with a missing required field (e.g., no product specified), **WHEN** processed, **THEN** the agent asks for the missing field before proceeding to the Confirmation Panel.
- **GIVEN** a user requests an action with a customer name that does not exist in Odoo, **WHEN** entity resolution runs, **THEN** the system returns an error and does NOT display a Confirmation Panel.

---

### AC-1-05: Human-in-the-Loop Confirmation

- **GIVEN** any write-intent action reaches the ERP Action Agent, **WHEN** the Confirmation Panel is displayed, **THEN** no Odoo write operation is executed until the user clicks "Confirm."
- **GIVEN** a user clicks "Cancel" on the Confirmation Panel, **WHEN** processed, **THEN** no Odoo record is created or modified, and the audit log contains a "cancelled_by_user" entry with timestamp.
- **GIVEN** a confirmed action results in a successful Odoo write, **WHEN** completed, **THEN** the response displays the created record ID (e.g., "SO-187 created") and the audit log contains a "success" entry.
- **GIVEN** an audit log query, **WHEN** run, **THEN** every write action and every cancellation from the session is present with timestamp, session ID, action type, entity, and outcome.

---

### AC-1-06: Multi-Agent Analytics

- **GIVEN** the query "Give me a business performance review for last month," **WHEN** processed, **THEN** the LangSmith trace shows ≥ 4 distinct agent invocations (Data Retrieval, KPI, Visualization, Insight Generation).
- **GIVEN** the analytics pipeline runs for an executive review, **WHEN** the report is returned, **THEN** it contains: an executive summary, at least 3 KPI metrics, at least 2 charts, and at least 3 key insights.
- **GIVEN** an analytics report is generated, **WHEN** KPI values are displayed, **THEN** each KPI value matches the value computable directly from the Odoo mock dataset (no fabricated numbers).
- **GIVEN** an analytics report is generated, **WHEN** the report is generated for a period with prior-period data available, **THEN** period-over-period comparison (delta %) is included for revenue.
- **GIVEN** the full analytics pipeline, **WHEN** run on the mock dataset, **THEN** total end-to-end time is ≤ 30 seconds.

---

### AC-1-07: Session Memory

- **GIVEN** a user queries "Show me Customer X's orders" followed by "What is their outstanding balance?", **WHEN** the second query is processed, **THEN** "their" resolves to Customer X without re-specification.
- **GIVEN** a session expires after 60 minutes of inactivity, **WHEN** the user sends a new message, **THEN** the system starts a new context and informs the user.
- **GIVEN** a conversation spanning 15+ turns, **WHEN** the context is passed to the LLM, **THEN** only the last 10 turns and system prompt are included (context truncation applied).

---

### AC-2-01: Inventory Health Monitoring

- **GIVEN** a product with current stock ≤ (lead_time_days × avg_daily_consumption), **WHEN** the monitoring cycle runs, **THEN** that product is classified as CRITICAL and an alert is pushed to the UI.
- **GIVEN** the monitoring cycle runs, **WHEN** complete, **THEN** all 200 mock products have been evaluated and assigned a risk state.
- **GIVEN** a product transitions from WATCH to AT RISK, **WHEN** detected, **THEN** a notification appears in the procurement dashboard within the current monitoring cycle.

---

### AC-2-02: Demand Forecasting

- **GIVEN** a product with 90+ days of sales history, **WHEN** a forecast is generated, **THEN** the confidence level is "HIGH" and a projected stockout date is included.
- **GIVEN** a product with fewer than 30 days of sales history, **WHEN** a forecast is generated, **THEN** the confidence level is "LOW" and the output explicitly states "Limited historical data — forecast accuracy may be reduced."
- **GIVEN** a recommended order quantity is generated, **WHEN** displayed to the user, **THEN** it accounts for the product's minimum order quantity (MOQ) from Odoo supplier pricelist if available.

---

### AC-2-04: RFQ Generation

- **GIVEN** 3 at-risk products are identified, **WHEN** the RFQ generation pipeline runs, **THEN** draft RFQ documents are displayed in the Procurement Review Panel BEFORE any Odoo write.
- **GIVEN** a user approves an RFQ draft, **WHEN** confirmed, **THEN** a `purchase.order` record in RFQ state is created in Odoo with the correct product, quantity, and supplier.
- **GIVEN** a user rejects an RFQ draft, **WHEN** confirmed, **THEN** no Odoo record is created and a "rejected" entry appears in the audit log.
- **GIVEN** two at-risk products share the same preferred supplier, **WHEN** RFQ drafts are generated, **THEN** the system presents the option to combine them into a single RFQ.

---

### AC-2-05: Supplier Evaluation

- **GIVEN** a product with ≥ 2 historical purchase orders per supplier, **WHEN** the supplier evaluation runs, **THEN** each supplier receives a score with a breakdown across all four criteria.
- **GIVEN** a supplier with fewer than 2 historical POs, **WHEN** evaluated, **THEN** they are flagged as "New Supplier — Limited Data" in the ranking.
- **GIVEN** a supplier evaluation is complete, **WHEN** displayed, **THEN** the top-ranked supplier is pre-selected in the RFQ draft but the user can change it.

---

### AC-2-06: OCR Processing

- **GIVEN** a user uploads a mock supplier quotation PDF, **WHEN** processed, **THEN** supplier name, unit price, and lead time are extracted with ≥ 80% accuracy on the mock document set.
- **GIVEN** a field is extracted with low confidence, **WHEN** displayed, **THEN** it is highlighted in the editable review table and the user is prompted to verify it.
- **GIVEN** a file exceeding 10MB is uploaded, **WHEN** attempted, **THEN** the system rejects it with a clear file size error message.

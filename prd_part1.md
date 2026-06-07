# ERP Agentic AI Layer
## Master Product Requirements Document (PRD)
### Version 1.0 | Status: Approved for Development | Classification: Internal

---

**Document Control**

| Field | Value |
|---|---|
| Document Type | Master Product Requirements Document |
| Version | 1.0 |
| Based On | Vision & Discovery Document v1.0 |
| Primary Author | Product & Architecture Team |
| Reviewers | Engineering Leads, Module Owners |
| Status | Ready for Architecture & Sprint Planning |

---

## Table of Contents

1. Product Overview
2. Business Goals
3. Product Objectives
4. Success Metrics
5. Stakeholders
6. User Personas
7. User Journey Maps
8. Detailed Functional Requirements
9. Detailed Non-Functional Requirements
10. Agent Definitions
11. Agent Interaction Flows
12. User Stories
13. Acceptance Criteria
14. MVP Definition
15. Data Requirements
16. API Requirements
17. UI Requirements
18. Security Requirements
19. Risk Register
20. Final MVP Recommendation

---

## 1. Product Overview

### 1.1 Product Name
**ERP Agentic AI Layer** — internally codenamed **AERIE** (Agentic ERP Intelligence Engine)

### 1.2 Product Summary
AERIE is an Agentic AI platform that sits on top of Odoo ERP and transforms how business users interact with enterprise data. It is not an ERP system. It is not a chatbot. It is an AI workforce — a collection of specialized, collaborating AI agents that understand business context, reason over ERP data, execute ERP actions, automate procurement workflows, and deliver business intelligence in natural language.

The platform is delivered as a web application supporting English and Arabic, integrated with Odoo via JSON-RPC, and built on a multi-agent architecture using LangGraph.

### 1.3 Product Scope

**In Scope:**
- Module 1: ERP AI Copilot — conversational ERP interface with multi-agent analytics
- Module 2: Procurement Intelligence Agent — autonomous procurement monitoring and automation
- Module 3: Customer Support Multi-Agent System — stretch goal only
- Odoo integration layer (read and write)
- Arabic and English NLP
- Web-based user interface
- Human-in-the-loop confirmation for all ERP write actions
- Mock business dataset for demonstration

**Out of Scope:**
- Building or modifying the Odoo ERP system itself
- Mobile application
- Real-time ERP event streaming (webhooks) — future scope
- Multi-ERP platform support — future scope
- Agent memory persistence across sessions — future scope
- Production deployment infrastructure (Kubernetes, CI/CD) — future scope

### 1.4 Target Deployment
- Single-tenant web application
- Docker Compose deployment
- Odoo Community Edition (local instance)
- Mock business data

---

## 2. Business Goals

| ID | Business Goal | Priority |
|---|---|---|
| BG-01 | Demonstrate that Agentic AI can replace manual, high-frequency ERP workflows | Critical |
| BG-02 | Prove that non-technical users can fully interact with an ERP system without ERP training | Critical |
| BG-03 | Reduce procurement cycle time by automating the detection-to-RFQ workflow | Critical |
| BG-04 | Deliver Arabic-first enterprise AI for the MENA market where no strong alternative exists | High |
| BG-05 | Establish a production-grade, extensible architecture that supports real enterprise deployments | High |
| BG-06 | Position the team as capable of building enterprise-grade Agentic AI systems | High |
| BG-07 | Demonstrate business intelligence generation without analyst involvement | High |
| BG-08 | Create a compelling, risk-managed demo that impresses judges, clients, and recruiters | Medium |

---

## 3. Product Objectives

### 3.1 Module 1 — ERP AI Copilot Objectives

| ID | Objective | Measurable Outcome |
|---|---|---|
| OBJ-1-01 | Enable natural language ERP querying | Any supported query answered in < 10 seconds |
| OBJ-1-02 | Enable Arabic-language interaction | ≥ 90% intent recognition accuracy on Arabic test set |
| OBJ-1-03 | Enable ERP action execution via natural language | Draft creation (SO, PO, quotation) with confirmation step |
| OBJ-1-04 | Deliver automated executive business reviews | Full KPI report with charts generated in < 30 seconds |
| OBJ-1-05 | Maintain conversational context within a session | Multi-turn queries with correct context retention |
| OBJ-1-06 | Demonstrate multi-agent analytics collaboration | Analytics Supervisor orchestrating ≥ 3 sub-agents visibly |

### 3.2 Module 2 — Procurement Intelligence Objectives

| ID | Objective | Measurable Outcome |
|---|---|---|
| OBJ-2-01 | Detect at-risk inventory proactively | Alert generated before stockout, not after |
| OBJ-2-02 | Automate demand forecasting | Forecast generated from 90 days of history with confidence level |
| OBJ-2-03 | Automate RFQ drafting | RFQ draft created in Odoo with zero manual input from user |
| OBJ-2-04 | Enable intelligent supplier comparison | Ranked supplier recommendation with scoring rationale |
| OBJ-2-05 | Process supplier quotes from PDF | Structured extraction from mock PDF quotes |
| OBJ-2-06 | Enforce human approval on all PO/RFQ creation | Zero Odoo write operations without explicit user confirmation |

---

## 4. Success Metrics

### 4.1 Technical Performance Metrics

| Metric | Target | Measurement Method |
|---|---|---|
| Simple ERP query response time | < 5 seconds end-to-end | Frontend timer on demo scenarios |
| Complex analytics report generation | < 30 seconds end-to-end | Frontend timer on executive review scenario |
| Arabic intent recognition accuracy | ≥ 90% | Tested against 20-query Arabic test set |
| Agent task completion rate | ≥ 95% (no loops/failures) | LangSmith trace success rate |
| ERP data accuracy | 100% match to Odoo ground truth | Manual verification on demo dataset |
| Zero unauthorized ERP writes | 100% confirmation gate enforcement | Audit log verification |

### 4.2 Demo Day Metrics

| Metric | Target |
|---|---|
| Primary demo scenarios completed without failure | 5 of 5 |
| Arabic demo included and functional | Mandatory |
| Multi-agent collaboration visible in UI | Mandatory |
| Business value narrative delivered per demo | Every scenario |
| Before/after time comparison stated | Every scenario |

### 4.3 Architectural Quality Metrics

| Metric | Target |
|---|---|
| All 10 critical requirements demonstrated | 10 of 10 |
| Agent reasoning chain visible to user | Yes |
| Human-in-the-loop gate enforced | Yes, on all write operations |
| System recoverable from agent failure | Yes, with graceful error message |

---

## 5. Stakeholders

### 5.1 Primary Stakeholders

| Role | Name / Type | Interest | Influence |
|---|---|---|---|
| Engineering Team | 6 AI Engineers | Building and delivering the system | Primary |
| Program Judges | Academic / Industry Evaluators | Assessing AI capability and business value | High |
| ERP Users (Represented) | Personas in Sections 6 | Using the system in demo scenarios | High |
| Technical Recruiters | Industry Observers | Evaluating team technical capability | Medium |
| Enterprise Clients (Prospective) | MENA SMB/Mid-Market | Potential future deployment clients | Medium |

### 5.2 Secondary Stakeholders

| Role | Interest |
|---|---|
| Odoo Community | Integration standards and API compatibility |
| OpenAI / Anthropic | API consumption and responsible AI usage |
| Academic Institution | Program deliverable quality |

---

## 6. User Personas

### P-01 — Nour Al-Hassan | Sales Representative

| Field | Detail |
|---|---|
| Age / Location | 28, Cairo |
| Role | Sales Representative |
| ERP Literacy | Intermediate — uses Odoo daily but avoids complex queries |
| Primary Language | Arabic (preferred), English (functional) |
| Key Frustration | Spends 45 minutes each morning navigating Odoo before customer calls |
| Core Need | Instant customer intelligence: order history, outstanding invoices, preferred products |
| AI Interaction Style | Chat-based, Arabic queries, expects fast concise answers |
| Value Driver | Spend 3 minutes preparing for calls, not 45 |

### P-02 — Khaled Al-Mansouri | Procurement Manager

| Field | Detail |
|---|---|
| Age / Location | 42, Riyadh |
| Role | Procurement Manager |
| ERP Literacy | Advanced — power user |
| Primary Language | Arabic (management) and English (ERP interface) |
| Key Frustration | Reactive procurement — discovers stockouts after they happen. Manual RFQ preparation takes hours. |
| Core Need | Proactive inventory alerts, auto-generated RFQs, intelligent supplier comparison |
| AI Interaction Style | Dashboard-centric with conversational override |
| Value Driver | Shift from firefighting to proactive procurement management |

### P-03 — Layla Farouk | Operations Manager

| Field | Detail |
|---|---|
| Age / Location | 36, Dubai |
| Role | Operations Manager |
| ERP Literacy | Intermediate |
| Primary Language | English (primary), Arabic (team communication) |
| Key Frustration | Spends half a day each Friday manually compiling executive reports from ERP data |
| Core Need | Automated, shareable weekly performance reports with KPIs and charts |
| AI Interaction Style | Structured reports and dashboards, minimal conversational interaction |
| Value Driver | Reclaim 4+ hours per week spent on manual reporting |

### P-04 — Ibrahim Saleh | CEO / Executive

| Field | Detail |
|---|---|
| Age / Location | 55, Cairo |
| Role | Chief Executive Officer |
| ERP Literacy | None — never logs into ERP |
| Primary Language | Arabic |
| Key Frustration | Makes strategic decisions on 2–3 day old data, filtered through managers |
| Core Need | Real-time business snapshot: revenue, costs, risks, pipeline — on demand |
| AI Interaction Style | Voice or simple text, expects clean visual outputs |
| Value Driver | Real-time business visibility without analyst dependency |

### P-05 — Yasmine Hassan | Warehouse Supervisor

| Field | Detail |
|---|---|
| Age / Location | 31, Alexandria |
| Role | Warehouse Supervisor |
| ERP Literacy | Low — uses ERP minimally, contacts IT for queries |
| Primary Language | Arabic |
| Key Frustration | Cannot run her own ERP queries; depends on IT or analysts for stock information |
| Core Need | Simple natural language stock queries, expiry alerts, movement history |
| AI Interaction Style | Simple chat in Arabic, expects plain-language answers |
| Value Driver | Self-sufficient ERP access without training |

---

## 7. User Journey Maps

### Journey 1 — Nour Prepares for a Customer Call

**Current State (Without AI):**
1. Log in to Odoo (2 min)
2. Navigate to Customers module, search for the customer (2 min)
3. Check open orders (2 min)
4. Navigate to Invoices, filter by customer, check outstanding amounts (3 min)
5. Navigate to Products, cross-reference purchase history (5 min)
6. Manually write notes (3 min)
→ Total: ~17 minutes per customer | Daily cost: 45–60 minutes across 3–4 customers

**Future State (With AERIE):**
1. Type in chat (Arabic): "أعطني ملخصاً عن العميل شركة المستقبل قبل اجتماعي معهم"
2. Copilot Orchestrator classifies intent → routes to ERP Query Agent
3. ERP Query Agent retrieves: open orders, invoice balances, purchase history, last contact date
4. Response Formatter generates Arabic Customer Intelligence Brief
5. User reviews brief in 2 minutes
→ Total: ~3 minutes | Time saved: 14+ minutes per customer

**Journey Emotional Arc:** Frustration → Clarity → Confidence

---

### Journey 2 — Khaled Manages Procurement Risk

**Current State (Without AI):**
1. Export inventory report from Odoo (10 min)
2. Open Excel, build pivot table, apply reorder logic (30 min)
3. Identify at-risk products (15 min)
4. Manually write RFQs (20 min per supplier)
5. Email suppliers, wait for responses (1–3 days)
6. Manually compare responses (1 hour)
→ Total: 2–4 days from problem detection to PO decision

**Future State (With AERIE):**
1. System runs scheduled inventory check every 6 hours (automated)
2. Alert appears: "3 products projected to stockout within lead-time window"
3. Khaled clicks alert → sees ranked risk list with demand forecasts
4. Clicks "Generate RFQs for top risks" → system drafts RFQs with recommended quantities
5. Reviews supplier comparison panel → confirms top-ranked supplier for each item
6. Clicks "Submit to Odoo" → RFQs created with one approval click
→ Total: ~20 minutes from alert review to submitted RFQs | Total cycle: same day

**Journey Emotional Arc:** Anxiety → Relief → Confidence → Control

---

### Journey 3 — Ibrahim Gets a Monday Morning Business Review

**Current State (Without AI):**
1. Emails Layla asking for the weekly summary (Sunday evening)
2. Layla spends 2–3 hours on Monday morning compiling ERP data
3. Layla creates slides and sends by mid-morning
4. Ibrahim reviews data that is already 8–12 hours old
→ Lag: 8–12 hours | Analyst burden: 2–3 hours per week

**Future State (With AERIE):**
1. Ibrahim opens AERIE web app on Monday morning
2. Types (Arabic): "أعطني مراجعة أداء الأسبوع الماضي"
3. Analytics Supervisor spawns 4 sub-agents simultaneously
4. Data Retrieval, KPI Computation, Visualization, and Insight agents work in parallel
5. Full executive report with charts and narrative delivered in < 30 seconds
→ Lag: Zero | Analyst burden: Zero | Data freshness: Real-time

**Journey Emotional Arc:** Habitual frustration → Delight → Adoption

---

### Journey 4 — Yasmine Checks Inventory Without IT Help

**Current State (Without AI):**
1. Yasmine identifies a product she suspects is running low
2. Calls IT or a supervisor to run an Odoo query (wait: 30–120 minutes)
3. Receives a screenshot or printed report
→ Total delay: 30 minutes to 2 hours per query | IT overhead: real

**Future State (With AERIE):**
1. Yasmine opens chat interface on her workstation
2. Types in Arabic: "ما هو مستوى مخزون منتج رقم 2045؟"
3. ERP Query Agent retrieves stock data
4. Response returned in plain Arabic: "المخزون الحالي 34 وحدة. نقطة إعادة الطلب 50 وحدة. يُنصح بإنشاء طلب شراء."
→ Total: 10 seconds | IT involvement: Zero

---

## 8. Detailed Functional Requirements

### 8.1 Module 1 — ERP AI Copilot

---

#### FR-1-01: Bilingual Natural Language Processing

**Feature ID:** FR-1-01
**Feature Name:** Bilingual NLP Interface
**Priority:** Must Have

**Description:**
The system must detect the input language (Arabic or English) automatically and process the query through an appropriate NLP pipeline. Responses must be returned in the same language as the input.

**Inputs:**
- User text input (UTF-8 string, max 2,000 characters)

**Outputs:**
- Detected language (ISO 639-1 code)
- Parsed intent classification (see FR-1-02)
- Extracted entities (dates, product names, customer names, amounts, time ranges)

**Business Rules:**
- BR-1-01-1: Language detection must occur before intent classification.
- BR-1-01-2: Arabic queries must return Arabic responses. English queries must return English responses.
- BR-1-01-3: Mixed-language input (Arabic + English product names) must be handled gracefully; the dominant language determines response language.
- BR-1-01-4: Unrecognized or unsupported languages must return a polite error in English: "I currently support Arabic and English. Please rephrase your query in one of these languages."

**Constraints:**
- Arabic NLP must handle standard Modern Standard Arabic (MSA) and common Egyptian/Gulf dialect terms used in business contexts.
- Dialect support is best-effort; MSA is the baseline.

---

#### FR-1-02: Intent Classification and Routing

**Feature ID:** FR-1-02
**Feature Name:** Intent Classification Engine
**Priority:** Must Have

**Description:**
The Copilot Orchestrator Agent must classify each user input into one of the defined intent categories and route the request to the appropriate agent or agent pipeline.

**Intent Categories:**

| Intent Code | Description | Route To |
|---|---|---|
| `query.data` | Simple ERP data retrieval (stock, orders, customers) | ERP Query Agent |
| `query.analytics` | KPI analysis, performance reports, business reviews | Analytics Supervisor |
| `action.create` | Create ERP record (sales order, quotation, etc.) | ERP Action Agent (with confirmation) |
| `action.update` | Modify ERP record | ERP Action Agent (with confirmation) |
| `action.search` | Search/filter ERP records | ERP Query Agent |
| `procurement.status` | Procurement health inquiry | Procurement Orchestrator (cross-module) |
| `system.greeting` | Greeting or help request | Direct response, no agent spawn |
| `system.unknown` | Unclassified input | Clarification request to user |

**Business Rules:**
- BR-1-02-1: If confidence of intent classification is below 0.70, the system must ask the user a clarifying question before routing.
- BR-1-02-2: `action.create` and `action.update` intents must NEVER be executed without the explicit confirmation step defined in FR-1-05.
- BR-1-02-3: A single query may contain multiple intents (e.g., "Show me sales for last month and create a summary report"). The Orchestrator must identify composite intents and sequence the appropriate agents.

---

#### FR-1-03: ERP Data Query

**Feature ID:** FR-1-03
**Feature Name:** Natural Language ERP Data Retrieval
**Priority:** Must Have

**Description:**
The ERP Query Agent must translate natural language data requests into structured Odoo API calls and return results in a human-readable format.

**Supported Query Domains:**

| Domain | Odoo Models | Example Queries |
|---|---|---|
| Customer data | `res.partner` | "Who are our top 10 customers by revenue?" |
| Sales orders | `sale.order`, `sale.order.line` | "Show me all open orders this month" |
| Invoices | `account.move` | "What is Customer X's outstanding balance?" |
| Inventory / Stock | `stock.quant`, `product.product` | "What is the current stock level of Product Y?" |
| Products | `product.template`, `product.product` | "List all products in category Z" |
| Purchase orders | `purchase.order` | "What POs are pending supplier confirmation?" |
| Suppliers | `res.partner` (supplier type) | "Who are our top suppliers by order volume?" |

**Business Rules:**
- BR-1-03-1: All queries must be scoped to data visible within the authenticated Odoo instance. No cross-instance queries.
- BR-1-03-2: Results must be paginated if they exceed 50 records. The agent must inform the user: "Showing top 10 results. Say 'show more' to see the next set."
- BR-1-03-3: If an Odoo API call fails, the agent must retry once. On second failure, return a graceful error message.
- BR-1-03-4: Date range extraction must support relative dates: "last month," "this quarter," "last week," "last 90 days," "last year." These must be converted to absolute date ranges before querying Odoo.

**Outputs:**
- Structured data response (tabular or list format)
- Chart data if the intent has visualization markers (e.g., "show me" implies visual output)
- Agent reasoning summary (condensed, shown in UI sidebar)

---

#### FR-1-04: ERP Action Execution

**Feature ID:** FR-1-04
**Feature Name:** Natural Language ERP Action Execution
**Priority:** Must Have

**Description:**
The ERP Action Agent must translate natural language action requests into Odoo write operations. This includes creating records, updating record fields, and changing record states (e.g., confirming a quotation).

**Supported Actions (MVP):**

| Action | Odoo Operation | Notes |
|---|---|---|
| Create sales quotation | `sale.order` create | Requires customer name, products, quantities |
| Add product to order | `sale.order.line` create | Requires active order context |
| Create purchase order draft | `purchase.order` create | Procurement module — shared with Module 2 |
| Create RFQ | `purchase.order` create (RFQ state) | Procurement module — shared with Module 2 |
| Update product quantity | `stock.quant` update | Requires warehouse context |

**Business Rules:**
- BR-1-04-1: Every ERP write action MUST go through the confirmation protocol defined in FR-1-05 before executing.
- BR-1-04-2: The agent must extract all required fields before proposing an action. If required fields are missing, the agent must ask the user to provide them before proceeding.
- BR-1-04-3: Actions are irreversible in Odoo once confirmed. The confirmation message must clearly state this.
- BR-1-04-4: The agent must validate entity names against Odoo data before proposing an action (e.g., customer name must resolve to an existing `res.partner` record).

---

#### FR-1-05: Human-in-the-Loop Confirmation Protocol

**Feature ID:** FR-1-05
**Feature Name:** Action Confirmation Gate
**Priority:** Must Have — Non-Negotiable

**Description:**
Before executing any write operation in Odoo, the system must present a structured confirmation summary and require explicit user approval. This gate is mandatory for all ERP write operations without exception.

**Confirmation Summary Format:**
```
ACTION REVIEW
─────────────────────────────────
Action Type: Create Sales Quotation
Customer: Al-Mustaqbal Trading Co.
Products:
  • Product A — 50 units @ 25 EGP = 1,250 EGP
  • Product B — 20 units @ 80 EGP = 1,600 EGP
Total: 2,850 EGP
Assigned To: Nour Al-Hassan
─────────────────────────────────
⚠️ This action will create a record in Odoo. This cannot be automatically undone.

[ ✅ Confirm & Execute ]  [ ❌ Cancel ]
```

**Business Rules:**
- BR-1-05-1: The confirmation panel must be rendered before any Odoo API write call is made.
- BR-1-05-2: Confirmation must be an explicit user action (button click or typed confirmation). Implicit timeout confirmation is NOT permitted.
- BR-1-05-3: If the user cancels, no write operation occurs. The agent must acknowledge: "Action cancelled. No changes were made to Odoo."
- BR-1-05-4: Every confirmed or cancelled action must be written to the audit log with: timestamp, user session ID, action type, entity affected, and outcome.
- BR-1-05-5: The system must NEVER retry a cancelled action automatically.

---

#### FR-1-06: Multi-Agent Analytics System

**Feature ID:** FR-1-06
**Feature Name:** Multi-Agent Analytics Engine
**Priority:** Must Have

**Description:**
Analytics requests must be handled by a dedicated multi-agent sub-system orchestrated by an Analytics Supervisor. This sub-system comprises four specialized agents working in sequence (and partially in parallel) to produce a complete business intelligence output.

**Analytics Pipeline:**

```
Analytics Supervisor receives task
         ↓
1. Data Retrieval Agent → fetches raw ERP data
         ↓
2. KPI Computation Agent → processes raw data into KPIs
         ↓
3. Visualization Agent → selects chart types, generates chart configs
         ↓
4. Insight Generation Agent → writes narrative business insights
         ↓
Analytics Supervisor assembles final report → returns to Orchestrator
```

**Report Output Structure:**

| Section | Content | Format |
|---|---|---|
| Executive Summary | 2–3 sentence business performance summary | Text |
| Revenue KPIs | Revenue total, vs. prior period, trend | Number + delta |
| Top Customers | Ranked by revenue | Table + bar chart |
| Top Products | Ranked by units sold and revenue | Table + bar chart |
| Inventory Health | Stock status summary | Table |
| Procurement Status | Open POs, pending deliveries | Table |
| Key Insights | 3–5 bullet points with business significance | Bullet list |
| Data Basis | Time range, record count, data freshness | Footer metadata |

**Business Rules:**
- BR-1-06-1: Every analytics report must state the time period it covers. Default period: last 30 days.
- BR-1-06-2: KPIs must include both absolute values and period-over-period comparison where prior period data exists.
- BR-1-06-3: Visualizations must be auto-selected by the Visualization Agent based on data type (see Visualization Agent definition in Section 10).
- BR-1-06-4: Narrative insights must be grounded in the computed data. The Insight Generation Agent must not fabricate trends not present in the data.
- BR-1-06-5: Reports must include a data basis footer stating: data source (Odoo), query time range, and record count processed.

---

#### FR-1-07: Session Memory and Conversational Context

**Feature ID:** FR-1-07
**Feature Name:** In-Session Conversational Context
**Priority:** Must Have

**Description:**
The Copilot must maintain conversational context within a single user session, enabling multi-turn queries where later messages reference earlier context.

**Context Retention Requirements:**

| Context Type | Retention Scope | Example |
|---|---|---|
| Entity context | Within session | "Show me their invoices" (after querying a customer) |
| Time range context | Within session | "Now show me the same for Q1" |
| Filter context | Within turn | "Filter by Cairo" (applied to prior result) |
| Action context | Within turn | "Add another product" (to an order being drafted) |

**Business Rules:**
- BR-1-07-1: Session context must be maintained in Redis with a TTL of 60 minutes from the last interaction.
- BR-1-07-2: When context expires, the system must start a new context window and inform the user: "This is a new conversation. Previous context has been cleared."
- BR-1-07-3: Context must be stored as a structured message history object, not as free text.
- BR-1-07-4: The context window passed to the LLM must be truncated intelligently if it exceeds the model's context limit. Retain the last 10 turns and the initial system prompt.

---

### 8.2 Module 2 — Procurement Intelligence Agent

---

#### FR-2-01: Inventory Health Monitoring

**Feature ID:** FR-2-01
**Feature Name:** Real-Time Inventory Health Monitoring
**Priority:** Must Have

**Description:**
The Inventory Monitor Agent must continuously evaluate current stock levels against defined thresholds and generate alerts when products enter risk states.

**Risk State Classification:**

| State | Definition | Color Code |
|---|---|---|
| HEALTHY | Current stock ≥ Reorder Point × 1.5 | Green |
| WATCH | Current stock between Reorder Point and Reorder Point × 1.5 | Yellow |
| AT RISK | Current stock ≤ Reorder Point | Orange |
| CRITICAL | Current stock ≤ (Lead Time Days × Avg Daily Consumption) | Red |
| STOCKOUT | Current stock = 0 | Black |

**Business Rules:**
- BR-2-01-1: The monitoring cycle must run every 6 hours by default. The interval must be configurable.
- BR-2-01-2: State transitions from HEALTHY/WATCH to AT RISK/CRITICAL must generate an alert notification in the UI.
- BR-2-01-3: Reorder points must be read from Odoo's `product.template.reorder_point` field. If not set in Odoo, the system must calculate a default: average daily consumption × (lead time days + 7 safety days).
- BR-2-01-4: CRITICAL state must also trigger automatic initiation of the Demand Forecaster Agent and RFQ Draft Generator pipeline.

---

#### FR-2-02: Demand Forecasting

**Feature ID:** FR-2-02
**Feature Name:** Demand Forecasting Engine
**Priority:** Must Have

**Description:**
The Demand Forecaster Agent must compute future demand estimates for at-risk products using historical consumption data from Odoo.

**Forecasting Methodology (MVP):**
- Primary: Weighted Moving Average (90 days of sales/consumption history, with more recent data weighted higher)
- Secondary: Exponential Smoothing (for products with strong trend patterns)
- Fallback: Simple average if fewer than 30 days of history exist (flagged as "low confidence")

**Forecast Output Per Product:**

| Field | Description |
|---|---|
| Forecasted Demand | Units per day (7-day and 30-day projections) |
| Recommended Order Quantity | EOQ-based or reorder-to-max calculation |
| Confidence Level | High (90+ days data) / Medium (30–90 days) / Low (< 30 days) |
| Projected Stockout Date | If no reorder, on what date does stock reach zero |
| Days Until Stockout | Integer, critical for prioritization |

**Business Rules:**
- BR-2-02-1: Forecasts must be recalculated every time an inventory alert is triggered.
- BR-2-02-2: Confidence levels must be displayed alongside all forecasts. Users must be informed when a forecast has low confidence.
- BR-2-02-3: Seasonal adjustments are out of scope for MVP. Note: Forecast assumes flat demand trend.
- BR-2-02-4: Recommended Order Quantity must account for minimum order quantity (MOQ) constraints from the Odoo supplier pricelist if available.

---

#### FR-2-03: Procurement Health Score

**Feature ID:** FR-2-03
**Feature Name:** Procurement Health Scoring
**Priority:** Should Have

**Description:**
Each product and the overall procurement portfolio must be assigned a composite Procurement Health Score (PHS) that summarizes risk in a single metric.

**PHS Calculation:**

| Component | Weight | Data Source |
|---|---|---|
| Stock Level vs. Reorder Point | 30% | Odoo `stock.quant` |
| Days Until Projected Stockout | 25% | Demand Forecaster output |
| Pending RFQs / POs | 20% | Odoo `purchase.order` |
| Supplier Lead Time Risk | 15% | Odoo supplier pricelist |
| Expiry Risk (if applicable) | 10% | Odoo `lot.expiration.date` (if enabled) |

**Score Range:** 0–100 (100 = perfectly healthy, 0 = critical emergency)

**Business Rules:**
- BR-2-03-1: PHS must be recalculated after every monitoring cycle.
- BR-2-03-2: The procurement dashboard must display the portfolio-level PHS prominently.
- BR-2-03-3: Score thresholds: ≥ 75 = Green, 50–74 = Yellow, 25–49 = Orange, < 25 = Red.

---

#### FR-2-04: Automated RFQ Generation

**Feature ID:** FR-2-04
**Feature Name:** RFQ Draft Auto-Generation
**Priority:** Must Have

**Description:**
The RFQ Draft Generator must automatically create a draft Request for Quotation in Odoo for at-risk products, pre-populated with product details, recommended quantities, and the preferred supplier.

**RFQ Draft Fields Populated:**

| Field | Source |
|---|---|
| Supplier | Top-ranked supplier from Supplier Evaluator Agent |
| Product | At-risk product from Inventory Monitor |
| Quantity | Recommended order quantity from Demand Forecaster |
| Expected Lead Time | From Odoo supplier pricelist or historical data |
| Internal Notes | AI-generated note explaining why this RFQ was created |

**Business Rules:**
- BR-2-04-1: RFQ drafts must NOT be submitted to Odoo until a human confirms them via the approval gate.
- BR-2-04-2: The system may generate multiple RFQs simultaneously (one per at-risk product), grouped by supplier where possible.
- BR-2-04-3: If no preferred supplier is identified, the RFQ draft must still be created with an empty supplier field and flagged as "Supplier selection required."
- BR-2-04-4: The RFQ draft preview must be displayed in the procurement dashboard for review before confirmation.

---

#### FR-2-05: Supplier Evaluation and Ranking

**Feature ID:** FR-2-05
**Feature Name:** Intelligent Supplier Evaluation
**Priority:** Must Have

**Description:**
The Supplier Evaluator Agent must score and rank available suppliers for a given product based on historical performance data extracted from Odoo purchase orders.

**Supplier Scoring Model:**

| Criterion | Weight | Data Source | Calculation |
|---|---|---|---|
| Average Unit Price | 35% | Historical POs | Lower price = higher score |
| On-Time Delivery Rate | 30% | PO actual vs. expected delivery dates | % of POs delivered on time |
| Price Consistency | 20% | Price variance across historical POs | Lower variance = higher score |
| Order Volume History | 15% | Total order count with supplier | More history = higher confidence |

**Output:** Ranked supplier list with scores, score breakdown, and a recommendation rationale statement.

**Business Rules:**
- BR-2-05-1: Suppliers with fewer than 2 historical POs must be flagged as "New Supplier — Limited Data."
- BR-2-05-2: Supplier rankings must be re-evaluated every time a new PO is confirmed in Odoo (future: via webhook; MVP: on-demand recalculation).
- BR-2-05-3: The ranking must be product-specific, not generic. A supplier ranked #1 for Product X may not be #1 for Product Y.

---

#### FR-2-06: OCR-Based Supplier Quote Processing

**Feature ID:** FR-2-06
**Feature Name:** Supplier Quote PDF Processing
**Priority:** Should Have

**Description:**
Users must be able to upload supplier quotation PDFs. The OCR Agent must extract structured data from the document and format it for supplier comparison.

**Extracted Fields:**

| Field | Extraction Method |
|---|---|
| Supplier Name | Text extraction + entity recognition |
| Product Name / Description | Text extraction |
| Unit Price | Numeric extraction |
| Minimum Order Quantity | Numeric extraction |
| Delivery Lead Time | Text + numeric extraction |
| Payment Terms | Text extraction |
| Quotation Validity Date | Date extraction |

**Business Rules:**
- BR-2-06-1: OCR processing must handle standard Arabic and English PDF documents.
- BR-2-06-2: Extraction confidence must be indicated. Fields with low-confidence extraction must be highlighted for user review.
- BR-2-06-3: The extracted data must be presented in an editable table before being used in supplier comparison, allowing the user to correct OCR errors.
- BR-2-06-4: Supported file types: PDF only (MVP). Maximum file size: 10MB.

---

#### FR-2-07: Human Approval Workflow for Procurement Actions

**Feature ID:** FR-2-07
**Feature Name:** Procurement Approval Gate
**Priority:** Must Have — Non-Negotiable

**Description:**
All procurement write actions (RFQ submission, PO creation, PO confirmation) must go through a structured human approval workflow before any Odoo write operation is executed.

**Approval Steps:**

1. AI generates draft action (RFQ or PO)
2. Draft is displayed in the Procurement Review Panel (see UI Section 17)
3. User reviews: product, quantity, supplier, price estimate, and AI rationale
4. User selects: Approve / Reject / Modify
5. If Approved: system executes Odoo write operation, records action in audit log
6. If Rejected: draft is discarded, audit log entry created, system asks for reason
7. If Modify: user edits draft fields, then re-confirms before execution

**Business Rules:**
- BR-2-07-1: Batch approval is allowed (approve all pending RFQs in one action). Each approved item must still be individually logged.
- BR-2-07-2: Rejected drafts must be retained in audit log for 30 days (in MVP, for the session).
- BR-2-07-3: The approval UI must clearly label all AI-generated recommendations as "AI RECOMMENDATION — Human review required."

---

#### FR-2-08: Prototype Features (MVP Boundary)

**Feature ID:** FR-2-08
**Feature Name:** Prototype Procurement Features
**Priority:** Nice to Have / Prototype

The following features are defined but excluded from MVP delivery:

**FR-2-08-A — Expiry Risk Analysis:**
- Description: Flag products with lot-tracked inventory approaching expiration dates.
- Data required: Odoo `stock.lot` with `expiration_date` populated.
- Dependency: Odoo lot tracking must be enabled and configured.
- MVP Decision: PROTOTYPE — requires Odoo lot tracking configuration and additional data population. Include in demo only if time allows.

**FR-2-08-B — Slow-Moving Product Detection:**
- Description: Identify products with turnover velocity below a defined threshold over a rolling 90-day window.
- Threshold: Products with < 3 sales transactions or < 10 units sold in 90 days classified as slow-moving.
- MVP Decision: PROTOTYPE — valuable but not critical for demo. Implement if Sprint 4 has capacity.

**FR-2-08-C — Scenario Simulation:**
- Description: Allow user to ask "What if Supplier X's lead time increases by 2 weeks?" — system recalculates stockout risk for all products sourced from that supplier.
- MVP Decision: NICE TO HAVE — implement as a stretch capability in Module 2 if core features are stable.

---

### 8.3 Module 3 — Customer Support Multi-Agent System (Stretch)

**Priority:** Stretch Goal — DO NOT implement until Modules 1 and 2 are fully delivered and tested.

**Minimum Viable Definition:**

| Capability | Description |
|---|---|
| Customer query interface | External-facing chat (separate from internal Copilot) |
| Order status queries | Customer can query their own order status by order ID or name |
| Invoice queries | Customer can query their own invoice balance |
| Escalation | Queries that cannot be resolved automatically are flagged for human review |
| Language | Arabic and English |

**Implementation Approach:** Reuse ERP Query Agent from Module 1 with a customer-scoped tool access policy (restrict to partner-filtered queries). Module 3 is primarily a new UI + a new access policy, not new agent infrastructure.

---

## 9. Detailed Non-Functional Requirements

### 9.1 Performance Requirements

| ID | Requirement | Target | Condition |
|---|---|---|---|
| NFR-P-01 | Simple ERP query response time | ≤ 5 seconds | Single user, mock dataset |
| NFR-P-02 | Complex analytics report generation | ≤ 30 seconds | Full executive review, all 4 sub-agents |
| NFR-P-03 | RFQ draft generation time | ≤ 15 seconds | For 3 at-risk products |
| NFR-P-04 | Inventory monitoring cycle | ≤ 60 seconds | Full product catalog scan |
| NFR-P-05 | UI page initial load time | ≤ 3 seconds | Standard connection |
| NFR-P-06 | OCR processing per page | ≤ 10 seconds | Single-page PDF |
| NFR-P-07 | Agent streaming response | First token within 2 seconds | For streamed responses |

### 9.2 Scalability Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-S-01 | Concurrent users (MVP demo) | 5 simultaneous users without degradation |
| NFR-S-02 | Product catalog size (mock) | 200 products without performance degradation |
| NFR-S-03 | Historical order data | 6 months (est. 5,000 order lines) without query latency issues |
| NFR-S-04 | Session management | 10 active sessions simultaneously |
| NFR-S-05 | Architecture extensibility | New agent types must be addable without refactoring the orchestration layer |

### 9.3 Reliability Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-R-01 | System uptime during demo day | 100% (zero downtime) — use Docker Compose health checks |
| NFR-R-02 | Agent failure graceful degradation | If an agent fails, return error message to user; do not crash the system |
| NFR-R-03 | LLM API failure fallback | On LLM API timeout (>30s), return: "The AI service is temporarily unavailable. Please retry." |
| NFR-R-04 | Odoo API failure handling | On Odoo API failure, retry once. On second failure, return graceful error with retry suggestion |
| NFR-R-05 | Data consistency | All data displayed must reflect the Odoo state at query time. Cached data must not be older than 5 minutes for inventory data |

### 9.4 Security Requirements

Detailed in Section 18.

### 9.5 Observability Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-O-01 | All agent invocations logged | LangSmith trace for every agent call |
| NFR-O-02 | All Odoo API calls logged | Structured log with: timestamp, model, operation, record ID, success/failure |
| NFR-O-03 | All ERP write actions logged | Immutable audit log (see Section 18) |
| NFR-O-04 | LLM prompt/response logged | LangSmith + application log (exclude PII) |
| NFR-O-05 | Performance metrics logged | Response time per agent step, total pipeline time |
| NFR-O-06 | Agent reasoning visible to user | Collapsible "Agent Thinking" panel in UI showing step-by-step reasoning |

### 9.6 Auditability Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-A-01 | Every ERP write action is audited | Immutable entry: timestamp, session ID, user, action type, entity, outcome |
| NFR-A-02 | All approval and rejection events logged | With timestamp and session context |
| NFR-A-03 | Agent decision provenance | Each AI recommendation must reference the data it was based on |
| NFR-A-04 | Audit log retention | Session-scoped in MVP; persistent in production |
| NFR-A-05 | Audit log queryable | Admin interface or API endpoint to retrieve audit entries |

### 9.7 Usability Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-U-01 | Arabic RTL layout | All Arabic-language outputs must render right-to-left |
| NFR-U-02 | Responsive design | Functional on 1280px wide desktop. Mobile optimization is future scope |
| NFR-U-03 | Loading state indicators | All agent processing steps must show visible loading states — no silent waits |
| NFR-U-04 | Error message clarity | All error messages must be human-readable, in the user's language |
| NFR-U-05 | Agent reasoning transparency | Users must always be able to see what the AI did to produce a result |

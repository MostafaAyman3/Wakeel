
---

## 14. MVP Definition

### 14.1 Must Have — Core MVP (Non-Negotiable for Demo Day)

**Module 1:**
- Conversational chat interface (web, English + Arabic)
- Language detection and bilingual response
- Intent classification with routing
- ERP Query Agent: customer, order, product, invoice, stock queries
- Action Confirmation Gate (enforced on all writes)
- ERP Action Agent: create sales quotation with confirmation
- Analytics Supervisor + 4 sub-agents (full pipeline)
- Executive Review report: KPIs, ≥ 2 charts, narrative insights
- Session context retention within a session
- Agent reasoning panel ("Thinking Steps") in UI

**Module 2:**
- Inventory Health Monitoring (scheduled + on-demand)
- Demand Forecasting for at-risk products
- Supplier Evaluation and Ranking
- RFQ Draft Generation
- Procurement Review Panel with Approve / Reject workflow
- Procurement Health Dashboard
- Odoo RFQ creation on approval

**Infrastructure:**
- Odoo Community Edition (local, Docker)
- Mock dataset meeting minimum specifications (Section 15)
- LangSmith observability connected
- Full audit log for write actions
- Docker Compose for complete stack

---

### 14.2 Should Have — Quality and Demo Impact

- Agent Thinking Panel showing step-by-step reasoning in real time (streamed)
- OCR-based supplier quote processing (at least for mock PDF format)
- Procurement Health Score (composite, per-product and portfolio level)
- Proactive alert notifications pushed to UI during demo
- Period-over-period comparison in all analytics KPIs
- Arabic RTL report formatting (not just response text)
- Combined RFQ suggestion when multiple at-risk products share a supplier

---

### 14.3 Nice to Have — If Time Allows

- Slow-moving product detection
- Expiry risk analysis (requires lot tracking in mock data)
- Scenario simulation ("What if lead time doubles?")
- Supplier intelligence profile page (longitudinal scoring)
- Confidence score badges on all forecasts and recommendations
- Voice-to-text input (API-based, e.g., OpenAI Whisper)
- Draft PO creation (in addition to RFQ)

---

### 14.4 Prototype (Define but Do Not Build)

- Module 3: Customer Support Multi-Agent System (infrastructure reuse plan defined, not implemented)
- Dynamic pricing recommendations (requires external market data)
- Agent memory persistence across sessions (requires persistent vector store architecture)
- Autonomous procurement execution (no human gate — governed by configurable risk thresholds)
- Multi-company/multi-tenant architecture

---

### 14.5 Future Scope (Post-Program)

- Real-time Odoo event streaming via webhooks
- Mobile application
- Integration with SAP Business One, ERPNext, Microsoft Business Central
- Fine-tuned Arabic business language model
- Role-based agent access control (sales rep cannot execute procurement actions)
- Email / WhatsApp report delivery
- Organizational learning (agents improve recommendations over time)
- Full production deployment infrastructure (Kubernetes, CI/CD, monitoring)

---

## 15. Data Requirements

### 15.1 Required Odoo Entities

| Entity | Odoo Model | Fields Required | Purpose |
|---|---|---|---|
| Customers | `res.partner` | id, name, email, city, country_id, customer_rank, is_company | Customer queries, invoice assignment |
| Suppliers | `res.partner` | id, name, email, supplier_rank, is_company | Supplier evaluation |
| Products | `product.template`, `product.product` | id, name, default_code, categ_id, standard_price, list_price, type, reorder_point (custom or via orderpoint) | Product queries, inventory |
| Product Categories | `product.category` | id, name | Category filtering |
| Inventory / Stock | `stock.quant` | product_id, location_id, quantity, reserved_quantity | Current stock levels |
| Reorder Rules | `stock.warehouse.orderpoint` | product_id, product_min_qty, product_max_qty, qty_multiple | Reorder thresholds |
| Sales Orders | `sale.order` | id, name, partner_id, date_order, amount_total, state, user_id | Sales analytics, revenue |
| Sales Order Lines | `sale.order.line` | order_id, product_id, product_uom_qty, price_unit, price_subtotal | Product-level analysis |
| Invoices | `account.move` | id, name, partner_id, invoice_date, amount_total, amount_residual, state, move_type | Invoice queries, outstanding balances |
| Purchase Orders | `purchase.order` | id, name, partner_id, date_order, date_planned, amount_total, state | Procurement analytics, PO tracking |
| Purchase Order Lines | `purchase.order.line` | order_id, product_id, product_qty, price_unit, date_planned, qty_received | Product-level procurement |
| Supplier Pricelists | `product.supplierinfo` | product_id, partner_id, min_qty, price, delay (lead time days) | Supplier pricing and lead times |
| Inventory Lots (optional) | `stock.lot` | product_id, name, expiration_date | Expiry risk analysis (prototype) |
| Warehouses | `stock.warehouse` | id, name, lot_stock_id | Stock location context |

---

### 15.2 Mock Dataset Specifications

The mock dataset must represent a plausible SMB manufacturing or wholesale business in the MENA region. All data must be in both Arabic and English (bilingual product names, customer names in Arabic).

| Entity | Minimum Count | Notes |
|---|---|---|
| Customers | 15 | Mix of companies and individuals. Arabic names. 3 top customers with high transaction volume. 2 with outstanding invoices. |
| Suppliers | 10 | Arabic names. Varied performance history. 2 with limited history (< 2 POs). |
| Products | 50 | 3 product categories minimum. 8–10 products in CRITICAL or AT RISK state for demo. Arabic and English names. |
| Sales Orders | 300 | Spanning 6 months. Clear seasonality is optional. At least one customer with strong growth trend. |
| Sales Order Lines | 800 | Linked to sales orders above. |
| Invoices | 200 | Mix of paid and outstanding. 3–5 customers with significant outstanding balances. |
| Purchase Orders | 150 | Spanning 6 months. Varied suppliers. Some late deliveries recorded (for supplier scoring). |
| Purchase Order Lines | 400 | Linked to purchase orders above. |
| Stock Quantities | 50 (one per product) | Mixed health states: 10 CRITICAL, 10 AT RISK, 15 WATCH, 15 HEALTHY. |
| Reorder Rules | 50 | One per product. Min/max quantities set. |
| Supplier Pricelists | 100 | 2 suppliers per product average, varied pricing. |

**Demo Dataset Design Principles:**
1. Products in CRITICAL state must have a clear, visible demand trend that makes the forecasted stockout date believable.
2. At least 2 products must share a top-ranked supplier (to demonstrate combined RFQ feature).
3. One supplier must have a low on-time delivery record (to demonstrate supplier scoring differentiation).
4. Revenue for the mock company must show a clear quarter-over-quarter trend (growth or decline) for the analytics demo.
5. One customer must have a significantly large outstanding invoice balance (for invoice query demo).

---

### 15.3 Data Generation Approach

A Python script (`seed_mock_data.py`) must be written and included in the repository. This script:
- Generates all entities with realistic Arabic and English names
- Loads data into the Odoo instance via the JSON-RPC API
- Is idempotent (running it twice does not create duplicate records)
- Documents the key "story" data points used in demo scenarios (in a `demo_data_guide.md` file)

---

### 15.4 Data Relationships (Critical)

```
res.partner (Customer)
  ← sale.order → sale.order.line → product.product
  ← account.move (invoice)

res.partner (Supplier)
  ← purchase.order → purchase.order.line → product.product
  ← product.supplierinfo → product.product

product.product
  ← stock.quant (inventory level)
  ← stock.warehouse.orderpoint (reorder rules)
  ← product.supplierinfo (supplier pricing + lead time)
```

All foreign key relationships must be validated in the mock dataset. Broken references will cause agent query failures during the demo.

---

## 16. API Requirements

### 16.1 Backend API — Module 1 (Copilot)

**Base Path:** `/api/v1/copilot`

| Endpoint | Method | Description | Auth Required |
|---|---|---|---|
| `/session` | POST | Initialize a new chat session, return session_id | Yes |
| `/session/{session_id}` | DELETE | Terminate a session and clear Redis context | Yes |
| `/chat` | POST | Send a user message; returns agent response | Yes |
| `/chat/stream` | WebSocket | Stream agent response tokens in real time | Yes |
| `/actions/{action_id}/confirm` | POST | Confirm a pending ERP write action | Yes |
| `/actions/{action_id}/reject` | POST | Reject a pending ERP write action | Yes |
| `/reports/{report_id}` | GET | Retrieve a previously generated analytics report | Yes |

**POST `/chat` Request Body:**
```json
{
  "session_id": "string",
  "message": "string",
  "language_hint": "ar | en | auto"
}
```

**POST `/chat` Response:**
```json
{
  "session_id": "string",
  "response_text": "string",
  "language": "ar | en",
  "agent_steps": [],
  "charts": [],
  "kpis": [],
  "pending_action": null | { action_id, summary }
}
```

---

### 16.2 Backend API — Module 2 (Procurement)

**Base Path:** `/api/v1/procurement`

| Endpoint | Method | Description | Auth Required |
|---|---|---|---|
| `/health` | GET | Returns portfolio Procurement Health Score and risk summary | Yes |
| `/alerts` | GET | Returns current active procurement alerts | Yes |
| `/products` | GET | Returns all products with risk states | Yes |
| `/products/{product_id}/forecast` | GET | Returns demand forecast for a specific product | Yes |
| `/suppliers` | GET | Returns supplier list with scores | Yes |
| `/suppliers/{product_id}/ranking` | GET | Returns supplier ranking for a specific product | Yes |
| `/rfq/drafts` | GET | Returns all pending RFQ drafts awaiting approval | Yes |
| `/rfq/drafts/{draft_id}/approve` | POST | Approves and submits RFQ draft to Odoo | Yes |
| `/rfq/drafts/{draft_id}/reject` | POST | Rejects and discards an RFQ draft | Yes |
| `/rfq/generate` | POST | Manually triggers RFQ generation for specified products | Yes |
| `/monitoring/run` | POST | Manually triggers a procurement monitoring cycle | Yes |
| `/quotes/upload` | POST | Upload supplier quote PDF for OCR processing | Yes |
| `/quotes/{quote_id}` | GET | Returns extracted data from a processed quote | Yes |

---

### 16.3 Odoo Integration API (Internal)

**All Odoo communication is internal to the backend. Not exposed to the frontend directly.**

| Operation | Odoo Method | Description |
|---|---|---|
| Authentication | `common.authenticate` | Returns user UID for session |
| Model Read | `object.execute_kw` with `search_read` | Query records with filters |
| Model Create | `object.execute_kw` with `create` | Create new records (gated) |
| Model Write | `object.execute_kw` with `write` | Update existing records (gated) |
| Model Action | `object.execute_kw` with `action_*` | Execute workflow actions (gated) |
| Schema Lookup | `object.execute_kw` with `fields_get` | Retrieve model field definitions |

**Odoo Client Design Requirements:**
- Must be a singleton class (`OdooClient`) used by all agents
- Must handle authentication refresh automatically
- Must support both synchronous and async call patterns
- Must enforce a configurable rate limit (max 10 calls/second)
- Must log every call (model, method, domain, response time, success/failure)

---

### 16.4 WebSocket API — Agent Streaming

**Endpoint:** `WS /api/v1/copilot/chat/stream`

The WebSocket stream sends incremental agent events to the frontend for real-time display of:
- Agent step completions ("Querying Odoo for sales data...")
- Partial text tokens (streaming LLM response)
- Chart data ready events
- Error events

**Message Types:**
```json
{ "type": "agent_step", "step_name": "string", "status": "running | complete | error" }
{ "type": "text_token", "token": "string" }
{ "type": "chart_ready", "chart_id": "string", "chart_data": {} }
{ "type": "action_required", "action_id": "string", "confirmation_summary": {} }
{ "type": "complete", "response_id": "string" }
{ "type": "error", "error_code": "string", "message": "string" }
```

---

## 17. UI Requirements

### 17.1 Screen Inventory

| Screen ID | Screen Name | Module | Primary User |
|---|---|---|---|
| UI-01 | Login / Authentication | System | All users |
| UI-02 | Main Dashboard | System | All users |
| UI-03 | Copilot Chat Interface | Module 1 | All copilot users |
| UI-04 | Analytics Report View | Module 1 | Managers, Executives |
| UI-05 | Action Confirmation Panel | Module 1 | Any user performing write actions |
| UI-06 | Procurement Dashboard | Module 2 | Procurement, Supply Chain |
| UI-07 | Product Risk List | Module 2 | Procurement, Warehouse |
| UI-08 | RFQ Review Panel | Module 2 | Procurement Manager |
| UI-09 | Supplier Comparison Panel | Module 2 | Procurement Manager |
| UI-10 | Quote Upload & Review | Module 2 | Procurement Manager |
| UI-11 | Audit Log Viewer | System | Admin / Manager |

---

### 17.2 Screen Specifications

#### UI-03: Copilot Chat Interface

**Layout:**
- Left sidebar: session history (list of conversation titles), language toggle (AR/EN)
- Main area: chat thread (user messages right-aligned, AI responses left-aligned)
- Bottom: message input bar with send button and optional voice input button
- Right sidebar (collapsible): "Agent Thinking" panel — shows agent steps in real time

**Components:**
- `ChatBubble` — renders user and AI messages; AI messages support markdown + charts inline
- `AgentThinkingPanel` — collapsible panel showing: agent name, step description, status indicator (spinner / check / error), elapsed time
- `ConfirmationModal` — full-screen modal overlay for action confirmation (see UI-05)
- `ChartEmbed` — inline chart rendered from Recharts config (responsive width)
- `KPICard` — compact card showing KPI name, value, delta indicator (↑ / ↓), and period label
- `LanguageToggle` — toggle AR/EN in header; triggers response language preference
- `MessageInput` — text input with character limit indicator; Enter to send; Shift+Enter for newline

**Arabic RTL Requirement:**
- When language is set to Arabic, the entire interface must apply `dir="rtl"` to the root element
- Chat bubbles, sidebar, and input bar must all reflow for RTL
- All Arabic text must use an appropriate Arabic web font (e.g., Noto Kufi Arabic or IBM Plex Arabic)

**Behavior:**
- Loading state: animated dots + "Thinking..." label while agent processes
- Streaming: text tokens appear incrementally; charts appear when their data event arrives
- Error state: red-bordered message bubble with error text and retry button

---

#### UI-06: Procurement Dashboard

**Layout:**
- Top row: Portfolio Health Score widget (large gauge/score card) + 3 summary stats (Critical items, AT RISK items, Pending RFQs)
- Second row: Alert notification panel (list of active alerts with dismiss/action buttons)
- Main area: Product Risk Table (sortable by risk state, days-until-stockout, product name)
- Bottom: Quick Actions (Run Procurement Check, View RFQ Drafts, Upload Quote)

**Components:**
- `HealthScoreGauge` — radial gauge or large score card (0–100, color-coded by threshold)
- `AlertBanner` — dismissable alert card with severity icon, product name, risk description, and CTA button
- `ProductRiskTable` — sortable, filterable table with columns: Product Name, Category, Current Stock, Reorder Point, Days Until Stockout (forecast), Recommended Order Qty, Risk State badge
- `RiskStateBadge` — color-coded pill: Green (Healthy), Yellow (Watch), Orange (At Risk), Red (Critical), Black (Stockout)
- `QuickActionBar` — buttons triggering key procurement actions

---

#### UI-08: RFQ Review Panel

**Layout:**
- List of pending RFQ drafts, each as an expandable card
- Each card shows: product, quantity, supplier (with score badge), unit price estimate, projected delivery date, AI rationale note
- Action buttons per card: Approve, Reject, Edit
- Batch action bar: "Approve All" button

**Components:**
- `RFQDraftCard` — expandable card; collapsed state shows summary; expanded state shows full detail + edit mode
- `SupplierScoreBadge` — small badge showing supplier score (e.g., "82/100") and primary scoring driver
- `AIRationaleNote` — expandable text block showing the AI's reasoning for this recommendation, with data references
- `ApprovalBar` — sticky bottom bar showing: X drafts pending, "Approve All" + "Reject All" buttons

---

#### UI-09: Supplier Comparison Panel

**Layout:**
- Triggered from RFQ Draft Card or manually from product detail
- Shows side-by-side comparison of 2–4 suppliers for a given product
- Includes: score breakdown table, radar chart comparing key criteria, recommendation highlight

**Components:**
- `SupplierComparisonTable` — tabular comparison of all scored criteria per supplier; recommended supplier highlighted
- `SupplierRadarChart` — radar/spider chart showing relative supplier performance across scoring dimensions
- `SelectSupplierButton` — allows user to override AI recommendation and select a different supplier for the RFQ

---

#### UI-05: Action Confirmation Panel

- Rendered as a full-page modal overlay (cannot be dismissed by clicking outside)
- Header: "Review Required Action"
- Body: structured action summary (see FR-1-05 format)
- Warning text: "This will create / modify a record in Odoo."
- Two buttons: primary CTA "Confirm & Execute" (green) and secondary "Cancel" (red outline)
- Confirmation button text must be dynamic based on action type

---

### 17.3 Shared UI Requirements

- **Design System:** Tailwind CSS utility classes. Consistent color palette: primary brand color + semantic colors (green = success/healthy, yellow = watch, orange = at-risk, red = critical/error).
- **Typography:** Arabic font: IBM Plex Arabic or Noto Kufi Arabic. English font: Inter or system-ui. Minimum body font size: 14px.
- **Responsive Breakpoint:** Fully functional at 1280px wide desktop. 768px tablet view is optional.
- **Loading States:** All asynchronous operations must show a spinner or skeleton loader. No blank screens during data fetching.
- **Error States:** All error conditions have a user-facing message with a recommended action.
- **Empty States:** All tables and lists have an empty state illustration with a descriptive message (not just a blank table).
- **Toast Notifications:** Success/error toasts for all Odoo write operations (bottom-right, 4-second auto-dismiss).

---

## 18. Security Requirements

### 18.1 Authentication

| Requirement | Specification |
|---|---|
| Authentication method | JWT (JSON Web Tokens) issued on login |
| Token expiry | Access token: 8 hours. Refresh token: 7 days. |
| Login credentials | Username + password (stored as bcrypt hash in PostgreSQL) |
| Session management | JWT stored in httpOnly cookie (not localStorage) |
| Odoo authentication | Odoo UID and session key stored server-side only; never exposed to frontend |

### 18.2 Authorization

**User Roles (MVP):**

| Role | Permissions |
|---|---|
| `admin` | All features, audit log access |
| `manager` | All copilot features, all procurement features (including approvals), analytics |
| `analyst` | Read-only ERP queries, analytics reports, procurement dashboard (view only) |
| `procurement` | Procurement dashboard, RFQ approval/rejection, supplier comparison |
| `sales` | Copilot chat, sales-domain queries, sales quotation creation |

**Authorization Rules:**
- Roles are enforced at the API layer — no role enforcement logic in the frontend alone.
- ERP write actions (`action.create`, `action.update`) require `manager` or `sales` role (scoped by domain).
- Procurement approvals require `procurement` or `manager` role.
- Audit log access requires `admin` role.
- All role definitions must be stored in the application database, not hardcoded.

### 18.3 Human Approval Workflow (Security Perspective)

- The confirmation gate is a security control, not just a UX pattern.
- The backend must validate that a confirmation request was genuinely submitted by the same session that initiated the action.
- Confirmation tokens are single-use, tied to the session, and expire after 10 minutes.
- A replay attack (resubmitting a confirmation request) must be rejected by the backend.

### 18.4 Input Sanitization

- All user inputs must be sanitized before being passed to the LLM or used in Odoo API calls.
- Prompt injection mitigation: user input is passed as data in the system prompt structure, never directly concatenated into system-level instructions.
- SQL injection is not directly applicable (using Odoo's ORM), but domain filter construction must validate input types.
- File uploads (PDF for OCR) must be validated: type check (PDF only), size check (10MB max), and virus scan (optional in MVP; recommended for production).

### 18.5 Audit Log Specification

**Audit Log Entry Schema:**

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Unique log entry ID |
| `timestamp` | ISO 8601 datetime | When the action occurred |
| `session_id` | String | User session identifier |
| `user_id` | Integer | Application user ID |
| `action_type` | Enum | `create`, `update`, `delete`, `confirm`, `reject`, `query` |
| `odoo_model` | String | Odoo model affected (e.g., `sale.order`) |
| `odoo_record_id` | Integer or null | Odoo record ID created/modified |
| `action_payload` | JSON | Sanitized action parameters |
| `outcome` | Enum | `success`, `failure`, `cancelled_by_user` |
| `failure_reason` | String or null | Error message if outcome is `failure` |
| `agent_id` | String | Which agent executed the action |

**Audit Log Requirements:**
- Audit logs are INSERT-ONLY (no updates, no deletes).
- Audit logs are stored in the application PostgreSQL database in a dedicated `audit_log` table.
- Admin users can query audit logs via the UI (UI-11).
- All ERP write operations AND all approval/rejection events must be logged.

### 18.6 Data Privacy

- No real customer PII is used in the MVP (mock data only).
- LLM API calls must NOT include: raw financial data dumps, personal identification numbers, or personally identifiable contact information in prompts.
- LLM prompt construction must summarize and reference data, not include raw database dumps.
- LangSmith traces are enabled for development. Disable or configure data masking for any future production deployment.

---

## 19. Risk Register

### 19.1 Technical Risks

| ID | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| TR-01 | LLM hallucination producing incorrect ERP data or KPIs | High | High | KPI Computation Agent is code-only (no LLM); Insight Generation Agent is strictly grounded via prompt; output validation against raw data | AI Lead |
| TR-02 | Agent infinite loops (tool call cycles) | Medium | High | Hard limit: max 10 tool calls per agent invocation; LangGraph state machine enforces exit conditions | Agent Framework Lead |
| TR-03 | Odoo API rate limiting or session expiry under demo load | Medium | High | Pre-cache product catalog and schema registry; Odoo client manages session refresh; test under concurrent load before demo | ERP Integration Lead |
| TR-04 | LangGraph state machine complexity causing coordination failures | Medium | Medium | Each agent has a single defined input schema and output schema; all transitions are typed; integration tests per agent pair | Agent Framework Lead |
| TR-05 | Arabic NLP quality insufficient for domain-specific business language | High | Medium | Build and test a 30-query Arabic validation set; iterate on system prompt Arabic instructions; do not over-promise dialect support | NLP Lead |
| TR-06 | WebSocket streaming instability causing incomplete responses in UI | Medium | Medium | Implement graceful fallback: if WebSocket fails, fall back to polling REST endpoint | Frontend Lead |
| TR-07 | OCR accuracy too low for varied PDF layouts | High | Medium | Limit OCR demo to a controlled mock PDF template; disclose limitation in documentation; use GPT-4o Vision as primary extractor | Procurement Lead |
| TR-08 | Mock dataset too small or unrealistic for compelling demo | Medium | High | Data generation script creates narrative-rich dataset; peer-review data guide before first demo rehearsal | Data Lead |

---

### 19.2 Product Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| PR-01 | Scope creep consuming delivery time | High | High | Strict MoSCoW enforcement; no new Must Have features after Week 3; feature freeze before Sprint 4 |
| PR-02 | Demo scenarios not compelling enough | Medium | High | Demo scenarios scripted from this PRD; rehearsed ≥ 3 times before demo day; "before/after" narrative mandatory in every scenario |
| PR-03 | Team focuses on technology, not business value narrative | Medium | High | Every feature specification starts with the business problem it solves (as written in this PRD); value narrative rehearsed |
| PR-04 | Module 2 not complete by demo day | Medium | High | Module 2 has a clearly defined minimum: Inventory Monitor + Demand Forecast + RFQ Draft + Approval. Supplier scoring and OCR are Should Have, not Must Have |
| PR-05 | Judges do not differentiate this from a simple chatbot | Medium | High | LangSmith agent trace visible in demo; multi-agent architecture articulated in the opening narrative; architecture diagram shown before demo starts |

---

### 19.3 AI Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| AR-01 | Prompt injection via malicious user input | Low | High | System prompt and user input structurally separated in all LLM calls; input sanitization applied |
| AR-02 | LLM generates a business recommendation with no data basis | High | High | Insight Generation Agent prompt explicitly instructs: "Only reference data values present in the provided KPI object. Do not infer trends not present in the data." |
| AR-03 | AI executes ERP write without user confirmation | Low | Critical | Confirmation gate is enforced at the API layer, not just the UI layer; backend validates confirmation token before any Odoo write call |
| AR-04 | LLM API cost overrun during development | Medium | Low | Development API key has a monthly spend cap; use GPT-4o-mini for all non-critical reasoning tasks; avoid streaming large datasets to LLM |
| AR-05 | Model produces biased supplier rankings | Low | Medium | Supplier scoring is deterministic (code-based, not LLM); only the rationale text is LLM-generated; scoring criteria are documented and reviewable |

---

### 19.4 Data Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| DR-01 | Mock data relationships are broken (orphaned records) | Medium | High | Data generation script validates all foreign keys before completion; `demo_data_guide.md` documents key data stories |
| DR-02 | Insufficient historical data for meaningful forecasting | High | High | Minimum 6-month mock dataset specified; forecasting confidence logic degrades gracefully for sparse data |
| DR-03 | Odoo instance corrupted or unavailable on demo day | Medium | Critical | Daily backups during final sprint; Docker volume with pre-seeded data snapshot committed to repository |
| DR-04 | LLM context window overflowed by large Odoo query results | Medium | Medium | ERP Query Agent enforces 50-record limit per query; data summarization applied before LLM context insertion |

---

### 19.5 Integration Risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| IR-01 | Odoo JSON-RPC API behavior differs from documentation | Medium | Medium | Build OdooClient against actual running Odoo instance from Day 1; do not build against docs alone |
| IR-02 | Odoo field names differ from expected schema registry | Medium | Medium | Schema registry validated against live Odoo instance before any agent development begins; `schema_validate.py` script created |
| IR-03 | LangSmith observability not capturing all agent steps | Low | Low | LangSmith integration tested in Sprint 0; confirm all agents wrapped in LangSmith trace |
| IR-04 | Docker Compose environment behaves differently on demo machine | Medium | High | Docker Compose tested on clean machine; all environment variables documented; demo environment set up 48 hours before demo day |

---

## 20. Final MVP Recommendation

*This section is authored from the perspective of a Principal Product Manager reviewing this PRD against the realities of a 6-person team, academic timeline, and demo-day success criteria.*

---

### 20.1 What Should Be Prioritized Above All Else

**1. The Confirmation Gate (FR-1-05, FR-2-07) — Absolute Non-Negotiable**
This is both a security requirement and an enterprise-readiness signal. Any ERP AI platform that executes write operations without human confirmation is a liability. Every judge and enterprise evaluator will look for this. It must work flawlessly before any other feature is polished. Build it first in Sprint 1 alongside the basic chat interface.

**2. The Analytics Multi-Agent Pipeline (FR-1-06)**
This is the most technically impressive capability and the clearest demonstration of Agentic AI as distinct from a chatbot. The four-agent analytics sub-system is what earns the "this is not a chatbot" argument. Prioritize completing this over voice input, OCR, or any Module 3 work.

**3. The Proactive Procurement Pipeline (FR-2-01 through FR-2-04)**
The "system detected a problem and acted before I knew about it" moment is the highest-value procurement demo moment. Inventory monitoring → demand forecast → RFQ draft must work end-to-end. Supplier scoring and OCR are valuable but secondary. If time is short in Module 2, deliver a great core pipeline over a feature-rich incomplete one.

**4. Arabic Language Support (FR-1-01)**
Arabic NLP is the most powerful market differentiator. Even a simple, clean Arabic query → Arabic response demo is impactful. Ensure this works on at least 10 specific test queries before demo day. Do not claim Arabic support without testing it.

---

### 20.2 What Should Be Removed from MVP

**Voice-to-Text Input**
Voice adds setup complexity (browser permissions, API latency, audio processing), creates demo risk (background noise, microphone issues), and does not add architectural interest for a technical audience. It should be removed from MVP and listed as a v1.1 feature. The business value is real; the MVP demo risk is not worth it.

**Dynamic Pricing Recommendations (FR-2-08-C)**
Requires external market pricing data that does not exist in mock Odoo data. This feature cannot be meaningfully demonstrated and will appear superficial if attempted. Remove it from all scope discussions.

**Slow-Moving Product Detection and Expiry Risk Analysis**
Both are legitimate features but neither adds to the core demo narrative. They are variations on the inventory monitoring theme. If inventory monitoring, demand forecasting, and RFQ generation are working well, these features add incremental value. If the team is under time pressure, they should be the first to cut. Mark as Nice to Have and revisit only if Module 2 core is complete by end of Sprint 3.

**Module 3 — Customer Support**
This should not appear in any Sprint planning until both Module 1 and Module 2 are complete and demo-rehearsed. It is a reuse play, not a new capability. If Modules 1 and 2 are not fully working by Sprint 5, Module 3 does not happen. This is not negotiable.

---

### 20.3 What Should Be Postponed

**Supplier Intelligence Profile Pages**
The supplier scoring model is an MVP feature (should have). A dedicated supplier profile page with longitudinal scoring history is a post-MVP feature. Rank suppliers in the RFQ review panel; don't build a separate supplier CRM view.

**Scenario Simulation ("What If" Analysis)**
This is genuinely impressive in a demo but requires a separate computation pipeline. It is a Nice to Have. If Module 2 core is complete and stable by mid-Sprint 4, consider implementing one specific scenario: "What if Supplier X's lead time increases by N days?" as a single endpoint. Do not generalize this in MVP.

**Agent Memory Persistence Across Sessions**
Cross-session memory requires a persistent vector store, embedding pipelines, and a memory retrieval strategy. This significantly increases architectural complexity. In-session context (FR-1-07) is the MVP. Cross-session memory is Year 2.

---

### 20.4 Critical Quality Gates Before Demo Day

The following must be verified in a full dry-run at least 48 hours before demo day:

1. All 5 demo scenarios run end-to-end without agent failure
2. Arabic queries produce Arabic responses with correct RTL formatting
3. LangSmith shows agent traces for all multi-agent workflows
4. Confirmation gate intercepts all write operations — no exceptions
5. At least 3 RFQ drafts visible in procurement dashboard, awaiting approval
6. Analytics report produces correct KPIs matching the mock dataset values
7. Docker Compose stack starts cleanly on a fresh machine from the repository
8. Audit log contains entries from all demo scenario write actions

---

### 20.5 The Principal PM's Final Verdict

This PRD defines a genuinely impressive Agentic AI project that, if delivered correctly, will stand out in any academic, enterprise, or recruiter context. The risk is not ambition — the scope is well-calibrated. The risk is execution discipline.

**Do not add features. Ship the features defined here, and ship them well.**

A flawlessly executed 5-agent analytics pipeline with a clean Arabic interface and a working procurement automation demo is worth more than 10 half-working features. Polish what exists. Make the demo irresistible.

The three things that will define success on demo day:

1. The moment the CEO asks for a business review in Arabic and gets a full report in 20 seconds.
2. The moment the system says "Product X will stockout in 3 days — here's the draft RFQ, ready to approve."
3. The moment a judge asks "How is this different from a chatbot?" and the LangSmith trace shows five agents working in sequence.

Build those three moments first. Everything else is secondary.

---

*End of Master Product Requirements Document*

---

**Appendix: Document Dependency Chain**

```
Vision & Discovery Document (v1.0) [COMPLETE]
        ↓
Master PRD (v1.0) [THIS DOCUMENT]
        ↓
System Architecture Document
        ↓
Sprint Plan + Task Breakdown
        ↓
Agent Implementation Specs (per agent)
        ↓
API Contract Specification
        ↓
Frontend Component Spec
        ↓
Test Plan + Demo Script
```

*Next recommended document: System Architecture Document — defining the technical architecture, service boundaries, data flow, and infrastructure design based on this PRD.*

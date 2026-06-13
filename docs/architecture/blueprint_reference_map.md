# Blueprint Reference Map

> Read this file BEFORE opening ERP_Agentic_AI_Blueprint.md.
> This map tells you exactly which line to jump to for any architectural question.
> Written based on ERP_Blueprint_Index.md navigation guide.

---

## How to Use This File

1. Find your question in the table below
2. Note the section name and line number
3. Open ERP_Agentic_AI_Blueprint.md and jump to that line
4. Do NOT read the entire blueprint — use targeted navigation

---

## Sections Used in This Migration

| Section | Lines | Topic | Conclusion Extracted |
|---------|-------|-------|---------------------|
| 2.1 | 27-29 | M1 Goal | Single-sentence purpose: NL → ERP analytical insight, bilingual, no SQL needed by user |
| 2.2 | 31-54 | M1 Use Cases | 4 groups: Financial / Operational / Invoice / Tax (all 4 in MVP) |
| 2.3 | 56-76 | M1 MVP Features | 7 mandatory features: Intent Classifier, Query Builder, Invoice Analysis, Tax RAG, Output Selector, Narrative Generator, Bilingual |
| 2.3.1 | 78-117 | Dynamic Query Builder | 3-layer security: Read-Only DB + Templates (80%) + NL2SQL+Validation (20%). Start with Templates only in MVP. |
| 2.4 | 119-129 | Architecture Decision | **Single Orchestrator (LangGraph)** — NOT multi-agent. Sequential queries, easier debugging. |
| 2.5 | 131-190 | M1 Agent Workflow | Full LangGraph flow + State Schema defined |
| 2.6 | 192-231 | Invoice Sub-Pipeline | 4-node sub-pipeline inside M1. Invoices are in DB — NO OCR, NO PDF. |
| 2.7 | 233-246 | Tax Reasoning | RAG approach with pgvector. Always includes disclaimer. Never claims absolute accuracy. |
| 2.8 | 248-287 | Output Selector | 8 output types. Decision based on BOTH intent AND actual data shape. |
| 2.9 | 291-309 | M1 Demo Scenarios | 5 scenarios ready for demo: Executive, Collections, Invoice Batch, Tax, Anomaly Alert |
| 2.10 | 311-330 | M1 Data Requirements | DB tables required, assumptions, limitations |
| 3.1 | 335-337 | M3 Goal | Customer support agent with human review checkpoint |
| 3.2 | 339-346 | M3 Use Cases | 6 use cases: order status, invoice inquiry, billing dispute, return/refund, customer history, product complaint |
| 3.3 | 348-370 | M3 MVP Features | 9 mandatory: Customer Identifier, ERP Fetcher, Issue Classifier, Context Builder, Response Generator, Confidence Score, Human Review Interface, Escalation Path, Graceful Degradation |
| 3.4 | 372-441 | M3 Agent Workflow | 7-node LangGraph flow + State Schema |
| 3.5 | 444-456 | Graceful Degradation | 3 data states: complete / partial / none. Always respond with something useful. |
| 3.6 | 458-475 | Human Review Interface | Mandatory for billing disputes + refund requests + confidence < 70%. 3 actions: Approve / Reject+Regenerate / Escalate |
| 3.7 | 477-493 | M3 Demo Scenarios | 4 scenarios: Order Status / Invoice Dispute / Missing Data / Repeat Issue |
| 3.8 | 495-511 | M3 Data Requirements | Real invoice data from DB + 3 mock tables. Internal consistency mandatory. |
| 5.1 | 589-625 | System Architecture | 3-tier: Frontend (React) ↔ Backend (FastAPI) ↔ Agents (LangGraph) ↔ DB (PostgreSQL + pgvector) ↔ LLM |
| 5.2 | 627-634 | Shared Services | Auth, LLM Client, DB Pool, Logging, Error Handling — shared across ALL modules |
| 6 (Primary Stack) | 639-653 | Tech Stack | Full technology decisions with rationale |
| 6 (LLM Strategy) | 665-673 | LLM Usage | GPT-4o for complex, GPT-4o-mini for classification/simple. Hybrid approach. |
| 7 | 676-697 | MVP Checklist | Everything required in M1 + M3 before demo |

---

## Key Architectural Conclusions (Do Not Re-Derive)

### 1. Single Orchestrator vs. Multi-Agent
**Conclusion:** Single Orchestrator (LangGraph StateGraph) for both M1 and M3.
**Blueprint Location:** Section 2.4, line 119
**Reason:** M1 queries are sequential, not parallel. Simpler debugging and showcasing. Multi-agent only needed if 3+ data sources fetched in parallel simultaneously — not required in MVP.

### 2. Invoice Processing Strategy
**Conclusion:** Invoices from DB tables ONLY. No OCR, no PDF, no file uploads.
**Blueprint Location:** Section 2.6, line 192
**Reason:** Invoices are already structured in DB. Sub-pipeline is a specialized db_query_tool, not a separate module.

### 3. Tax Reasoning Strategy
**Conclusion:** RAG-based using pgvector. 3-5 pre-loaded tax rule documents. Always disclaimer.
**Blueprint Location:** Section 2.7, line 233
**Reason:** Avoids hallucination. Scoped context prevents out-of-scope tax advice.

### 4. Database Access Strategy
**Conclusion:** Read-Only PostgreSQL user for M1. No write operations in M1 agent.
**Blueprint Location:** Section 2.3.1, line 82
**Reason:** Security layer 1 — even if LLM generates DROP TABLE, DB rejects it.

### 5. Output Format Selection
**Conclusion:** Format decided by BOTH intent AND actual data shape (not intent alone).
**Blueprint Location:** Section 2.8, line 250
**Reason:** A question with scalar answer gets Metric Card, not a forced chart.

### 6. M3 Human Review
**Conclusion:** Mandatory for billing_dispute, refund_request, confidence < 0.70.
**Blueprint Location:** Section 3.6, line 460
**Reason:** Financial commitments and promises require human authorization.

### 7. M3 Data Sources
**Conclusion:** Invoice data is REAL from DB. Order/Shipping/History are MOCK structured tables.
**Blueprint Location:** Section 3.4, line 387
**Reason:** Real invoice DB exists. Order/shipping/history requires mock for MVP.

### 8. M2 Status
**Conclusion:** M2 is DEFERRED. Design exists but implementation starts only after M1+M3 are demo-ready with 3+ weeks remaining.
**Blueprint Location:** Section 4 note, line 517
**Reason:** Time constraint — M1+M3 take priority for demo.

### 9. pgvector vs. Qdrant
**Conclusion:** pgvector (PostgreSQL extension). Single DB for both relational and vector.
**Blueprint Location:** Section 6 alternatives, line 649
**Reason:** Simpler deployment, sufficient for MVP scale.

### 10. Frontend Stack
**Conclusion:** React + TypeScript + shadcn/ui + Apache ECharts. NOT Recharts.
**Blueprint Location:** Section 6 Primary Stack, line 644
**Reason:** ECharts supports complex visualizations and Arabic RTL. Enterprise-grade appearance.

---

## M1 Sprint Map (from M1_Sprints.md)

| Sprint | Focus | Duration | Key Deliverable |
|--------|-------|----------|-----------------|
| 0 | DB + Shared Services + Setup | 4 days | DB schema + project skeleton |
| 1 | LangGraph + Intent Classifier | 5 days | Agent classifies and routes |
| 2 | Query Builder — 10 Templates | 5 days | M1 answers financial/operational queries |
| 3 | Invoice Analysis Tool | 4 days | Pattern detection from DB invoices |
| 4 | Tax RAG | 4 days | Tax answers with legal reference |
| 5 | Output Selector (8 types) + Narrative + Anomaly | 5 days | All outputs formatted correctly |
| 6 | Frontend + Integration | 5 days | 5 demo scenarios work end-to-end |
| **Total** | | **~32 days** | |

## M3 Sprint Map (from M3_Sprints.md)

| Sprint | Focus | Duration | Key Deliverable |
|--------|-------|----------|-----------------|
| 0 | Mock Data (order/shipping/history) | 3 days | 3 mock tables, internally consistent |
| 1 | LangGraph + Input Parser + Data Fetcher | 5 days | Agent fetches and scores data |
| 2 | Issue Classifier + Context Builder | 4 days | Issue classified, context structured |
| 3 | Response Generator + Graceful Degradation | 5 days | Draft response + confidence score |
| 4 | Human Review Gate + Escalation + Audit | 4 days | Routing works, audit trail complete |
| 5 | Frontend: Customer Input + Review Interface | 5 days | Two interfaces complete |
| 6 | Integration + 4 Demo Scenarios | 4 days | M3 end-to-end |
| **Total** | | **~30 days** | |

---

## Sections NOT Read (and Why)

| Section | Lines | Reason Skipped |
|---------|-------|----------------|
| M2 (Section 4) | 515-583 | M2 is deferred — files archived. Read only when M2 implementation begins. |
| Section 8 — Presentation Strategy | 704-end | Not relevant to repository architecture. Relevant at demo prep stage. |

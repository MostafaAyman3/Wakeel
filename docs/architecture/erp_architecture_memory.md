# ERP Architecture Memory

This document stores the architecture decisions, module boundaries, repository mappings, and implementation guidelines for the ERP Agentic AI Platform.

---

## 1. Module Boundaries

### Module 1 (M1) — AI ERP Intelligence Agent
* **Goal:** Convert natural language business queries (Arabic/English) into data insights, charts, and summaries from the ERP database.
* **Scope:** Financial queries, operational queries, invoice analyses, tax reasoning, and executive summaries.
* **Orchestration:** Single orchestrator using LangGraph `StateGraph` with localized tools (no multi-agent parallel execution required in MVP).
* **Security:** Read-Only database connection (SELECT privileges only) at the database engine level (first line of defense) and SQL validation layer (second line of defense).

### Module 3 (M3) — Customer Support Agent
* **Goal:** Provide automated customer support, retrieve real/mock shipping and order statuses, and build response drafts for customer queries.
* **Scope:** Status inquiries, billing disputes, shipping issues, refund requests, and complaints.
* **Security & Verification:** Human-in-the-Loop review gate. Mandatory reviews for financial implications (billing disputes, refund requests) or low confidence scores.
* **Robustness:** Graceful degradation for partial/missing data, repeat issue detection, and escalation paths.

### Module 2 (M2) — Purchasing / Inventory Agent
* **Status:** **Deferred**. Implementation is on standby. All code and resources associated with M2 are moved to archived or deferred subdirectories (`m2_deferred`) to avoid cluttering current M1/M3 operations.

---

## 2. Shared Services Boundaries
* **LLM Client:** Unified client instance initializing GPT-4o (for complex reasoning, narrative summaries, and tax retrieval) and GPT-4o-mini (for fast tasks like classification and simple status queries).
* **Database Pool:** SQLAlchemy asynchronous connection pool pointing to PostgreSQL with `pgvector` enabled.
* **Auth Layer:** Simple JWT-based authentication system passing user context into agent state execution.
* **Logging & Observability:** Direct logging of all LLM requests, database queries, tools execution, and user actions.
* **Error Handling:** Standardized middleware formatting database/network errors into human-understandable messages.

---

## 3. Architecture Decisions (ADR Summary)
1. **LangGraph vs Custom Framework:** LangGraph chosen for robust state management and built-in support for human-in-the-loop gates.
2. **PostgreSQL/pgvector vs Separate Vector Database:** Unified database chosen for reduced architectural complexity and streamlined MVP deployment.
3. **Template-First SQL Generation:** Dynamic query generation utilizes a predefined set of 10-15 SQL templates for 80% of common business questions to eliminate SQL injection and syntax errors, reserving LLM-generated SQL only for complex, unmapped requests.

---

## 4. Repository Mapping Summary
* `backend/agents/`: Hosts LangGraph orchestration flows.
  * `m1_intelligence/`: Module 1 logic (graphs, nodes, registry, tools).
  * `m3_support/`: Module 3 logic (graphs, nodes, registry, tools).
  * `m2_deferred/`: Archived/Deferred Module 2 logic.
* `backend/api/v1/`: FastAPI routers.
  * `/query`: M1 endpoint (replaces old copilot endpoint).
  * `/support`: M3 endpoint.
* `frontend/app/`: Next.js page layout.
  * `/m1_intelligence/`: Page for M1 analytics chat.
  * `/m3_support/`: Page for M3 customer support interface + review panel.
* `data/`: Relational seeds, migrations, schemas, and static tax rules vector store contents.

---

## 5. Future Implementation Notes
* Ensure all database calls within agents use the Read-Only user context.
* Tax RAG must return a static disclaimer alongside legally referenceable source chunks.
* M3 input parser must be tested for dual-language parameters extraction (identifying order IDs, names, issue descriptions).

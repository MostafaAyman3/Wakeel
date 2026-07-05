# Wakeel (وكيل) — Agentic AI ERP Intelligence Platform

<div align="center">
  <img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" alt="Next.js" />
  <img src="https://img.shields.io/badge/FastAPI-0.103+-009688?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangGraph-Agentic-blue?logo=openai" alt="LangGraph" />
  <img src="https://img.shields.io/badge/PostgreSQL-17.6-336791?logo=postgresql" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/pgvector-0.8.0-4169E1?logo=postgresql" alt="pgvector" />
  <img src="https://img.shields.io/badge/OpenAI-GPT--4o-412991?logo=openai" alt="OpenAI" />
  <img src="https://img.shields.io/badge/Language-Arabic%20%7C%20English-green" alt="Bilingual" />
</div>

<br />

**🌍 Live Deployment:** [https://wakeel-two.vercel.app/](https://wakeel-two.vercel.app/)  
*(Note: The codebase for this deployed version resides in the `feature/vercel-deployment` branch.)*

**Wakeel** is a production-grade, multi-agent AI platform built on top of ERP data. It combines LangGraph orchestration, GPT-4o reasoning, pgvector semantic search, and a bilingual (Arabic/English) Next.js frontend to deliver three specialized AI copilots: a Financial Intelligence Agent, a Procurement Dashboard, and a Human-in-the-Loop Customer Support Agent.

---

## Table of Contents

- [Modules & Status](#-modules--status)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [API Reference](#-api-reference)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Testing](#-testing)
- [Architectural Constraints](#-architectural-constraints)
- [Roadmap](#-roadmap)

---

## Modules & Status

Wakeel is a unified hub with a global **Module Switcher** in the header for seamless navigation between agents.

| Module | Name | Status | Description |
|--------|------|--------|-------------|
| M1 | Financial Intelligence Agent | **Fully Operational** (Sprints 0–6 Complete) | Context-aware data analyst copilot with NL2SQL, Tax RAG, anomaly detection |
| M2 | Procurement Agent | **Frontend Ready** (Backend Deferred) | Inventory dashboard, RFQ management, pricing recommendations |
| M3 | Customer Support Agent | **Fully Operational** | Human-in-the-Loop support with RAG, escalation detection, ticket management |

---

## Key Features

### M1 — Financial Intelligence Agent
- **Stratified Routing (T0–T6)**: Differentiates greetings, known templates, follow-ups, complex analysis, clarification requests, out-of-scope queries, and M3 delegations
- **Dynamic NL2SQL**: Generates and validates SQL with `sqlglot` AST checks and a repair loop for failed queries
- **Invoice Analysis**: Detects late payment patterns, vendor price spikes, and supplier concentration risk
- **Legal Tax RAG Pipeline**: Semantic search over Egyptian Tax Laws using `text-embedding-3-small` (1536-dim) and `pgvector` with cosine similarity
- **Proactive Anomaly Detection**: Pure-Python thresholds flag expense outliers before rendering
- **Adaptive Output**: Dynamically selects Metric Cards, ECharts (bar/line), Sortable Tables, Narratives, or Alerts
- **Context Persistence**: Structured `analysis_frame` tracking in `conversations` table enables drill-down follow-ups

### M3 — Customer Support Agent
- **4-way Intent Routing**: Greeting / General Knowledge / Customer Issue / Hybrid
- **Dynamic RAG Responses**: Retrieves from support knowledge base and tax law documents
- **Confidence Thresholding**: Auto-escalates low-confidence responses to human review
- **Human Review Gate**: Agents can Approve, Revise, or Escalate every AI draft
- **Mini-RAG Microservice**: Standalone FastAPI service for PDF chunking, embedding, and pgvector retrieval

### Platform-Wide
- **Bilingual UI**: Full RTL (Arabic) and LTR (English) support — Cairo & Inter typography, localized currency formatting
- **JWT Authentication**: Secure login with token refresh
- **Audit Logging**: All actions recorded in `audit_log` table
- **LangSmith Tracing**: Full agent execution traces for debugging

---

## System Architecture

### Macro Architecture — Multi-Agent System

```mermaid
graph TD
    subgraph Frontend [Frontend — Next.js 14]
        Nav[Global Module Switcher]
        UI_M1[M1: Chat Copilot]
        UI_M2[M2: Procurement Dashboard]
        UI_M3[M3: Support Portal]
        Nav --> UI_M1 & UI_M2 & UI_M3
    end

    subgraph Backend [Backend — FastAPI]
        API_M1[POST /api/v1/query]
        API_M2[GET/POST /api/v1/m2/*]
        API_M3[POST /api/v1/support]
        Auth[POST /api/v1/login]
    end

    subgraph Agents [Agent Layer — LangGraph]
        subgraph M1 [M1: Financial Intelligence]
            M1Router{Intent Router T0–T6}
            M1SQL[NL2SQL + Repair Loop]
            M1RAG[Tax RAG Node]
            M1Eval[Result Evaluator]
            M1Out[Output Selector]
        end

        subgraph M3 [M3: Customer Support]
            M3Router{Intent Router}
            M3RAG[RAG Retrieval]
            M3CRM[Data Fetcher]
            M3Review[Human Review Gate]
        end
    end

    subgraph MiniRAG [Mini-RAG Microservice — FastAPI]
        Embed[Embedding Generator]
        Search[pgvector Search]
        Rerank[Re-ranker]
    end

    subgraph Data [Data Layer — Supabase PostgreSQL 17.6]
        DB[(ERP Tables)]
        VectorDB[(pgvector — Tax Laws + Support KB)]
        ConvDB[(conversations)]
    end

    UI_M1 <-->|JSON| API_M1
    UI_M2 <-->|JSON| API_M2
    UI_M3 <-->|JSON| API_M3

    API_M1 <--> M1
    API_M3 <--> M3

    M1SQL <-->|Read-only SQL| DB
    M1RAG <-->|Semantic Search| MiniRAG
    M3RAG <-->|Semantic Search| MiniRAG
    M3CRM <-->|Read/Write| DB
    MiniRAG <--> VectorDB
    M1 --> ConvDB
    M3 --> ConvDB
```

### Micro Architecture — M1 Stratified Routing (v2.0)

```mermaid
graph TD
    API[API: /api/v1/query] --> CtxLoad[Context Loader]
    CtxLoad --> Router{Intent Router}

    Router -->|Greeting| T0[T0: Conversation]
    Router -->|Known Templates| T1[T1: Template Dispatcher]
    Router -->|Follow-ups| T2[T2: Follow-up Resolver]
    Router -->|Complex Analysis| T3[T3: Analytical Planner & NL2SQL]
    Router -->|Missing Info| T4[T4: Clarification]
    Router -->|Out-of-Scope| T5[T5: Reject]
    Router -->|Support Cases| T6[T6: Delegate to M3]

    T1 --> Eval[Result Evaluator]
    T2 -->|Requery| T3
    T2 -->|Direct Reason| OutSelect
    T3 --> Eval

    Eval --> Validate[Validation & Enrichment]
    Validate --> OutSelect[Output Selector]
    OutSelect --> Narrative[Narrative Generator]

    T0 & T4 & T5 & T6 & Narrative --> CtxSave[Context Saver]
```

### M3 Customer Support Workflow

```mermaid
graph TD
    Input[User Query] --> M3Router{Intent Router}

    M3Router -->|Greeting| Greet[Greeting Response]
    M3Router -->|General Knowledge| RAG[RAG Retrieval]
    M3Router -->|Customer Issue| Parse[Input Parser]
    M3Router -->|Hybrid| Both[RAG + Data Fetcher]

    Parse --> Fetch[Data Fetcher]
    Fetch --> Classify[Issue Classifier]
    Classify --> Context[Context Builder]

    RAG & Context & Both --> Draft[Response Generator]
    Draft --> Confidence{Confidence Score}

    Confidence -->|High| AutoSend[Send to Customer]
    Confidence -->|Low| Review[Human Review Gate]

    Review -->|Approve| AutoSend
    Review -->|Revise| Draft
    Review -->|Escalate| Queue[Support Queue]
```

---

## API Reference

### M1 — Financial Intelligence

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/query` | Main M1 query endpoint |

**Request:**
```json
{
  "query": "ما هي الفواتير المتأخرة لهذا الشهر؟",
  "language": "ar",
  "session_id": "uuid-optional"
}
```

**Response:**
```json
{
  "format": "table | metric | chart | narrative | alert",
  "data": [...],
  "chart_config": { "type": "bar", "xKey": "...", "yKey": "..." },
  "narrative": "...",
  "alert": null,
  "session_id": "uuid"
}
```

### M2 — Procurement

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/m2/inventory` | Inventory status with anomaly flags |
| `POST` | `/api/v1/m2/analyze` | Analyze procurement data |
| `GET` | `/api/v1/m2/rfqs` | List RFQ drafts |
| `POST` | `/api/v1/m2/rfqs` | Create new RFQ |
| `GET` | `/api/v1/m2/offers` | Supplier offers |
| `GET` | `/api/v1/m2/pricing` | Pricing recommendations |

### M3 — Customer Support

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/support` | Submit support query |
| `POST` | `/api/v1/support/review` | Human review action (approve/reject/escalate) |

**Request:**
```json
{
  "query": "أين طلبي رقم 1042؟",
  "identifier": "customer-id-optional",
  "session_id": "uuid-optional"
}
```

**Response:**
```json
{
  "draft_response": "...",
  "final_response": "...",
  "confidence_score": 0.87,
  "review_required": false,
  "escalation_needed": false
}
```

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/login` | Obtain JWT token |
| `POST` | `/api/v1/refresh` | Refresh JWT token |
| `GET`  | `/health` | Liveness probe |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 14, React 18, Tailwind CSS 3.4, Apache ECharts, Lucide React |
| **Backend** | Python 3.11+, FastAPI, Uvicorn, SQLAlchemy (async) |
| **AI / Orchestration** | LangGraph, LangChain, OpenAI GPT-4o / GPT-4o-mini |
| **Embeddings** | OpenAI `text-embedding-3-small` (1536 dim) |
| **Database** | Supabase PostgreSQL 17.6, pgvector 0.8.0, asyncpg |
| **Auth** | python-jose, passlib (JWT) |
| **SQL Safety** | sqlglot (AST validation) |
| **Data Processing** | pandas, numpy, pymupdf |
| **Observability** | LangSmith |
| **Infrastructure** | Docker Compose, Nginx |

---

## Project Structure

```text
Wakeel/
├── agents/                    # LangGraph AI agents
│   ├── m1/                   # M1: Financial Intelligence Agent
│   │   ├── graphs/           # m1_graph.py — LangGraph state machine
│   │   ├── nodes/            # Intent router, NL2SQL, Tax RAG, evaluator, output selector
│   │   └── tools/            # db_query_tool, invoice_analysis_tool, nl2sql_generator
│   ├── m2/                   # M2: Procurement Agent (backend archived)
│   ├── m3/                   # M3: Customer Support Agent
│   │   ├── graphs/           # m3_graph.py — Support workflow
│   │   ├── nodes/            # Input parser, data fetcher, classifier, response generator
│   │   └── tools/            # invoice_fetcher_tool, rag_tool
│   ├── prompts/              # LLM prompt templates (intent routers, narratives)
│   ├── shared/               # llm_client.py, db_utils.py, language_tools.py
│   ├── tests/                # pytest integration tests
│   └── requirements.txt
│
├── backend/                   # FastAPI server
│   ├── api/v1/               # Route handlers (m1_query, m2_*, m3_support, auth)
│   ├── core/                 # Config, logging, database connections
│   ├── models/               # SQLAlchemy ORM models
│   ├── repositories/         # Data access layer
│   ├── schemas/              # Pydantic request/response schemas
│   ├── services/             # conversation_service, human_review_service, rag_service
│   ├── middleware/           # Error handling
│   ├── main.py               # FastAPI app entry point
│   └── requirements.txt
│
├── frontend/                  # Next.js 14 bilingual UI
│   ├── app/                  # Pages: /m1, /m2, /m3
│   ├── components/           # Chat UI, Metric Cards, Charts, Tables, Module Switcher
│   ├── hooks/                # Custom React hooks
│   ├── types/                # TypeScript type definitions
│   └── styles/               # Tailwind global styles (RTL/LTR support)
│
├── MIni-RAG-APP-V1/          # Standalone RAG microservice (FastAPI)
│   ├── main.py               # Embedding + pgvector search endpoints
│   └── requirements.txt
│
├── data/                      # Knowledge bases (raw + processed)
│   ├── support_kb/           # Customer support FAQs and policies
│   └── tax_knowledge_base/   # Egyptian tax laws (PDFs + chunked text)
│
├── database/                  # DB migrations and seed scripts
├── deployment/               # Docker configs, Nginx reverse proxy
├── docs/                      # Architecture docs, sprint logs, module maps
├── scripts/                   # E2E tests, DB seeding, RAG ingestion
├── docker-compose.yml
└── README.md
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- Supabase account (or local PostgreSQL 15+ with `pgvector` extension)

### 1. Clone the Repository
```bash
git clone https://github.com/MostafaAyman3/Wakeel.git
cd Wakeel
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```ini
# Database — Supabase Shared Pooler (port 6543 recommended)
DATABASE_URL=postgresql+asyncpg://user:password@host:6543/postgres
READONLY_DB_URL=postgresql+asyncpg://erp_readonly:password@host:6543/postgres
SUPABASE_URL=https://your-project.supabase.co

# OpenAI
OPENAI_API_KEY=sk-your-key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
VECTOR_EMBEDDING_DIMENSION=1536

# Mini-RAG Microservice
MINI_RAG_BASE_URL=http://localhost:8001

# LangSmith (optional — for agent tracing)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_your_key

# JWT
SECRET_KEY=your-secret-key
```

Also create `frontend/.env.local`:

```ini
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 3. Start the Backend

```bash
pip install -r backend/requirements.txt
pip install -r agents/requirements.txt
python -m uvicorn backend.main:app --reload --port 8000
```

Interactive API docs: `http://localhost:8000/docs`

### 4. Start the Mini-RAG Microservice (required for M1 Tax RAG and M3)

```bash
cd MIni-RAG-APP-V1
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8001
```

### 5. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Access the app at `http://localhost:3000/`

---

## Testing

```bash
# M1 — Full pipeline (Sprints 1–6)
python scripts/test_e2e_all_sprints.py

# RAG — Semantic search and LLM extraction
python scripts/test_rag.py

# M3 — Escalation, routing, and Human-in-the-Loop workflows
python scripts/test_unified_support.py

# Unit tests (individual sprints)
pytest agents/tests/test_sprint3.py
pytest agents/tests/test_sprint5.py
```

---

## Architectural Constraints

- All AI queries to the ERP database **must** use `READONLY_DB_URL` — no INSERT, UPDATE, or DELETE from agent nodes.
- No direct schema modifications from agents. All DB access goes through explicit tool nodes with schema catalog validation.
- SQL queries are validated via `sqlglot` AST parsing before execution to prevent injection and schema violations.
- Odoo and OCR modules have been archived; the system integrates directly with Supabase PostgreSQL.

---

## Database Schema (Key Tables)

| Table | Purpose |
|-------|---------|
| `conversations` | Multi-turn chat history with structured `analysis_frame` metadata |
| `tax_chunks` | Egyptian tax law chunks with 1536-dim pgvector embeddings |
| `inventory_alerts` | M2 inventory anomalies with JSONB metadata |
| `audit_log` | Full action audit trail (entity_type, action, details) |
| `invoices`, `invoice_items` | ERP invoice data (read-only for M1) |
| `orders`, `order_items` | ERP order data (read-only for M1) |
| `customers`, `vendors` | Party master data |
| `products`, `inventory` | Product catalog and stock levels |
| `payments`, `transactions` | Financial transaction records |

---

## Roadmap

- **M2 Backend**: Un-archive and integrate the Procurement LangGraph agent with the existing Next.js dashboard (inventory analysis, supplier scoring, RFQ automation).
- **M3 Enhancements**: Expand the CRM integration for deeper customer data access and add proactive ticket resolution suggestions.
- **Auth Hardening**: Implement role-based access control (RBAC) to scope M1 read-only access per user.
- **Streaming Responses**: Add Server-Sent Events (SSE) to stream LLM output tokens to the frontend in real time.

---

*For the full project evolution history, see [`docs/progress/agent_execution_log_updated.md`](docs/progress/agent_execution_log_updated.md).*

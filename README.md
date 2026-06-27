# Wakeel (وكيل) - Smart ERP System

<div align="center">
  <img src="https://img.shields.io/badge/Next.js-14-black?logo=next.js" alt="Next.js" />
  <img src="https://img.shields.io/badge/FastAPI-0.103+-009688?logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/LangGraph-Agentic-blue?logo=openai" alt="LangGraph" />
  <img src="https://img.shields.io/badge/PostgreSQL-17.6-336791?logo=postgresql" alt="PostgreSQL" />
</div>

<br />

Wakeel is a comprehensive Agentic AI platform built on top of ERP data. It leverages Large Language Models (GPT-4o / GPT-4o-mini), LangGraph for complex orchestration, and a modern web stack to provide intelligent insights, proactive anomaly detection, and interactive bilingual (Arabic/English) interfaces.

## 📋 Table of Contents
- [🚀 The Modules & Current Status](#-the-modules--current-status)
- [✨ Key Features](#-key-features)
- [🏗 System Architecture (v2.0 - Stratified Routing)](#-system-architecture-v20---stratified-routing)
- [🛠 Tech Stack](#-tech-stack)
- [📂 Project Structure](#-project-structure)
- [🏁 Getting Started](#-getting-started)
- [🛣 Future Roadmap](#-future-roadmap)

---

## 🚀 The Modules & Current Status

Wakeel is designed as a unified hub hosting multiple specialized AI agents. You can navigate between these modules seamlessly using the global **Module Switcher** built into the unified Header.

- 🤖 **M1 (Intelligence Agent / Financial Analyst)**: **Fully Operational (Sprints 0-6 Completed).**
  - Features a true **Context-Aware Data Analyst Copilot** architecture.
  - Stratified Routing (T0-T6), dynamic NL2SQL querying with repair loops, complex invoice analysis, multi-stage Tax RAG pipeline, and proactive anomaly detection.
  - Full interactive Next.js Chat UI with rich visual outputs (Metric Cards, ECharts, Sortable Tables).

- 📦 **M2 (Procurement Agent)**: **Frontend Dashboard Integrated.**
  - M2 provides a procurement dashboard focusing on inventory status, active alerts, RFQ drafts, and pricing recommendations.
  - The UI layout is established and accessible via the global Module Switcher. *(Note: The backend AI orchestration for M2 is currently deferred to future iterations).*

- 🎧 **M3 (Customer Support Agent)**: **Infrastructure Ready.**
  - Sprint 0 completed (Database mock tables for customer interactions and shipments).
  - Placeholder UI integrated into the global navigation. Development of the human review and support routing agent is up next.

---

## ✨ Key Features

- **Global Unified Interface**: A sleek, glassmorphism-styled Module Switcher enables instant navigation between the Financial Analyst, Procurement, and Customer Support modules.
- **Dynamic Intent Classification**: Automatically routes queries and detects language (Arabic/English).
- **SQL Query Generation & Execution**: Safely builds and executes read-only SQL queries against ERP data using optimized templates and `sqlglot` AST validation.
- **Advanced Invoice Analysis**: Detects patterns such as late payments, vendor price increases, and concentration risk.
- **Legal Tax RAG Pipeline**: Uses `text-embedding-3-small` and `pgvector` to semantically search Egyptian Tax laws with hybrid retrieval and reranking.
- **Proactive Anomaly Detection**: Pure-Python thresholds detect out-of-bounds expenses and data anomalies before displaying them to the user.
- **Adaptive Output Formatting**: Intelligently selects the best format to display data: Metric Cards, Sortable Tables, ECharts (Bar/Line), Narratives, or Alerts.
- **Premium Bilingual UI**: Full RTL and LTR support with localized currency/number formatting and a cohesive typography system (Cairo & Inter).

---

## 🏗 System Architecture

Wakeel is architected as a Multi-Agent system. The platform consists of a global macro-architecture that routes traffic to specialized LangGraph agents, and a highly detailed micro-architecture (Stratified Routing) specifically for the M1 copilot.

### 1. Macro Architecture (Multi-Agent System)

```mermaid
graph TD
    %% Frontend Layer
    subgraph Frontend [Frontend - Next.js]
        GlobalNav[Global Module Switcher]
        
        subgraph Views [Module Interfaces]
            UI_M1[M1: Chat Copilot]
            UI_M2[M2: Procurement Dashboard]
            UI_M3[M3: Support Portal]
        end
        GlobalNav --> Views
    end

    %% Backend API Layer
    subgraph Backend [Backend - FastAPI]
        API_M1["/api/v1/m1_query"]
        API_M2["/api/v1/m2/*"]
        API_M3["/api/v1/m3/*"]
    end

    %% Agentic Layer
    subgraph Agents [Agent Layer - LangGraph]
        
        subgraph M1_Agent [M1: Financial Intelligence]
            Router{Intent Router}
            T1_3[T1-T3: Analytical & SQL]
            T4_6[T4-T6: Out-of-Scope & Support]
            Router --> T1_3 & T4_6
        end

        subgraph M2_Agent [M2: Procurement Agent]
            Inventory[Inventory Analysis]
            Pricing[Pricing Engine]
            Alerts[Anomaly Alerts]
        end

        subgraph M3_Agent [M3: Customer Support]
            Ticketing[Support Ticketing]
            HumanReview[Human-in-the-loop]
        end

    end

    %% Database Layer
    subgraph Data [Data Layer - Supabase]
        DB[(PostgreSQL 17.6)]
        VectorDB[(pgvector: Tax Laws)]
    end

    %% Connections
    UI_M1 <-->|JSON| API_M1
    UI_M2 <-->|JSON| API_M2
    UI_M3 <-->|JSON| API_M3

    API_M1 <--> M1_Agent
    API_M2 <--> M2_Agent
    API_M3 <--> M3_Agent

    T1_3 <-->|Read-only SQL| DB
    Inventory <-->|Read-only SQL| DB
    Ticketing <-->|Read/Write| DB
    T1_3 <-->|Semantic Search| VectorDB
```

### 2. Micro Architecture: M1 Stratified Routing (v2.0)

For the M1 Intelligence Agent, the platform utilizes a "Stratified Routing" model. Every request is routed into specific execution tiers (T0 to T6), decoupling conversational intent from database analytical execution. This ensures that analytical complexity is bounded, safer, and supports dynamic valid NL2SQL execution for complex queries.

```mermaid
graph TD
    %% Backend Layer
    subgraph Backend [Backend - FastAPI]
        API[API Router<br>/api/v1/m1_query]
    end

    %% Agent Layer (LangGraph v2.0)
    subgraph Agents [M1 Agent Layer - Stratified LangGraph]
        ContextLoad[Context Loader]
        Router{Intent Router}
        
        T0[T0: Conversation]
        T1[T1: Template Dispatcher]
        T2[T2: Follow-up Resolver]
        T3[T3: Analytical Planner & Executor]
        T4[T4: Clarification]
        T5[T5: Out of Scope]
        T6[T6: M3 Delegation]
        
        Eval[Result Evaluator]
        Validate[Validation & Enrichment]
        OutSelect[Output Selector]
        Narrative[Narrative Generator]
        ContextSave[Context Saver]

        ContextLoad --> Router
        Router -->|Greeting| T0
        Router -->|Known Templates| T1
        Router -->|Follow-ups| T2
        Router -->|Complex Analysis| T3
        Router -->|Missing Slots| T4
        Router -->|Unsupported| T5
        Router -->|Support Cases| T6

        T1 --> Eval
        T2 -->|Requery| T3
        T2 -->|Reason| OutSelect
        T3 --> Eval
        
        Eval --> Validate
        Validate --> OutSelect
        OutSelect --> Narrative
        
        T0 --> ContextSave
        T4 --> ContextSave
        T5 --> ContextSave
        T6 --> ContextSave
        Narrative --> ContextSave
    end

    %% Connections
    API <--> ContextLoad
```

### 🔄 Architectural Advancements (Copilot Shift)

Version 2.0 transforms Wakeel from a basic "ERP Chatbot" to a **Context-Aware Data Analyst Copilot**:
- **Execution Tiers (T0-T6)**: Differentiates between greetings (T0), templates (T1), follow-ups (T2), and complex multi-step analytics (T3).
- **Central Query Gateway & NL2SQL Repair Loop**: Safely generates and repairs dynamic SQL for out-of-bounds questions while strictly adhering to read-only DB permissions and an authorized schema catalog.
- **Result Evaluation**: A `ResultEvaluatorNode` verifies if returned data semantically covers the user's question before responding, preventing hallucinations.
- **Context Persistence**: Uses structured `analysis_frame` tracking instead of raw text history in the `conversations` table, allowing the agent to remember precise metrics, dimensions, and filters for seamless drill-down.

---

## 🛠 Tech Stack

- **Frontend**: Next.js 14, React, Tailwind CSS 3.4, Apache ECharts, Lucide Icons
- **Backend**: Python 3.11, FastAPI, SQLAlchemy (Async)
- **AI & Orchestration**: LangGraph, LangChain, OpenAI (GPT-4o, GPT-4o-mini)
- **Database**: Supabase PostgreSQL 17.6 (via Pooler), `pgvector` 0.8.0
- **Observability**: LangSmith

---

## 📂 Project Structure

```text
.
├── agents/             # LangGraph agent definitions, nodes, tools, and prompts
│   ├── m1/             # M1 Intelligence Agent (Stratified Copilot Architecture)
│   ├── m2/             # M2 Procurement Agent (Backend Deferred/Archived)
│   ├── m3/             # M3 Customer Support Agent (Placeholders ready)
│   └── shared/         # Shared LLM clients & infrastructure
├── backend/            # FastAPI backend, API routes, Auth, Database connections
├── frontend/           # Next.js 14 bilingual interface (Chat, M2 Dashboards, Global Nav)
├── data/               # Raw and processed knowledge base documents (e.g., Tax laws)
├── docs/               # Architecture maps, execution logs, progress tracking
└── scripts/            # Testing suites, DB seeding, and RAG ingestion scripts
```

---

## 🏁 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 20+
- Supabase account (or local PostgreSQL with pgvector)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/MostafaAyman3/Wakeel.git
   cd Wakeel
   ```

2. **Environment Setup**
   Create a `.env` file in the root directory. You will need:
   ```ini
   # Database (Supabase Shared Pooler recommended - port 6543)
   DATABASE_URL=postgresql://user:password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
   READONLY_DB_URL=postgresql://erp_readonly:password@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
   SUPABASE_URL=https://your-project.supabase.co
   
   # OpenAI & Vector Setup
   OPENAI_API_KEY=sk-your-key
   OPENAI_EMBEDDING_MODEL=text-embedding-3-small
   VECTOR_EMBEDDING_DIMENSION=1536
   
   # LangSmith (Optional for Tracing)
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=lsv2_pt_your_key
   ```
   *(Ensure `frontend/.env.local` is also configured for Next.js variables like `NEXT_PUBLIC_API_BASE_URL`)*.

3. **Start the Backend**
   ```bash
   pip install -r backend/requirements.txt
   pip install -r agents/requirements.txt
   python -m uvicorn backend.main:app --reload --port 8000
   ```
   *You can view the interactive API documentation at `http://localhost:8000/docs`.*

4. **Start the Frontend**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. Access the interface at `http://localhost:3000/`.

---

## 🧪 Testing

The repository includes extensive testing scripts:
- **E2E Integration**: Run `python scripts/test_e2e_all_sprints.py` to verify the entire M1 pipeline (Sprints 1-5).
- **RAG Testing**: Run `python scripts/test_rag.py` to test semantic search and LLM extraction.
- **Unit Tests**: Check individual sprint tests (e.g., `test_sprint3.py`, `test_sprint5.py`).

---

## 📜 Architectural Constraints
- All AI queries to the database **must** use the `READONLY_DB_URL` connection.
- No direct schema modifications from agents. All DB access is secured via explicit tool nodes.
- Odoo and OCR modules have been archived in favor of direct Supabase PostgreSQL integration.

---

## 🛣 Future Roadmap
- **M3 (Customer Support)**: Implement the 7 backend nodes (InputParser, DataFetcher, etc.) and wire `m3_graph.py`. Connect to the existing frontend placeholder.
- **M2 (Procurement)**: Un-archive and integrate the procurement LangGraph backend with the currently active Next.js M2 dashboard.

---
*Refer to `docs/progress/agent_execution_log_updated.md` for the comprehensive history of the project's evolution.*

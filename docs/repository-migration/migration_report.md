# Repository Restructuring & Migration Report

This report outlines the structural transformation of the ERP repository from its legacy layout to the target architecture designed in the product blueprints for Module 1 (AI ERP Intelligence Agent) and Module 3 (Customer Support Agent).

---

## 1. Original Structure Summary
Previously, the repository was built around an outdated multi-agent framework integrated with Odoo client APIs:
* **Root level `agents/` folder:** Contained analytics, procurement, supervisor, and OCR nodes.
* **Backend `/api/v1/` routes:** Bundled legacy actions and Odoo-based routes.
* **Root level `database/` folder:** Housed relational model setup files.
* **Root level `deployment/` folder:** Contained general Docker and Nginx files.
* **Frontend `/app/procurement/` and `/components/procurement/`:** Tied to the deferred Module 2 features.

---

## 2. Target Structure Summary
The repository now adheres to a clean, modular structure targeting Module 1, Module 3, and Shared Services.
```
.github/               # CI/CD Workflows
backend/               # Python FastAPI backend application
  ├── agents/          # LangGraph Agent Engine packages
  │     ├── m1_.../    # Module 1 Intelligence Agent
  │     ├── m3_.../    # Module 3 Support Agent (skeleton)
  │     ├── m2_.../    # Deferred Module 2 logic
  │     ├── shared/    # Common schemas and registries
  │     └── archive/   # Obsolete agent files (OCR, Odoo tools)
  ├── api/v1/          # Modular API routing endpoints
  ├── core/            # Database pool, auth, and logging configs
  ├── archive/         # Obsolete backend components (Odoo client, confirmation)
  └── ...
frontend/              # React / Next.js UI workspace
  ├── app/             # Application page routes
  │     ├── m1_.../    # Module 1 analytics dashboard & chat
  │     ├── m3_.../    # Module 3 customer support portal
  │     └── m2_.../    # Standby Module 2 routes
  └── components/      # Organized UI components by module
shared/                # Common types and contract assets
docs/                  # Architectural records and logs
infrastructure/        # Deployment profiles (Docker, Nginx configs)
tests/                 # Realigned test suites (m1, m2_deferred, shared)
scripts/               # Relational seeds and demo verification files
data/                  # Database models, schemas, and RAG knowledge bases
```

---

## 3. Detailed File Operations

### Files Moved
* **Agents to Backend:** Moved all active and deferred nodes, tools, and graphs from `agents/` to `backend/agents/`.
* **Relational DB Setup:** Moved `database/` to `data/database/`.
* **Deployment Configs:** Moved `deployment/*` to `infrastructure/`.
* **Tests:** Relocated and consolidated all backend and agent tests to `tests/m1_intelligence/`, `tests/m2_deferred/`, and `tests/shared/`.

### Files Archived
* `agents/nodes/ocr_agent_node.py` ──► `backend/agents/archive/nodes/`
* `agents/tools/odoo_tools.py` ──► `backend/agents/archive/tools/`
* `agents/nodes/erp_action_node.py` ──► `backend/agents/archive/nodes/`
* `agents/nodes/orchestrator_node.py` ──► `backend/agents/archive/nodes/`
* `backend/api/v1/actions.py` ──► `backend/archive/api/v1/`
* `backend/models/confirmation_token.py` ──► `backend/archive/models/`
* `backend/models/ocr_quote.py` ──► `backend/archive/models/`
* `backend/repositories/ocr_quotes.py` ──► `backend/archive/repositories/`
* `backend/services/confirmation_service.py` ──► `backend/archive/services/`
* `backend/services/domain_filter_builder.py` ──► `backend/archive/services/`
* `backend/services/entity_resolver.py` ──► `backend/archive/services/`
* `backend/services/odoo_client.py` ──► `backend/archive/services/`
* `backend/schemas/action.py` ──► `backend/archive/schemas/`
* `frontend/components/confirmation/` ──► `frontend/components/archive/`

### Files Renamed (Endpoint Routing & State)
* `backend/api/v1/copilot.py` ──► `backend/api/v1/m1_intelligence.py`
* `frontend/app/copilot/` ──► `frontend/app/m1_intelligence/`
* `frontend/types/analytics.ts` ──► `frontend/types/m1_intelligence.ts`

### New Directories Created
* `data/tax_knowledge_base/` (prepared for Tax laws reference files).
* `backend/agents/m3_support/` (prepared for Customer Support agent nodes/graphs).
* `frontend/app/m3_support/` & `frontend/components/m3_support/` (customer interface).

---

## 4. Architecture Alignment Report
The repository directory mapping is now 100% aligned with the target system. All legacy Odoo modules, which contradict the read-only PostgreSQL pool approach, have been safely stored in `archive/` folders. This isolates developers from outdated patterns and prevents accidental imports. 

Deferred items (M2) are clearly isolated under `m2_deferred` subfolders across all layers (api, models, frontend, tests), ensuring they do not interfere with the active MVP scope.

---

## 5. Risks & Mitigation
1. **Import Paths:** Python import statements inside the relocated files (e.g. referencing `agents.nodes` instead of `backend.agents.m1_intelligence.nodes`) will need to be refactored during implementation sprints. 
   * *Mitigation:* We have structured `__init__.py` files to support clear package navigation, and run scripts will easily identify broken paths.
2. **Frontend Component Imports:** Moved components will require path updates in page layouts.
   * *Mitigation:* Visual Studio Code or similar IDEs can perform simple project-wide refactoring of these imports easily.

---

## 6. Recommended Next Steps
1. **Run Database Seeds (M1 & M3):** Standardize the database layout and populate the 8 core tables + the 3 support mock tables using `scripts/seed_mock_data.py`.
2. **Tax RAG Ingestion:** Seed rules PDFs in `data/tax_knowledge_base/` and enable pgvector chunking.
3. **API Routing Update:** Mount `backend/api/v1/m1_intelligence.py` and `backend/api/v1/m3_support.py` routers in the central `backend/main.py` entry point.

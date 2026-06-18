# M3 Sprint 1 — Execution Log

> Dedicated detailed record for **M3 (Customer Support Agent) — Sprint 1**:
> LangGraph Skeleton + Input Parser + Data Fetcher + Completeness Check.
> Summary entry also exists in `agent_execution_log.md` (Step 25).
> Date: 2026-06-18 · Branch: `m3_s1_kk53`

---

## 1. Sprint Goal

Build the first slice of the M3 LangGraph pipeline that:

1. Parses a free-form customer message (AR/EN).
2. Extracts an identifier (`order_id` / `invoice_id` / `customer_id`) + issue description.
3. Fetches data from 4 sources **in parallel**.
4. Scores data completeness + confidence.
5. Returns structured JSON through `POST /api/v1/support`.

**Out of scope (later sprints):** issue classification (S2), response generation (S3),
human-review gate + escalation + audit trail (S4), frontend (S5), demo scenarios (S6).

---

## 2. Key Decisions

| # | Decision | Why |
|---|----------|-----|
| 1 | Kept existing `agents/m3/` + `backend/` structure (rejected the generic `app/` tree) | Consistency with M1; reuse shared infra; avoid an orphaned parallel codebase |
| 2 | Fetch order/shipping/history from **real Supabase tables** (rejected in-memory mock dicts) | Sprint 0 already seeded these tables (orders=250, shipments=189, customer_interactions=32), consistent by `customer_id`; keeps the 4 demo scenarios real |
| 3 | State is a `TypedDict` (not Pydantic) | Matches `M1State` + LangGraph partial-update semantics (nodes return partial dicts). Pydantic used at the API boundary only |
| 4 | All lookups by `display_id` (ORD-…/INV-…/CUST-…), never raw UUID | Customer-facing references are display ids |
| 5 | `identifier` is **optional** in the request | Honors both the template (query-only) and the sprint plan ({query, identifier}); parser extracts it when omitted |
| 6 | M3 uses the read-write engine (`get_db_session`) | `readonly_db_url` is documented as M1-exclusive; M3 queries are still SELECT-only |
| 7 | Agent errors degrade to escalation, never HTTP 500 | Graceful-degradation principle (blueprint §3.5) — never show a technical error to the customer |

### Table-name mapping (spec → real DB)
| Sprint spec | Actual table |
|-------------|--------------|
| `order_status` | `orders` |
| `shipping` | `shipments` |
| `customer_history` | `customer_interactions` |

---

## 3. Files Created / Updated

### Shared (reusable)
- **`agents/shared/language.py`** — `detect_language(text)` → "ar"/"en" via Arabic Unicode range (U+0600–U+06FF). Single source of truth for new modules.
- **`agents/shared/db_utils.py`** — `jsonify_row` / `jsonify_rows`: convert DB rows to JSON-safe dicts (datetime/date → isoformat, Decimal → float, UUID → str).

### M3 core
- **`agents/m3/schemas/m3_state.py`** — `M3State` TypedDict (12 fields, `total=False`), `IssueType` + `IdentifierType` literals, and `build_initial_state(query, identifier, language)` default factory.
- **`agents/prompts/input_parser.py`** — bilingual `INPUT_PARSER_SYSTEM_PROMPT` with extraction rules + AR/EN examples.
- **`agents/m3/nodes/input_parser_node.py`** — `parse_input(state)`:
  - language auto-detect
  - trusts a valid API-supplied identifier (skips LLM)
  - GPT-4o-mini structured extraction (`ParsedInput`)
  - regex fallback (`ORD|DEL|TRK` → order_id, `INV` → invoice_id, `CUST` → customer_id)
  - no identifier found → `escalation_needed = True`
- **`agents/m3/tools/invoice_fetcher_tool.py`** — `fetch_invoice(identifier)`: REAL invoice from `invoices` + `customers`, one parametrized SELECT per identifier type, aliased to `{ invoice_id, amount, status, customer_id, customer_name, … }`.
- **`agents/m3/tools/mock_data_tool.py`** — `fetch_order` (orders), `fetch_shipping` (shipments), `fetch_history` (customer_interactions, multiple rows for repeat-issue detection in S3). Each self-contained for all 3 identifier types.
- **`agents/m3/nodes/data_fetcher_node.py`** — `fetch_data(state)`: runs the 4 fetchers concurrently with `asyncio.gather(..., return_exceptions=True)`; missing source → `None`; one failure never crashes the pipeline; assembles `fetched_data = { invoice, order, shipping, history }`.
- **`agents/m3/nodes/data_completeness_node.py`** — `check_completeness(state)`: all 4 present → 1.0; some → 0.5 + `missing_fields`; none → 0.0 + `escalation_needed=True`. `confidence_score = data_completeness` (Sprint 1). `get_confidence_label(score)` → High (≥0.8) / Medium (≥0.5) / Low.
- **`agents/m3/graphs/m3_graph.py`** — `build_support_graph()` compiles `START → input_parser → data_fetcher → completeness_check → END`; exports compiled `support_graph`.
- **`backend/api/v1/m3_support.py`** — `POST /api/v1/support` wired to `support_graph`. Optional `identifier`. Returns:
  ```json
  { "draft_response", "confidence_score", "confidence_label",
    "review_required", "escalation_needed", "issue_type",
    "transparency_data": { "invoice", "order", "shipping", "history" },
    "missing_fields" }
  ```
  `transparency_data` is internal-only (TODO: Sprint 5 review UI — never shown to the customer).
- **`agents/m3/{nodes,schemas,graphs,tools}/__init__.py`** — package inits.
- **`scripts/test_m3_sprint1.py`** — integration test (5 cases), forces UTF-8 stdout for Arabic on Windows.

---

## 4. Pipeline Flow

```
POST /api/v1/support  { query, identifier? }
        │
        ▼
  build_initial_state()  →  M3State (all defaults)
        │
        ▼
  input_parser     →  language + customer_identifier + issue_description
        │              (escalate if no identifier)
        ▼
  data_fetcher     →  asyncio.gather(fetch_invoice, fetch_order,
        │                            fetch_shipping, fetch_history)
        │              fetched_data = { invoice, order, shipping, history }
        ▼
  completeness_check → data_completeness, confidence_score,
        │               missing_fields, escalation_needed
        ▼
  SupportResponse (JSON)
```

---

## 5. Verification

- **Deps installed:** `pip install -r backend/requirements.txt` on Python 3.10 (the terminal default).
- **Graph compiles:** nodes = `['__start__', 'input_parser', 'data_fetcher', 'completeness_check', '__end__']`.
- **Live integration test (real GPT-4o-mini + Supabase): 5/5 PASSED**

| Test | Identifier | Result |
|------|-----------|--------|
| AR order status — identifier in free text | `ORD-2024-1567` (parsed) | ✅ 4 sources, confidence High |
| EN invoice dispute — explicit identifier | `INV-0001` | ✅ found |
| AR repeat issue — customer history | `CUST-001` | ✅ 4 sources, history present |
| Missing data — non-existent reference | `DEL-999` | ✅ graceful degradation + escalation |
| No identifier at all | — | ✅ auto-escalate |

- **Test fixture fix:** `INV-890` (a blueprint illustration) does not exist in the seed; real invoices are `INV-0001`–`INV-0318`. Changed the dispute test to `INV-0001`. The code itself was correct — it returned escalation for the non-existent id, which is the intended graceful-degradation behavior.

### How to run
```bash
pip install -r backend/requirements.txt        # once
python scripts/test_m3_sprint1.py              # integration test
uvicorn backend.main:app --reload              # run the API → POST /api/v1/support
```

---

## 6. Known Notes / Follow-ups

- On Windows, after the test prints results you may see `RuntimeError: Event loop is closed` SSL noise — cosmetic (asyncpg + ProactorEventLoop teardown), unrelated to correctness. Suppress with `2>$null` (PowerShell) / `2>/dev/null` (bash) if desired.
- `draft_response` is intentionally empty in Sprint 1 (ResponseGenerator is Sprint 3); `review_required` defaults False (HumanReviewGate is Sprint 4).
- `ORD-2024-1567` exists in the seed with a linked invoice, shipment, and history — demo Scenario 1 is ready out of the box.
- Next: **Sprint 2 — IssueClassifierNode + ContextBuilderNode**.

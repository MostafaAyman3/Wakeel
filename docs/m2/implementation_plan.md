# M2 — Implementation Plan (Sprint 0 Deliverable)

> **Status:** Sprint 0 complete — architecture locked, schema ready, seed data defined.
> **Last updated:** 2026-06-22
> **Author:** Architect (Sprint 0)

---

## 1. Architecture Decisions (Final)

### 1.1 Single Responsibility Split

| Layer | Tool | Responsibility |
|-------|------|----------------|
| **Brain + State** | LangGraph | All detection logic, LLM calls, human approval, state persistence |
| **Transport + Scheduling** | n8n | Daily cron trigger, outbound RFQ emails, WhatsApp notifications |
| **API Gateway** | FastAPI | Bridge between Frontend/n8n and the LangGraph |
| **State Persistence** | AsyncPostgresSaver | Pausing the graph between RFQ send and offer receipt |

**Why this split matters:** n8n must NOT make business logic decisions. It only calls `POST /api/v1/m2/analyze` and sends emails. LangGraph owns everything else. This prevents duplication of approval logic.

### 1.2 One Graph, Two Paths

```
InventoryCheckNode
       │
       ├─ detection_type ∈ {low_stock, predicted_shortage}
       │         └──► AlertGeneratorNode → RFQBuilderNode → HumanApprovalNode
       │
       └─ detection_type ∈ {slow_moving, near_expiry}
                 └──► PricingAdvisorNode
```

The router is a simple conditional edge function in `m2_graph.py` that reads `state["detection_type"]`.

### 1.3 Async Loop Architecture (Phase 2)

```
RFQ approved → graph sets thread_id → AsyncPostgresSaver checkpoints → PAUSE
                                                    ⋮
supplier reply → POST /api/v1/m2/offers → server fetches thread_id from rfqs table
               → graph.aresume(thread_id) → OfferAnalysisNode runs → HumanApprovalNode
```

The graph does NOT poll for offers. It sleeps in the checkpointer until explicitly resumed.

### 1.4 DB Schema — Key Design Choices

- All PKs are `uuid` (consistent with existing project schema — NOT integer).
- The new M2 inventory fields (`lead_time_days`, `expiry_date`, `avg_daily_sales`) are added to the existing `inventory` table, NOT `products`, because they are operational/logistics data.
- `inventory_alerts.rfq_id` is a deferred FK (set after the RFQ is created, not at alert creation time).
- `rfqs.vendor_ids` is a `uuid[]` array — allows sending one RFQ to multiple vendors in one shot.

---

## 2. Node Responsibilities (Detailed)

### 2.1 InventoryCheckNode (no LLM)

**File:** `agents/m2/nodes/inventory_check_node.py`
**Sprint:** 1

**What it does:**
1. Queries `inventory JOIN products` for all active products.
2. For each product, runs these checks in order (first match wins):
   - `quantity <= reorder_point` → `low_stock`
   - `avg_daily_sales > 0 AND quantity / avg_daily_sales < lead_time_days` → `predicted_shortage`
   - `avg_daily_sales > 0 AND turnover_rate < SLOW_MOVING_THRESHOLD (0.5/month)` → `slow_moving`
   - `expiry_date IS NOT NULL AND expiry_date <= today + NEAR_EXPIRY_WINDOW (30 days)` → `near_expiry`
3. Computes: `days_until_stockout`, `turnover_rate`, `suggested_quantity`.
4. Writes detected products to `state["flagged_products"]` and `state["scan_summary"]`.
5. Saves an `inventory_alerts` row for each flagged product.

**SQL used:**
```sql
SELECT
    i.id            AS inv_id,
    p.id            AS product_id,
    p.sku, p.name, p.name_ar, p.category,
    i.quantity,
    i.reorder_point,
    i.lead_time_days,
    i.avg_daily_sales,
    i.expiry_date,
    -- Compute avg daily sales from last 90 days of orders
    COALESCE(
        (SELECT SUM(oi.quantity)::float / 90
         FROM order_items oi
         JOIN orders o ON o.id = oi.order_id
         WHERE oi.product_id = p.id
           AND o.order_date >= now() - interval '90 days'),
        i.avg_daily_sales  -- fallback to cached value
    ) AS computed_daily_sales
FROM inventory i
JOIN products p ON p.id = i.product_id
WHERE p.is_active = true
ORDER BY p.category, p.name;
```

**Thresholds (constants in the node file):**
```python
SLOW_MOVING_THRESHOLD = 0.5   # turnover_rate per month
NEAR_EXPIRY_WINDOW    = 30    # days
MIN_AVG_DAILY_SALES   = 0.01  # avoid division by zero
```

---

### 2.2 AlertGeneratorNode (LLM: gpt-4o-mini)

**File:** `agents/m2/nodes/alert_generator_node.py`
**Sprint:** 2

**Input:** `state["current_product"]`, `state["detection_type"]`, `state["days_until_stockout"]`, `state["user_context"]["language"]`

**Output:** `state["explanation"]` — a concise, action-oriented alert message.

**Prompt behavior:** Uses `llm_fast` (gpt-4o-mini). The prompt includes structured data and asks for a single sentence in the user's language. No long explanations — just what the manager needs to decide.

**Example outputs:**
- AR: `"رصيد لابتوب Dell XPS 13 وصل لـ 3 وحدات — أقل من الحد الأدنى (10). مطلوب طلب 20 وحدة فوراً."`
- EN: `"Dell XPS 13 stock is at 3 units (reorder point: 10). Order 20 units immediately."`

---

### 2.3 RFQBuilderNode (LLM: gpt-4o)

**File:** `agents/m2/nodes/rfq_builder_node.py`
**Sprint:** 2

**Input:** `state["current_product"]`, `state["suggested_quantity"]`, `state["explanation"]`, `state["user_context"]["language"]`

**Output:** `state["rfq_draft"]` — a complete, professional RFQ email body.

**AR example structure:**
```
الموضوع: طلب عرض سعر — [اسم المنتج]

السادة / شركة [اسم المورد] المحترمين،

يسعدنا التواصل معكم بخصوص حاجتنا لـ [الكمية] وحدة من [اسم المنتج] (SKU: [SKU]).
...
مع التحية،
فريق المشتريات
```

**Saves to DB:** Creates an `rfqs` row with `status='draft'` and stores `rfq_id` in state.

---

### 2.4 HumanApprovalNode (interrupt — no LLM)

**File:** `agents/m2/nodes/human_approval_node.py`
**Sprint:** 6

**Mechanism:** LangGraph `interrupt()` — graph execution stops and waits.

**Appears twice in the Procurement path:**
1. Before sending the RFQ (manager reviews draft).
2. After offer analysis (manager selects the recommended vendor).

**Resume trigger:** `POST /api/v1/m2/rfqs/{id}/approve` with `{"status": "approved"|"rejected", "notes": "..."}`.

---

### 2.5 PricingAdvisorNode (LLM: gpt-4o)

**File:** `agents/m2/nodes/pricing_advisor_node.py`
**Sprint:** 5 (Phase 1)

**Input:** `state["current_product"]`, `state["detection_type"]` (slow_moving or near_expiry), computed metrics.

**Output:** `state["pricing_recommendation"]` — recommendation for the manager (NOT automatic price change).

---

### 2.6 OfferAnalysisNode (LLM: gpt-4o)

**File:** `agents/m2/nodes/offer_analysis_node.py`
**Sprint:** 7 (Phase 2)

**Scoring formula:**
```
score = (price_score × 0.50) + (lead_time_score × 0.30) + (terms_score × 0.20)
```
Where each sub-score is normalized 0–1 relative to the other offers.

---

## 3. API Design

### Phase 0 Endpoints

#### `GET /api/v1/m2/inventory`
Returns current inventory status for all products.

**Response schema:**
```json
{
  "products": [
    {
      "product_id": "uuid",
      "sku": "ELC-001",
      "name": "Dell XPS 13",
      "name_ar": "لابتوب ديل",
      "category": "Electronics",
      "quantity": 3,
      "reorder_point": 10,
      "lead_time_days": 7,
      "avg_daily_sales": 1.5,
      "days_until_stockout": 2.0,
      "status": "low_stock",
      "expiry_date": null
    }
  ],
  "summary": {
    "total": 25,
    "low_stock": 2,
    "predicted_shortage": 2,
    "slow_moving": 2,
    "near_expiry": 2,
    "safe": 17
  }
}
```

#### `POST /api/v1/m2/analyze`
Triggers the LangGraph for all flagged products.

**Request body:**
```json
{
  "trigger_source": "manual",
  "language": "ar-EG"
}
```

**Response:** `scan_summary` + list of generated `alerts` + list of `rfq_drafts`.

---

## 4. n8n Workflow Design

### Workflow 1 — Daily Cron Analysis

```
Cron (08:00 daily)
  → HTTP Request Node: POST /api/v1/m2/analyze
      body: { "trigger_source": "cron", "language": "ar-EG" }
  → IF Node: response.scan_summary.low_stock_count > 0 OR predicted_shortage_count > 0
  → WhatsApp Node / Email Node:
      "تقرير المخزون الصباحي: {N} منتج يحتاج طلب شراء. افتح لوحة التحكم للمراجعة."
```

**Credential needed:** WhatsApp Business API or SMTP.

### Workflow 2 — RFQ Send on Approval

```
Webhook Node (receives POST from FastAPI when RFQ status → 'approved')
  body: { rfq_id, vendor_emails: [...], subject, body_text }
  → FOR EACH vendor_email:
      → Email Node: Send RFQ to vendor
  → HTTP Request: POST /api/v1/m2/rfqs/{rfq_id}/mark-sent
      (updates rfqs.status = 'sent' + sets thread_id checkpoint)
```

---

## 5. Voice Integration Design (Phase 3)

### Flow

```
User speaks → Browser captures audio (MediaRecorder API)
→ Blob uploaded to POST /api/v1/m2/voice
→ FastAPI: OpenAI Whisper (whisper-1) → transcribed text
→ POST /api/v1/m2/analyze with trigger_source="voice"
→ Response JSON → OpenAI TTS (tts-1, voice="nova")
→ Audio stream returned to browser → plays automatically
```

### Language Detection

The STT (Whisper) auto-detects the language. The transcribed text is inspected:
- If Arabic characters present → `language = "ar-EG"`
- Otherwise → `language = "en"`

This is passed as `user_context.language` to all downstream nodes.

### Demo Questions

| Arabic (عامية) | English |
|---------------|---------|
| "إيه المنتجات اللي مخزنها وصل الحد الأدنى؟" | "Which products are low on stock?" |
| "إيه المنتجات اللي هتخلص قبل ما الطلبية توصل؟" | "What's at risk of stockout before next shipment?" |
| "في منتجات قريبة تنتهي صلاحيتها؟" | "Any products near expiry?" |

---

## 6. Prompt Design

### 6.1 AlertGeneratorNode Prompt

```python
ALERT_PROMPT = """
You are an inventory management assistant for an Egyptian ERP system.
Generate a concise, action-oriented alert message for the manager.

Product: {name} ({name_ar}) | SKU: {sku} | Category: {category}
Issue type: {detection_type}
Current quantity: {quantity} | Reorder point: {reorder_point}
Days until stockout: {days_until_stockout:.1f} | Lead time: {lead_time_days} days

Language: {language}  (ar-EG = Egyptian Arabic dialect; en = English)

Rules:
- Maximum 2 sentences
- Include the exact numbers
- Mention the recommended action (reorder / discount / urgent check)
- Egyptian Arabic: use informal dialect (عامية مصرية), not Modern Standard Arabic
- Do NOT use markdown formatting
"""
```

### 6.2 RFQBuilderNode Prompt

```python
RFQ_PROMPT = """
You are drafting a professional Request-For-Quotation email on behalf of
an Egyptian company's procurement department.

Product: {name} ({name_ar}) | SKU: {sku}
Quantity needed: {suggested_quantity} {unit}
Reason: {explanation}

Language: {language}

Write a complete, formal email body (no subject line).
Include:
  - Polite greeting
  - Clear product specification (name, SKU, quantity)
  - Request for: unit price, total price, delivery timeline, payment terms
  - Deadline for response (3 business days)
  - Professional closing

For Arabic: use formal Modern Standard Arabic (فصحى مهنية) for business emails,
NOT Egyptian dialect. Dialect is for internal chat only.
"""
```

### 6.3 PricingAdvisorNode Prompt

```python
PRICING_PROMPT = """
You are a pricing advisor for an Egyptian retail/wholesale ERP system.
Recommend a pricing action for the manager to take.

Product: {name} ({name_ar}) | SKU: {sku}
Issue: {detection_type}
Current quantity: {quantity} | Avg daily sales: {avg_daily_sales}/day
{expiry_info}
{turnover_info}

Language: {language}

Provide:
1. Recommended discount percentage (or "no discount needed")
2. Justification (1-2 sentences)
3. Expected outcome

This is a RECOMMENDATION for the manager. Do NOT say prices will be changed
automatically. Manager must approve all pricing changes.
"""
```

---

## 7. Testing Strategy

### Unit Tests (per node — Sprint 1 onwards)

Each node gets a test in `agents/tests/` with:
- Happy path with mock DB results
- Edge case: zero avg_daily_sales (division by zero guard)
- Edge case: product with NULL expiry_date
- Language switching (ar-EG vs en)

### Integration Test (Sprint 2 onwards)

`tests/integration/test_m2_pipeline.py`:
1. Call `POST /api/v1/m2/analyze` with trigger_source="manual"
2. Assert 4 alerts created (one per scenario from seed data)
3. Assert 2 RFQ drafts generated (for low_stock and predicted_shortage products)
4. Assert 2 pricing recommendations generated

### Checkpointer Test (Sprint 6)

Verify graph can be paused and resumed:
1. Run analyze → get rfq_id
2. Approve RFQ → graph pauses at checkpoint
3. Simulate server restart
4. POST /api/v1/m2/offers with same rfq_id
5. Assert graph resumes correctly and OfferAnalysisNode runs

---

## 8. File Map (complete)

```
agents/m2/
├── schemas/
│   └── m2_state.py          ← Sprint 0 ✅
├── tools/
│   └── inventory_tools.py   ← Sprint 1 (SQL queries)
├── nodes/
│   ├── inventory_check_node.py   ← Sprint 1
│   ├── alert_generator_node.py   ← Sprint 2
│   ├── rfq_builder_node.py       ← Sprint 2
│   ├── human_approval_node.py    ← Sprint 6
│   ├── pricing_advisor_node.py   ← Sprint 5
│   └── offer_analysis_node.py    ← Sprint 7
└── graphs/
    └── m2_graph.py               ← Sprint 2

backend/api/v1/
├── m2_inventory.py    ← Sprint 1 (GET /inventory)
├── m2_analyze.py      ← Sprint 2 (POST /analyze)
├── m2_rfqs.py         ← Sprint 6 (POST /rfqs/{id}/approve)
├── m2_offers.py       ← Sprint 7 (POST /offers)
├── m2_pricing.py      ← Sprint 5 (GET /pricing)
└── m2_voice.py        ← Sprint 8 (POST /voice)

backend/models/
├── m2_inventory_alert.py  ← Sprint 1
├── m2_rfq.py              ← Sprint 2
└── m2_supplier_offer.py   ← Sprint 7

database/migrations/m2/
├── 001_create_inventory_alerts.sql        ← Sprint 0 ✅
├── 002_create_rfqs.sql                    ← Sprint 0 ✅
├── 003_create_supplier_offers.sql         ← Sprint 0 ✅
└── 004_alter_inventory_add_m2_fields.sql  ← Sprint 0 ✅

database/seeds/
└── m2_seed_inventory.py  ← Sprint 0 ✅

frontend/app/m2/
└── page.tsx              ← Sprint 3

frontend/components/m2/
├── InventoryTable.tsx           ← Sprint 3
├── AlertsPanel.tsx              ← Sprint 3
├── RFQDraftView.tsx             ← Sprint 3
├── ApprovalButton.tsx           ← Sprint 3
├── OfferComparisonView.tsx      ← Sprint 7
├── PricingRecommendationsPanel.tsx ← Sprint 5
└── VoiceAssistantPanel.tsx      ← Sprint 8

n8n/workflows/
├── m2_workflow1_daily_analysis.json  ← Sprint 9
└── m2_workflow2_send_rfq.json        ← Sprint 9
```

---

## 9. DoD Checklist — Sprint 0

- [x] Unified architecture documented (this file + M2_Sprints.md §2)
- [x] `m2_state.py` — all fields defined with types and docstrings
- [x] `001_create_inventory_alerts.sql` — idempotent, uuid FKs, indexes
- [x] `002_create_rfqs.sql` — idempotent, uuid FKs, thread_id column
- [x] `003_create_supplier_offers.sql` — idempotent, uuid FKs
- [x] `004_alter_inventory_add_m2_fields.sql` — adds lead_time_days, expiry_date, avg_daily_sales
- [x] `m2_seed_inventory.py` — covers all 4 detection scenarios
- [x] n8n workflow design documented (§4)
- [x] Voice integration design documented (§5)
- [x] All prompts drafted (§6)
- [x] Node responsibilities defined (§2)
- [x] API surface defined (§3)

**Next step:** Run migrations against the DB, run the seed script, then begin Sprint 1.

```bash
# Apply migrations (run in order):
psql $DATABASE_URL -f database/migrations/m2/001_create_inventory_alerts.sql
psql $DATABASE_URL -f database/migrations/m2/002_create_rfqs.sql
psql $DATABASE_URL -f database/migrations/m2/003_create_supplier_offers.sql
psql $DATABASE_URL -f database/migrations/m2/004_alter_inventory_add_m2_fields.sql

# Seed demo data:
python -m database.seeds.m2_seed_inventory
```

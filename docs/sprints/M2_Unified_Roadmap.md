# M2 — خطة التنفيذ الموحّدة: Purchasing & Inventory Agent

> **الهدف من هذا الملف:** دمج الخطتين (`M2_Sprints.md` النسخة المصغرة + `M2_Full_Build_Sprints_V2.md` الطبقات الإضافية) في **خارطة طريق واحدة متكاملة وواقعية** — بترقيم Sprints متّصل، وبنية معمارية موحّدة، ونموذج بيانات واحد.
> **المرجع:** `ERP_Agentic_AI_Blueprint.md` — القسم 4 (سطر 515–583)، مع إعادة استخدام مكوّنات من M1 و M3.
> **الفريق:** Architect + Developer A + Developer B (عمل متوازٍ).

---

## 1. فلسفة البناء (Build Philosophy)

البناء **تدريجي (incremental)** على مراحل، كل مرحلة تُركَّب فوق سابقتها — وليست إعادة بناء:

| المرحلة | المحتوى | تُبنى فوق | Shippable؟ |
|---------|---------|-----------|:----------:|
| **Phase 0 — Spine** | البنية الأساسية: Inventory Check + Alerts + RFQ Draft + Dashboard (متزامن، خطّي) | من الصفر | ✅ نعم (هذا هو الـ MVP) |
| **Phase 1 — Intelligence + Pricing** | كشف ذكي استباقي (slow-moving / near-expiry / shortage prediction) + مسار التسعير | توسعة `InventoryCheckNode` | ✅ نعم |
| **Phase 2 — Async Procurement Loop** | اعتماد بشري (interrupt) + إرسال + Checkpointer + استقبال عروض + تحليلها | امتداد مسار الـ RFQ | ✅ نعم |
| **Phase 3 — Interaction + Automation** | مساعد صوتي (Speech-to-Speech) + أتمتة n8n (cron + webhooks) | فوق كل ما سبق | ✅ نعم |
| **Phase 4 — Integration** | ربط end-to-end + اختبار ثبات + Demo كامل | الكل | 🎯 العرض النهائي |

**مبدأ التوقيت:** الـ **Phase 0 لوحده قابل للشحن (shippable MVP)**. لو الوقت المتبقّي **أكثر من 3 أسابيع**، تُضاف باقي المراحل بالترتيب أعلاه. لو الوقت ضيّق، يُكتفى بـ Phase 0 (+ جزء من Phase 1).

**خيط ثابت عبر كل الموديول:** كل المخرجات النصية (التنبيهات، مسودة الـ RFQ، الرد الصوتي، تحليل العروض) تحترم لغة المستخدم — **مصري عامية أو إنجليزي** — وتُحدَّد من `user_context.language`.

---

## 2. البنية المعمارية الموحّدة (Unified Architecture)

```
المُشغّلات (Triggers)
   ├─ [n8n Cron]  →  فحص يومي صباحي (POST /analyze, trigger_source="cron")
   └─ [Dashboard "افحص الآن" / Voice]  →  فحص يدوي (POST /analyze, trigger_source="manual")
                         │
                         ▼
   ┌─────────────────────────────────────────────────────────┐
   │  InventoryCheckNode   (SQL + Intelligence — بدون LLM)    │
   │  يقرأ المخزون + يحسب turnover + days_until_stockout +     │
   │  expiry window، ثم يتفرّع حسب detection_type:             │
   └─────────────────────────────────────────────────────────┘
        ├─ low_stock / predicted_shortage ───────►  مسار الشراء (Procurement)
        └─ slow_moving / near_expiry ────────────►  مسار التسعير (Pricing)

── مسار الشراء (Procurement) ───────────────────────────────────────────
   AlertGenerator (LLM) → RFQBuilder (LLM) → HumanApprovalNode (interrupt)
        │  عند الاعتماد: status=sent + CHECKPOINT (thread_id محفوظ)
        ▼
   إرسال للمورد عبر [n8n Email Node]  ──►  الـ graph يقف
        ⋮   (انتظار ساعات/أيام — AsyncPostgresSaver يحفظ الحالة في DB)
        ▼   رد المورد ──► POST /api/v1/m2/offers ──► استئناف نفس thread_id
   OfferAnalysisNode (LLM) → يوصّي بالأفضل + مبرر → HumanApprovalNode (نهائي)

── مسار التسعير (Pricing) ──────────────────────────────────────────────
   PricingAdvisorNode (LLM) → توصية خفض سعر للمدير → مراجعة في Dashboard

── طبقة التفاعل (Interaction) ──────────────────────────────────────────
   VoiceAssistantPanel: STT → POST /analyze → نتيجة → TTS (عامية/إنجليزي)

── طبقة الأتمتة (Automation: n8n) ──────────────────────────────────────
   Workflow 1: Cron يومي → فحص → WhatsApp/Email digest للمدير
   Workflow 2: Webhook استلام RFQ معتمد → Email Node → إرسال للمورد
```

**تقسيم المسؤوليات (مهم — يحلّ ازدواج الآليات):**
- **n8n = طبقة النقل والجدولة (Transport + Scheduling) فقط:** الجدولة اليومية (cron) + إرسال إيميلات الـ RFQ للموردين + إشعارات WhatsApp.
- **LangGraph = العقل والحالة (Brain + State):** كل المنطق والكشف والتنبيهات والتحليل + حفظ حالة الـ async loop عبر الـ Checkpointer.
- **الاعتماد البشري واحد فقط:** `HumanApprovalNode` (نمط `interrupt`، مُعاد استخدامه من HumanReviewGate في M3). زر **"Approve & Send"** في الواجهة هو الطرف الأمامي الذي يستأنف الـ graph الموقوف — وليس آلية اعتماد منفصلة.

---

## 3. نموذج البيانات الموحّد (Unified Data Model)

### 3.1 جداول **موجودة بالفعل** في قاعدة البيانات (مؤكَّدة من ملف `erp_data_expansion2.sql`)

| الجدول | الفائدة لـ M2 |
|--------|----------------|
| `products` | الأصناف (مرجع `product_id`، `sku`؛ الفئات: ELC/FRN/MNT/OFS/SVC) |
| `vendors` | الموردون (10 موردين VND-001…VND-010) — أساس الـ RFQ والعروض |
| `customers` | العملاء (مرجع، يدعم تحليل الطلب) |
| `orders` + `order_items` | تاريخ المبيعات ← لحساب `avg_daily_sales` و shortage prediction |
| `invoices` + `invoice_items` | فواتير بيع (99) **وشراء (31، مربوطة بـ `vendor_id`)** ← turnover + تاريخ التوريد + أداء الموردين |
| `transactions` | الحركات المالية (type/category/amount) ← turnover والتحليل المالي |
| `payments` | المدفوعات |
| `shipments` | الشحنات (carrier/shipped_date/delivered_date) ← يمكن اشتقاق **مدة التوريد الفعلية** لتعبئة `lead_time_days` بواقعية |
| `customer_interactions` | تفاعلات العملاء (لـ M3، غير مطلوب مباشرة لـ M2) |

### 3.2 جداول **مطلوب إنشاؤها** لـ M2 (غير موجودة)

| الجدول | المرحلة | الوصف |
|--------|---------|-------|
| `inventory_alerts` | Phase 0 → يُوسَّع في Phase 1 | تخزين التنبيهات؛ `alert_type` enum = `low_stock \| predicted_shortage \| slow_moving \| near_expiry` |
| `rfqs` | Phase 2 | طلبات الشراء (مع `thread_id` و `status`) |
| `supplier_offers` | Phase 2 | عروض الموردين المستلمة |
| `pricing_recommendations` *(اختياري)* | Phase 1 | توصيات التسعير (بديل: تُخزَّن داخل `inventory_alerts`) |

```sql
-- inventory_alerts
CREATE TYPE alert_type_enum AS ENUM ('low_stock','predicted_shortage','slow_moving','near_expiry');
CREATE TABLE inventory_alerts (
  id              SERIAL PRIMARY KEY,
  product_id      INT REFERENCES products(id),
  alert_type      alert_type_enum NOT NULL,
  message         TEXT,
  metadata        JSONB,          -- days_until_stockout, turnover_rate, ...
  status          VARCHAR(20) DEFAULT 'open',
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- rfqs
CREATE TYPE rfq_status_enum AS ENUM ('draft','approved','sent','analyzing','closed');
CREATE TABLE rfqs (
  rfq_id      SERIAL PRIMARY KEY,
  product_id  INT REFERENCES products(id),
  vendor_ids  INT[],              -- الموردون المُرسَل إليهم
  quantity    INT,
  status      rfq_status_enum DEFAULT 'draft',
  thread_id   VARCHAR(128),       -- مفتاح الـ checkpointer (لاستئناف الـ graph)
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- supplier_offers
CREATE TABLE supplier_offers (
  offer_id        SERIAL PRIMARY KEY,
  rfq_id          INT REFERENCES rfqs(rfq_id),
  vendor_id       INT REFERENCES vendors(id),
  price           DECIMAL(12,2),
  lead_time_days  INT,
  terms           TEXT,
  raw_message     TEXT,
  received_at     TIMESTAMPTZ DEFAULT now()
);
```

### 3.3 إضافات على جدول `products`

| الحقل | النوع | الوصف | يُستخدم في |
|------|------|-------|-----------|
| `lead_time_days` | int | مدة التوريد المتوقعة | shortage prediction |
| `turnover_rate` | float | معدل الدوران (محسوب/مخزَّن) | slow-moving |

> ⚠️ **انظر قسم "فجوة بيانات المخزون" أدناه** — هذه الإضافات لا تكفي وحدها؛ هناك حقول مخزون أساسية يجب التحقق من وجودها وتعبئتها قبل أن يعمل الكشف.

---

## 4. LangGraph State Schema (الموحّد)

```python
{
  trigger_source:        "cron" | "manual",
  flagged_products:      list,
  current_product:       dict,
  detection_type:        "low_stock" | "predicted_shortage" | "slow_moving" | "near_expiry",
  consumption_rate:      float,    # avg_daily_sales
  turnover_rate:         float,
  days_until_stockout:   float,
  suggested_quantity:    int,
  explanation:           str,
  # مسار الشراء
  rfq_draft:             str,
  rfq_id:                str,
  thread_id:             str,
  # مسار التسعير
  pricing_recommendation: str,
  # تحليل العروض
  supplier_offers:       list,
  recommended_offer:     dict,
  approval_status:       str,
  user_context:          dict      # { language: "ar-EG" | "en", role, ... }
}
```

### الـ Nodes
| Node | LLM؟ | الوصف |
|------|:----:|-------|
| `InventoryCheckNode` | ❌ | SQL + Intelligence: stock<reorder + turnover + near-expiry + shortage prediction، ثم يتفرّع حسب `detection_type` |
| `AlertGeneratorNode` | ✅ GPT-4o-mini | تحويل النواقص لتوصيات استباقية مقروءة |
| `RFQBuilderNode` | ✅ GPT-4o | مسودة إيميل رسمي للمورد (عامية/إنجليزي) |
| `HumanApprovalNode` | — (interrupt) | اعتماد بشري؛ نفس pattern M3؛ يظهر مرتين (قبل الإرسال + بعد التحليل) |
| `PricingAdvisorNode` | ✅ GPT-4o | توصية خفض سعر للبطيء/قريب الانتهاء (للمدير فقط، ليس dynamic pricing) |
| `OfferAnalysisNode` | ✅ GPT-4o | مقارنة العروض (سعر + مدة + شروط) والتوصية بالأفضل مع مبرر |

---

## 5. واجهة الـ API الموحّدة (API Surface)

| Method | Endpoint | المرحلة | الوظيفة |
|--------|----------|---------|---------|
| `GET`  | `/api/v1/m2/inventory` | Phase 0 | حالة المخزون الحالية + النواقص |
| `POST` | `/api/v1/m2/analyze` | Phase 0 | تشغيل مسار الـ agent → تنبيهات + مسودات RFQ (يستقبل `trigger_source`) |
| `POST` | `/api/v1/m2/rfqs/{id}/approve` | Phase 2 | اعتماد RFQ → استئناف الـ graph الموقوف + إطلاق إرسال n8n |
| `POST` | `/api/v1/m2/offers` | Phase 2 | استقبال عروض المورد → تخزين → استئناف نفس `thread_id` → تحليل |
| `GET`  | `/api/v1/m2/pricing` | Phase 1 | توصيات التسعير للمراجعة |
| `POST` | `/api/v1/m2/voice` | Phase 3 | (اختياري) استقبال نص الصوت وتمريره للـ analyze |
| Webhook | n8n endpoints | Phase 3 | cron daily check + RFQ send |

---

## 6. خطة الـ Sprints الموحّدة (ترقيم متّصل)

> **التوزيع المتوازي:** Architect يبدأ، ثم Dev A و Dev B يعملان على مسارين متوازيين قدر الإمكان. ⟂ = يمكن العمل عليه بالتوازي مع السابق.

### Phase 0 — Spine (الـ MVP القابل للشحن)

#### Sprint 0 — Architecture & Planning — *Architect* — 3 أيام
- البنية المعمارية الموحّدة + `m2_state.py` schema + مهام الـ Nodes.
- تصميم آلية n8n + تجربة الصوت + Prompts (عامية مصرية + إنجليزي).
- كتابة `implementation_plan.md` التفصيلي + إنشاء جداول `inventory_alerts` (وseed بيانات المخزون — انظر قسم الفجوة).
- **DoD:** مسار هندسي واضح + schema جاهز + بيانات مخزون تجريبية في الـ DB.

#### Sprint 1 — Backend & Inventory Check — *Dev A* — 4 أيام ⟂ (مع Sprint 2)
- `agents/m2/schemas/m2_state.py`.
- `inventory_tools.py` (PostgreSQL: قراءة الأرصدة + تحديد ما وصل لـ reorder).
- `inventory_check_node.py` (أول خطوة، بدون LLM).
- `GET /api/v1/m2/inventory`.
- **DoD:** Endpoint يرجّع حالة المخزون ويكتشف النواقص من الـ DB.

#### Sprint 2 — LLM Nodes: Alerts & RFQ Draft — *Dev B* — 5 أيام ⟂ (مع Sprint 1)
- `alert_generation_node.py` (توصيات استباقية).
- `rfq_builder_node.py` (مسودة إيميل رسمي، عامية/إنجليزي).
- ربط الـ Nodes → `agents/m2/graphs/m2_graph.py`.
- `POST /api/v1/m2/analyze`.
- **DoD:** agent يعمل في الـ Backend ويولّد تنبيهات + مسودات RFQ.

#### Sprint 3 — Frontend Dashboard — *Dev A + Dev B (مشترك)* — 5 أيام
- **Dev A:** `frontend/app/m2/page.tsx` + `InventoryTable.tsx` (ألوان حالة المخزون: منخفض/آمن).
- **Dev B:** `AlertsPanel.tsx` + `RFQDraftView.tsx` مع زر "Approve & Send" (في هذه المرحلة: يعلّم الـ RFQ كـ approved فقط — يُرقّى لاحقاً في Phase 2).
- دمج المكوّنات مع endpoints الـ Sprints 1 و 2.
- **DoD:** لوحة تحكم M2 متكاملة تعرض الأرصدة والتنبيهات والمسودات.

> 🚢 **نقطة الشحن (Ship point):** بنهاية Sprint 3 يكون لدينا MVP قابل للعرض. ما بعده يُضاف لو الوقت يسمح.

---

### Phase 1 — Inventory Intelligence + Pricing

#### Sprint 4 — Inventory Intelligence Layer — *Dev A* — 4 أيام
- حساب `turnover = المبيعات ÷ متوسط المخزون` (من `transactions`/`invoices`/`order_items`).
- Slow-moving + Near-expiry detection (فحص `expiry_date` ضمن نافذة N يوم).
- Shortage prediction: `days_until_stockout = stock_level ÷ avg_daily_sales` (يفلاج **قبل** الوصول لـ reorder).
- توسعة `alert_type` enum + تفريع `InventoryCheckNode` حسب `detection_type`.
- Seed بيانات mock لكل سيناريو كشف.
- **DoD:** كشف proactive بأربعة أنواع تنبيه.

#### Sprint 5 — Pricing Advisor — *Dev B* — 3 أيام
- `PricingAdvisorNode` (GPT-4o): توصية خفض سعر مدروسة للمدير.
- منطق التفريع: نقص/توقّع نقص ← الشراء؛ بطيء/قريب انتهاء ← التسعير.
- تخزين التوصيات + لوحة تسعير منفصلة في الـ Dashboard + `GET /api/v1/m2/pricing`.
- **DoD:** مسار التسعير يعمل بالتوازي مع الشراء.

---

### Phase 2 — Async Procurement Loop (الجزء الأصعب)

#### Sprint 6 — Human Approval + Send + Checkpointer — *Dev B* — 4 أيام
- `HumanApprovalNode` (interrupt) — إعادة استخدام HumanReviewGate من M3.
- إعداد `AsyncPostgresSaver` على PostgreSQL.
- جدول `rfqs` (مع `thread_id`, `status`).
- آلية الإرسال عند الاعتماد → `status=sent` + checkpoint + إطلاق webhook الإرسال (n8n لاحقاً، mock الآن).
- التأكد أن الـ graph يقف ويُستأنف بعد restart.
- **DoD:** اعتماد بشري + إرسال + حالة محفوظة تدوم عبر إعادة التشغيل.

#### Sprint 7 — Offer Intake + Offer Analysis — *Dev B (تحليل) + Dev A (واجهة الإدخال)* — 4 أيام
- جدول `supplier_offers` + `POST /api/v1/m2/offers` (للـ demo: **form + mock هجين**).
- استئناف الـ graph على `thread_id` عند وصول العروض.
- `OfferAnalysisNode` (GPT-4o): مقارنة + توصية بمبرر لغوي.
- العودة للاعتماد البشري النهائي.
- **DoD:** الـ async loop مكتمل + تحليل عروض يعمل.

---

### Phase 3 — Interaction + Automation

#### Sprint 8 — Speech-to-Speech Integration — *Dev A* — 4 أيام ⟂ (مع Sprint 6/7)
- `VoiceAssistantPanel.tsx`.
- Speech-to-Text لالتقاط سؤال المدير (مثل: "إيه المنتجات اللي ناقصة في المخزن؟").
- إرسال النص للـ Backend (`/analyze`) لتشغيل الـ agent — **بما فيه التنبيهات الذكية الجديدة** من Phase 1.
- Text-to-Speech (OpenAI Audio API أو ElevenLabs) للرد بالعامية المصرية أو الإنجليزية بشكل طبيعي.
- **DoD:** مساعد مخزون تفاعلي بالأوامر والردود الصوتية.

#### Sprint 9 — n8n Automation & Webhooks — *Dev B* — 4 أيام
- **Workflow 1:** Cron يومي صباحي → استدعاء `POST /analyze` → رسالة WhatsApp/Email للمدير بالتنبيهات (**متضمّنة shortage prediction الاستباقي** من Phase 1).
- **Workflow 2:** استلام webhook الـ RFQ المعتمد (من Sprint 6) → Email Node → إرسال للمورد الحقيقي.
- ربط الـ webhooks بآلية الإرسال والجدولة في الـ Backend.
- **DoD:** نظام مخزون آلي بالكامل (جدولة + إرسال) دون تدخل يدوي إضافي.

---

### Phase 4 — Integration

#### Sprint 10 — Integration + Full Demo — *Dev A + Dev B (مشترك)* — 3 أيام
- End-to-end كامل: كشف ← تنبيه ← RFQ ← اعتماد ← إرسال (n8n) ← [وقفة/checkpoint] ← عروض ← تحليل ← توصية.
- اختبار ثبات الـ checkpointer (استئناف بعد تأخير/restart).
- تشغيل كل سيناريوهات العرض (انظر §8).
- **DoD:** M2 يعمل end-to-end، جاهز للعرض.

---

## 7. الجدول الزمني (Timeline)

| Phase | Sprints | الجهد (dev-days) |
|-------|---------|:---:|
| 0 — Spine | S0–S3 | 17 |
| 1 — Intelligence + Pricing | S4–S5 | 7 |
| 2 — Async Loop | S6–S7 | 8 |
| 3 — Interaction + Automation | S8–S9 | 8 |
| 4 — Integration | S10 | 3 |
| **إجمالي الجهد** | | **≈ 43 يوم-عمل** |

**حساب المسار الحرج بمطوّرَيْن متوازيين:**
- **Phase 0 (MVP) لوحده:** S0 (3) + S1∥S2 (5) + S3 (5) ≈ **13 يوم تقويمي** ← هذا هو "الحد الأدنى القابل للشحن".
- **المشروع كامل (بالتوازي):** ≈ **26–28 يوم تقويمي** (مع تداخل مسار Dev A الصوتي مع مسار Dev B للـ async loop).

> **توزيع متوازي:** S1∥S2، وكذلك S8 (Dev A) يمكن أن يجري بالتوازي مع S6/S7 (Dev B). الموازنة الدقيقة للأحمال بين المطوّرَيْن قرار فريق.

---

## 8. سيناريوهات العرض (Demo Scenarios)

| # | السيناريو | المتوقع | المرحلة |
|---|-----------|---------|:---:|
| 1 | Reorder hit | صنف تحت reorder ← تنبيه + مسودة RFQ | 0 |
| 2 | Shortage prediction | صنف فوق reorder لكن `days_until_stockout` صغير ← تنبيه استباقي | 1 |
| 3 | Slow-moving → Pricing | صنف بطيء الدوران ← توصية خفض سعر | 1 |
| 4 | Near-expiry → Pricing | صنف قرب انتهاؤه ← توصية تصريف | 1 |
| 5 | Async procurement | RFQ يُعتمد ويُرسَل (n8n) ← الـ graph يقف ← إدخال عروض ← استئناف ← تحليل | 2 |
| 6 | Offer Analysis | 3 عروض موردين ← توصية بالأفضل مع مبرر | 2 |
| 7 | Checkpointer resilience | استئناف نفس الـ RFQ بعد restart بدون فقد حالة | 2 |
| 8 | Voice | المدير يسأل صوتياً "إيه الناقص؟" ← رد صوتي (عامية/إنجليزي) | 3 |
| 9 | n8n daily digest | cron صباحي ← WhatsApp/Email بالتنبيهات الاستباقية | 3 |

---

## 9. المتطلبات والاعتماديات (Prerequisites)

- **Shared Services (مُعاد استخدامها من M1/M3، لا تُبنى من جديد):** Auth · LLM Client · DB Pool · Logging · Error Handling (Blueprint §5.2).
- **مفاتيح/بيئة:** OpenAI API key · مفتاح TTS (ElevenLabs اختياري) · مثيل n8n قيد التشغيل · اتصال PostgreSQL (للبيانات + الـ checkpointer).
- **إعادة استخدام:** نمط `HumanReviewGate` من M3 → `HumanApprovalNode`.

---

## 10. الحدود والمخاطر (Limitations & Risks)

**الحدود (تُفصح في العرض):**
- الـ async loop يعتمد على إدخال عروض يدوي/mock — لا تكامل بريد وارد فعلي في الـ MVP (الإرسال الصادر عبر n8n حقيقي).
- توصيات التسعير استرشادية للمدير، ليست dynamic pricing.
- shortage prediction خطّي بسيط (`stock ÷ avg_daily_sales`)، ليس نموذج ML.
- turnover محسوب من بيانات تاريخية موجودة (mock حيث يلزم).

**سجل المخاطر:**
| المخاطرة | الأثر | التخفيف |
|----------|------|---------|
| الـ Async Checkpointer (أصعب جزء معماري) | فقد حالة الـ RFQ بين الإرسال والرد | `AsyncPostgresSaver` + اختبار restart مبكر في Sprint 6 |
| **غياب بيانات المخزون** (انظر تقرير الـ SQL) | الكشف لا يعمل أصلاً | تعبئة حقول `products` + seed قبل Sprint 1 |
| ازدواج آلية الإرسال (n8n مقابل الـ graph) | تعارض/تكرار | الفصل الواضح: n8n نقل، LangGraph حالة (§2) |
| جودة الـ TTS بالعامية | رد صوتي غير طبيعي | اختبار مزوّدَيْن (OpenAI/ElevenLabs) واختيار الأفضل |

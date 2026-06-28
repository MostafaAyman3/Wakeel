# M2 — خطة التنفيذ: Full Build (الطبقات الإضافية فوق النسخة المصغرة)

> **المرجع:** `ERP_Agentic_AI_Blueprint.md` — القسم 4.3 (سطر 532–583)
> **العلاقة بالملف الآخر:** هذا الملف يمتد `M2_Sprints.md` (النسخة المصغرة). الـ minimal هو الأساس (الـ spine)، وهذه طبقات تُركَّب فوقه — وليست إعادة بناء.
> **تنبيه الوقت:** البلوبرنت يحدد الـ Full Build فقط إذا تبقّى **أكثر من 3 أسابيع**. الموصى به: بناء الـ minimal أولاً (shippable) ثم إضافة هذه الطبقات على مراحل.

---

## نطاق هذه المرحلة (Scope)

تغطّي هذه الخطة الميزات الستة المؤجلة، مجمّعة في **3 طبقات** فوق الـ minimal:

| الطبقة | الميزات | فوق ماذا تُبنى؟ |
|--------|---------|----------------|
| **1 — Inventory Intelligence** | Slow-moving · Near-expiry · Shortage prediction | توسعة `InventoryCheckNode` |
| **2 — Pricing Advisor** | توصيات خفض السعر للبطيء/قريب الانتهاء | فرع موازٍ جديد |
| **3 — Procurement Async Loop** | Async Supplier Loop · Offer Analysis · PostgreSQL Checkpointer | امتداد مسار الـ RFQ |

> الفارق الجوهري: الـ minimal كان **متزامناً وخطياً**. الطبقة 3 تُدخِل **الانتظار غير المتزامن** (إرسال RFQ ← وقفة أياماً ← رد المورد) — وهي أصعب جزء معماري في M2 كله.

---

## البنية المعمارية الكاملة (Full Architecture)

نفس طبقات الـ minimal، مع تفريع في الـ Agent ومسار async للمورد:

```
Triggers: [Scheduler/cron]  +  [Dashboard "افحص الآن"]
              │
              ▼
InventoryCheckNode   (SQL + Intelligence — لا LLM)
   ├─ low_stock / predicted_shortage ──────────►  مسار الشراء (Procurement)
   └─ slow_moving / near_expiry ───────────────►  مسار التسعير (Pricing)

── مسار الشراء (Procurement) ─────────────────────────────────
   AlertGenerator (LLM) → RFQBuilder (LLM) → HumanApproval (interrupt)
        │  عند الاعتماد
        ▼
   Send to Supplier  ──►  [CHECKPOINT — الـ graph يقف، thread_id محفوظ]
        ⋮   (انتظار ساعات/أيام — AsyncPostgresSaver يحفظ الحالة في DB)
        ▼   (رد المورد عبر POST /offers → استئناف نفس thread_id)
   OfferAnalysis (LLM) → يوصّي بالأفضل + مبرر → HumanApproval (نهائي)

── مسار التسعير (Pricing) ─────────────────────────────────────
   PricingAdvisor (LLM) → توصية خفض سعر → مراجعة المدير
```

---

## الطبقة 1 — Inventory Intelligence Layer

توسّع `InventoryCheckNode` من مجرد `stock < reorder` إلى كشف ذكي:

- **Slow-moving:** حساب معدل الدوران `turnover = المبيعات ÷ متوسط المخزون` (من `transactions`/`invoices`) → فلاج البطيء.
- **Near-expiry:** فحص `expiry_date` ضمن نافذة N يوم → تحذير مبكر.
- **Shortage prediction:** بدل انتظار الوصول لـ reorder، يحسب `days_until_stockout = stock_level ÷ avg_daily_sales` ويفلاج **قبل** النقص الفعلي → نظام proactive حقيقي.

**النتيجة:** توسعة `alert_type` enum إلى:
`low_stock | predicted_shortage | slow_moving | near_expiry`
والـ node يتفرّع حسب النوع (شراء أم تسعير).

---

## الطبقة 2 — Pricing Advisor

فرع موازٍ لمسار الشراء — للأصناف البطيئة/قريبة الانتهاء:

- **`PricingAdvisorNode`** (GPT-4o): يقترح خفض سعر مدروس **للمدير فقط** (ليس dynamic pricing تلقائياً).
- **Input:** `product_id, days_in_stock, expiry_date, avg_daily_sales`
- **Output:** مثال — "يُوصى بخفض السعر 15% لتصريف المخزون قبل انتهاء الصلاحية خلال 30 يوماً"
- يُخزَّن كتوصية (في `inventory_alerts` أو جدول `pricing_recommendations`) ويظهر في لوحة منفصلة بالـ Dashboard.

> منطق التفريع في `InventoryCheckNode`: نقص/توقّع نقص ← مسار الشراء (RFQ)، بطيء/قريب انتهاء ← مسار التسعير.

---

## الطبقة 3 — Procurement Async Loop (الجزء الصعب)

بعد إنشاء المسودة: `Human approval` ← إرسال للمورد ← **وقفة** ← عند وصول العروض ← `Offer analysis`.

### لماذا الـ Checkpointer؟
لما الـ RFQ يُرسَل، الـ graph يصل لنقطة `interrupt` ويقف — والوقفة قد تطول أياماً. **`AsyncPostgresSaver`** (الـ LangGraph PostgreSQL Checkpointer) يحفظ حالة الـ graph في الـ DB تحت `thread_id` مربوط بالـ RFQ. بدونه، تضيع الحالة بين الإرسال والرد (خاصة لو الـ server أُعيد تشغيله). معه، يمكن استئناف الـ graph من حيث وقف بعد يومين بشكل طبيعي.

### استدعاءان منفصلان مربوطان بـ `thread_id`:
1. **الأول:** check → alert → RFQ → approval → send → (وقفة، checkpoint محفوظ، RFQ status = `sent`).
2. **الثاني:** عند رد المورد، `POST /api/v1/m2/offers` يستقبل العرض → يخزّنه في `supplier_offers` → يستأنف الـ graph على نفس `thread_id` → `OfferAnalysisNode` يقارن العروض ويوصّي.

### `HumanApprovalNode`
يُعاد استخدام **نفس pattern الـ HumanReviewGate من M3** (interrupt + مراجعة الموظف) — جزء مبنيّ مسبقاً، مخاطرته قليلة. يظهر مرتين: قبل الإرسال (اعتماد الـ RFQ)، وبعد التحليل (اعتماد العرض المختار).

### `OfferAnalysisNode` (GPT-4o)
يستقبل كل عروض الـ RFQ، يقارنها (السعر + مدة التوريد + الشروط)، ويوصّي بالأفضل مع مبرر لغوي.

> **افتراض الـ Demo (راجعه):** بما أنك لن تنتظر مورداً حقيقياً، الافتراض المبدئي هو **form + mock هجين** — endpoint بسيط تُدخِل فيه 2–3 عروض (أو عروض mock جاهزة يطلقها زر)، ثم يُشغَّل التحليل. قابل للتبديل لـ parsing إيميل حقيقي لاحقاً.

---

## نموذج البيانات (Full Build Additions)

### توسعة `inventory_alerts`
- `alert_type` enum → `low_stock | predicted_shortage | slow_moving | near_expiry`

### إضافات `products`
| الحقل | النوع | الوصف |
|------|------|-------|
| `lead_time_days` | int | مدة التوريد المتوقعة (لـ shortage prediction) |
| `turnover_rate` | float | معدل الدوران (محسوب/مُخزَّن، لـ slow-moving) |

### جدول جديد `rfqs`
| الحقل | النوع | الوصف |
|------|------|-------|
| `rfq_id` | PK | معرّف الطلب |
| `product_id` | FK → `products` | الصنف |
| `vendor_ids` | array | الموردون المُرسَل إليهم |
| `quantity` | int | الكمية المطلوبة |
| `status` | enum | `draft / approved / sent / analyzing / closed` |
| `thread_id` | str | مفتاح الـ checkpointer (لاستئناف الـ graph) |
| `created_at` | timestamp | — |

### جدول جديد `supplier_offers`
| الحقل | النوع | الوصف |
|------|------|-------|
| `offer_id` | PK | معرّف العرض |
| `rfq_id` | FK → `rfqs` | الطلب المرتبط |
| `vendor_id` | FK → `vendors` | المورد |
| `price` | decimal | السعر المعروض |
| `lead_time_days` | int | مدة التوريد المعروضة |
| `terms` | text | الشروط |
| `received_at` | timestamp | وقت الاستلام |
| `raw_message` | text | نص العرض الأصلي |

---

## LangGraph State Schema (Full)

```python
{
  trigger_source:        "cron" | "manual",
  flagged_products:      list,
  current_product:       dict,
  detection_type:        "low_stock" | "predicted_shortage" | "slow_moving" | "near_expiry",
  consumption_rate:      float,   # avg_daily_sales
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
  user_context:          dict
}
```

### الـ Nodes الجديدة/المُوسَّعة
- **`InventoryCheckNode`** (مُوسَّع، لا LLM): يضيف turnover + near-expiry + shortage prediction، ويتفرّع حسب `detection_type`.
- **`PricingAdvisorNode`** (GPT-4o): توصية خفض السعر للبطيء/قريب الانتهاء.
- **`HumanApprovalNode`** (interrupt): نفس pattern M3؛ قبل الإرسال وبعد التحليل.
- **`OfferAnalysisNode`** (GPT-4o): مقارنة العروض والتوصية بالأفضل.

---

## خطة الـ Sprints (Full Build — تكمل من Sprint 4 في الـ minimal)

### Sprint 5 — Inventory Intelligence Layer — 4 أيام
- حساب turnover من `transactions`/`invoices`
- Slow-moving + Near-expiry detection (فحص `expiry_date`)
- Shortage prediction (`days_until_stockout`)
- توسعة `alert_type` enum + تفريع `InventoryCheckNode`
- Seed بيانات mock لكل سيناريو كشف

**المخرج:** كشف ذكي proactive بأربعة أنواع تنبيه

### Sprint 6 — Pricing Advisor — 3 أيام
- `PricingAdvisorNode` (LLM): توصية خفض السعر
- منطق التفريع: شراء (نقص) مقابل تسعير (بطيء/منتهي)
- تخزين التوصيات + لوحة تسعير في الـ Dashboard

**المخرج:** مسار التسعير يعمل بالتوازي مع الشراء

### Sprint 7 — Human Approval + Send + Checkpointer — 4 أيام
- `HumanApprovalNode` (interrupt) — إعادة استخدام HumanReviewGate من M3
- إعداد `AsyncPostgresSaver` على PostgreSQL
- جدول `rfqs` (مع `thread_id, status`)
- آلية الإرسال للمورد (mock/email) عند الاعتماد → `status=sent` + checkpoint
- التأكد من أن الـ graph يقف ويُستأنف بعد restart

**المخرج:** اعتماد بشري + إرسال + حالة محفوظة تدوم

### Sprint 8 — Offer Intake + Offer Analysis — 4 أيام
- جدول `supplier_offers`
- endpoint `POST /api/v1/m2/offers` (استقبال — form/mock للـ demo)
- استئناف الـ graph على `thread_id` عند وصول العروض
- `OfferAnalysisNode` (GPT-4o): مقارنة + توصية بمبرر
- العودة للاعتماد البشري النهائي

**المخرج:** الـ async loop مكتمل + تحليل عروض يعمل

### Sprint 9 — Integration + Full Demo — 3 أيام
- End-to-end كامل: كشف ← تنبيه ← RFQ ← اعتماد ← إرسال ← [وقفة] ← عروض ← تحليل ← توصية
- اختبار ثبات الـ checkpointer (استئناف بعد تأخير/restart)
- كل السيناريوهات: نقص، توقّع نقص، تسعير بطيء، قرب انتهاء، مقارنة عروض

**المخرج:** M2 Full Build يعمل end-to-end، جاهز للعرض

---

## سيناريوهات العرض (Full Build Demo)

| # | السيناريو | المتوقع |
|---|-----------|---------|
| 1 | Shortage prediction | صنف لسه فوق reorder لكن `days_until_stockout` صغير ← تنبيه استباقي |
| 2 | Slow-moving → Pricing | صنف بطيء الدوران ← توصية خفض سعر للمدير |
| 3 | Near-expiry → Pricing | صنف قرب انتهاؤه ← توصية تصريف |
| 4 | Async procurement | RFQ يُعتمد ويُرسَل ← الـ graph يقف ← إدخال عروض ← استئناف ← تحليل |
| 5 | Offer Analysis | 3 عروض موردين ← توصية بالأفضل مع مبرر |
| 6 | Checkpointer | استئناف نفس الـ RFQ بعد تأخير/restart بدون فقد حالة |

---

## Assumptions & Open Decisions (راجعها)

1. **أسلوب البناء:** يفترض هذا الملف بناءً **incremental** (minimal أولاً ثم هذه الطبقات). لو الوقت بقى +3 أسابيع وتريد الـ full من البداية، الترتيب نفسه لكن بلا "وقفة shippable" بعد الـ minimal.
2. **استقبال العروض في الـ demo:** الافتراض الحالي **form + mock هجين**. البدائل: عروض mock جاهزة فقط (أسهل)، أو parsing إيميل حقيقي (الأصعب، غير ضروري للعرض).

## Limitations (تُفصح في العرض)
- الـ async loop يعتمد على إدخال عروض يدوي/mock — لا تكامل بريد فعلي في الـ MVP
- توصيات التسعير استرشادية للمدير، ليست dynamic pricing
- shortage prediction خطي بسيط (`stock ÷ avg_daily_sales`)، ليس نموذج ML
- turnover محسوب من بيانات mock تاريخية

---

## ملخص الجدول الزمني (Full Build Extension)

| Sprint | المحتوى | المدة |
|--------|---------|-------|
| 5 | Inventory Intelligence Layer | 4 أيام |
| 6 | Pricing Advisor | 3 أيام |
| 7 | Human Approval + Send + Checkpointer | 4 أيام |
| 8 | Offer Intake + Offer Analysis | 4 أيام |
| 9 | Integration + Full Demo | 3 أيام |
| **المجموع (الإضافة)** | | **≈ 18 يوم** |
| **+ الـ minimal (12 يوم)** | | **≈ 30 يوم إجمالي** |

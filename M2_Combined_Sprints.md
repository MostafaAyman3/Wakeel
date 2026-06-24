# M2 — الخطة الشاملة لتنفيذ الوكيل الذكي (Purchasing & Inventory Agent)

> **ملاحظة هامة:** هذا الملف يمثل دمجاً كاملاً لمرحلتي تنفيذ موديول M2.
> - **المرحلة الأولى (الحد الأدنى - Minimal Build):** مسار خطي ومتزامن لبناء نسخة قابلة للإطلاق (Shippable) سريعاً.
> - **المرحلة الثانية (البناء الكامل - Full Build):** طبقات ذكاء متقدمة ومسارات غير متزامنة (Async Loop) تُضاف فوق المرحلة الأولى إذا توفر وقت إضافي (+3 أسابيع).

---

## 1. البنية المعمارية الشاملة (Full Architecture)

يتم بناء النظام على طبقتين، الأساس والامتداد:

```text
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
   Send to Supplier  ──►  [CHECKPOINT — الـ graph يقف، thread_id محفوظ]  <-- (إضافة المرحلة 2)
        ⋮   (انتظار ساعات/أيام — AsyncPostgresSaver يحفظ الحالة في DB)
        ▼   (رد المورد عبر POST /offers → استئناف نفس thread_id)
   OfferAnalysis (LLM) → يوصّي بالأفضل + مبرر → HumanApproval (نهائي)  <-- (إضافة المرحلة 2)

── مسار التسعير (Pricing) ── (إضافة المرحلة 2) ────────────────
   PricingAdvisor (LLM) → توصية خفض سعر → مراجعة المدير
```

---

## 2. نموذج البيانات الموسع (Extended Data Model)

بالإضافة إلى الجداول الأساسية، يتطلب البناء الكامل التوسعات التالية:

### توسعة `inventory_alerts`
- `alert_type` enum → `low_stock | predicted_shortage | slow_moving | near_expiry`

### إضافات جدول `products`
- `lead_time_days` (int): مدة التوريد المتوقعة (لـ shortage prediction)
- `turnover_rate` (float): معدل الدوران (محسوب/مُخزَّن، لـ slow-moving)

### جدول جديد `rfqs`
| الحقل | النوع | الوصف |
|------|------|-------|
| `rfq_id` | PK | معرّف الطلب |
| `product_id` | FK → `products` | الصنف |
| `vendor_ids` | array | الموردون المُرسَل إليهم |
| `quantity` | int | الكمية المطلوبة |
| `status` | enum | `draft / approved / sent / analyzing / closed` |
| `thread_id` | str | مفتاح الـ checkpointer (لاستئناف الـ graph) |

### جدول جديد `supplier_offers`
| الحقل | النوع | الوصف |
|------|------|-------|
| `offer_id` | PK | معرّف العرض |
| `rfq_id` | FK → `rfqs` | الطلب المرتبط |
| `vendor_id` | FK → `vendors` | المورد |
| `price` | decimal | السعر المعروض |
| `lead_time_days` | int | مدة التوريد المعروضة |
| `terms` | text | الشروط |

---

## 3. حالة الوكيل الذكي (LangGraph State Schema)

الـ Schema الكاملة التي تغطي المرحلتين:

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
  # مسار التسعير (المرحلة 2)
  pricing_recommendation: str,
  # تحليل العروض (المرحلة 2)
  supplier_offers:       list,
  recommended_offer:     dict,
  approval_status:       str,
  user_context:          dict
}
```

---

## 4. خطة التنفيذ الكاملة للـ Sprints (المرحلة الأولى + الثانية)

تم دمج مراحل التنفيذ بحيث تبدأ بالأساس القابل للتشغيل ثم تمتد إلى التعقيدات الإضافية المتتابعة.

### المرحلة الأولى: الحد الأدنى القابل للتشغيل (Minimal Build) - ≈ 25 يوماً

| Sprint | المهام والمخرجات | المسؤول | المدة |
|--------|----------------|---------|-------|
| **Sprint 0** | **Architecture & Planning:** تصميم بنية M2 بناءً على البلوبرنت، حالة الوكيل، ودمج n8n. | Architect | 3 أيام |
| **Sprint 1** | **Backend & Inventory Check:** برمجة `inventory_tools.py` للاتصال بـ Database وفحص (Reorder Point)، وبرمجة `inventory_check_node.py` ومسار `GET /inventory`. | Dev A | 4 أيام |
| **Sprint 2** | **LLM Nodes (Alerts & RFQs):** تحليل النواقص، هندسة Prompts لصياغة مسودة طلب الشراء، وربط الـ Nodes في `m2_graph.py`، وإنشاء مسار التشغيل. | Dev B | 5 أيام |
| **Sprint 3** | **Frontend Dashboard:** تصميم `InventoryTable.tsx` (Dev A) وعرض التنبيهات ومسودات الشراء `RFQDraftView.tsx` (Dev B) وربطها بالـ API. | Dev A&B | 5 أيام |
| **Sprint 4** | **Speech-to-Speech Integration:** دمج خدمة STT والـ TTS لتوفير تفاعل صوتي في واجهة `VoiceAssistantPanel.tsx`. | Dev A | 4 أيام |
| **Sprint 5** | **n8n Automation & Webhooks:** مسارات الجدولة اليومية (Cron) للفحص، والـ Webhook لإرسال طلبات الشراء أوتوماتيكياً عبر الـ Email. | Dev B | 4 أيام |

---

### المرحلة الثانية: طبقات البناء الكامل (Full Build Extensions) - ≈ 18 يوماً

*(تُنفذ بعد اكتمال المرحلة الأولى مباشرة إذا توفر الوقت)*

| Sprint | المهام والمخرجات | المدة |
|--------|----------------|-------|
| **Sprint 6** | **Inventory Intelligence Layer:** توسعة كشف المخزون ليشمل (Slow-moving, Near-expiry, Shortage prediction). تفريع الـ `InventoryCheckNode` حسب نوع التنبيه. | 4 أيام |
| **Sprint 7** | **Pricing Advisor:** إضافة `PricingAdvisorNode` لتقديم توصيات بخفض أسعار الأصناف بطيئة الحركة أو قريبة الانتهاء وعرضها في لوحة التحكم. | 3 أيام |
| **Sprint 8** | **Human Approval + Checkpointer:** إعداد `AsyncPostgresSaver` لحفظ حالة الـ Graph، استخدام `HumanApprovalNode`، بناء جدول `rfqs` وآلية توقف واستئناف الـ Agent للرد. | 4 أيام |
| **Sprint 9** | **Offer Intake & Analysis:** جدول `supplier_offers`، استقبال عروض الموردين عبر API، وبرمجة `OfferAnalysisNode` للمقارنة والتوصية بالأفضل. | 4 أيام |
| **Sprint 10** | **Integration & Full Demo:** ربط المسار بالكامل (كشف ← تنبيه ← اعتماد ← إرسال ← توقف ← استلام عروض ← استئناف ← تحليل)، وتجربة كافة السيناريوهات. | 3 أيام |

---

## 5. سيناريوهات العرض الشاملة (Full Demo Scenarios)

1. **Shortage prediction:** صنف استهلاكه سريع ← تنبيه استباقي باحتمالية نقصه قبل الوصول للحد الأدنى.
2. **Slow-moving → Pricing:** صنف بطيء الدوران ← توصية للمدير بخفض سعره لتصريفه.
3. **Near-expiry → Pricing:** صنف قرب موعد انتهاء صلاحيته ← توصية تسعير للبيع السريع لتجنب الهالك.
4. **Async procurement:** اعتماد طلب شراء ← يُرسَل للمورد ← يتوقف الوكيل ← يتم إدخال عروض وهمية للمحاكاة ← يستأنف الوكيل عمله تلقائياً.
5. **Offer Analysis:** الوكيل يحلل 3 عروض من موردين مختلفين ويوصي بالأفضل مع مبرر لغوي واضح.
6. **Checkpointer Resiliency:** إيقاف السيرفر وإعادة تشغيله في فترة انتظار الرد، للتأكيد على أن حالة طلب الشراء محفوظة بشكل آمن في قاعدة البيانات.

---

> **الخلاصة الزمنية:** مجموع الأيام الكلي للموديول (المرحلتين معاً): **≈ 43 يوماً عمل**. 
> *(ملاحظة: يمكن تقليل المدة الفعلية بنسبة تصل إلى 40% من خلال العمل المتوازي بين مطورين اثنين في مهام محددة).*

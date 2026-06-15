# M3 — Sprint Plan: Customer Support / Issue Resolution Agent

> **مرجع:** `ERP_Agentic_AI_Blueprint.md` — سطر 333 إلى 513
> **تنبيه:** Sprint 0 يفترض أن DB الأساسية وShared Services جاهزة من M1. M3 يضيف فوقها.

---

## Sprint 0 — Mock Data Setup
**المدة:** 3 أيام

**الجداول المطلوبة (mock — تُبنى مرة واحدة بشكل منظّم):**

```
order_status:     (order_id, customer_id, status, created_at, estimated_delivery, items)
shipping:         (tracking_id, order_id, status, carrier, location, last_update)
customer_history: (customer_id, interaction_type, issue_type, resolution, date)
```

**البيانات الحقيقية (موجودة من M1 DB):**
- جدول `invoices` + جدول `clients` (customer profiles المرتبطة بالفواتير)

**شروط الاتساق الداخلي (إلزامية):**
- `customer_id` في `order_status` و`customer_history` يُطابق `customer_id` في `invoices` و`clients`
- كل `order_id` في `shipping` له سجل في `order_status`
- `customer_history` يحتوي على عميل واحد على الأقل بمشكلة متكررة (لـ Scenario 4)
- عميل واحد على الأقل بـ order_id غير موجود (لـ Scenario 3 — Graceful Degradation)

**المخرج:** 3 جداول mock جاهزة، متسقة، قابلة للاستعلام

---

## Sprint 1 — LangGraph Skeleton + Input Parser + Data Fetcher
**المدة:** 5 أيام

**LangGraph State Schema (كامل):**
```
customer_identifier: dict   # { type: order_id|invoice_id|customer_id, value: str }
issue_description: str
language: str               # "ar" | "en" — auto-detect من InputParserNode، الرد يتطابق معها
issue_type: IssueType
fetched_data: dict          # { invoice, order, shipping, history }
data_completeness: float    # 0.0 → 1.0
confidence_score: float
draft_response: str
review_required: bool
escalation_needed: bool
final_response: str
```

**الـ Nodes:**

- `InputParserNode` (GPT-4o-mini): يستخرج `identifier_type` + `identifier_value` + `issue_description` من نص العميل الحر
- `DataFetcherNode`: يجلب من 4 مصادر بالتوازي:
  - `invoice_data` → **REAL** من DB الفعلية
  - `order_status` → **MOCK**
  - `shipping_status` → **MOCK**
  - `customer_history` → **MOCK**
- `DataCompletenessCheckNode`:
  - كل البيانات موجودة → `data_completeness = 1.0` → كمّل
  - بيانات جزئية → `data_completeness = 0.5` → flagging للـ missing fields
  - لا بيانات → `escalation_needed = true` → توجيه فوري للـ Escalation

- endpoint `/support` يستقبل `{ query, identifier }` ويرجع JSON بالـ schema التالي:

```json
{
  "draft_response":    "string",
  "confidence_score":  "float (0.0 → 1.0)",
  "confidence_label":  "High | Medium | Low",
  "review_required":   "boolean",
  "escalation_needed": "boolean",
  "issue_type":        "status_inquiry | billing_dispute | shipping_issue | refund_request | general_complaint",
  "transparency_data": {
    "invoice":  "object | null",
    "order":    "object | null",
    "shipping": "object | null",
    "history":  "array  | null"
  },
  "missing_fields":    "array of strings | []"
}
```

**ملاحظة:** `transparency_data` و`confidence_label` مخصصان لـ Human Review Interface فقط — لا يُعرضان للعميل مباشرة.

**المخرج:** agent يُحلّل الإدخال، يجلب البيانات، ويعرف اكتمالها

---

## Sprint 2 — Issue Classifier + Context Builder
**المدة:** 4 أيام

- `IssueClassifierNode` (GPT-4o-mini): يصنّف إلى:
  `status_inquiry / billing_dispute / shipping_issue / refund_request / general_complaint`
  — يحدد نوع المشكلة **والأولوية** (High/Medium/Low)

- `ContextBuilderNode`: يدمج كل `fetched_data` في context مُهيكَل يُغذي الـ LLM:
```
{
  customer_name, identifier_used,
  invoice: { number, date, amount, status },
  order:   { id, status, items, estimated_delivery },
  shipping:{ carrier, tracking, location },
  history: [ { date, issue_type, resolution } ]
}
```
- لو `data_completeness < 1.0`: يُضيف `missing_fields` للـ context عشان الـ LLM يُعالجها في الرد

**المخرج:** issue مصنّف + context كامل ومنظّم جاهز للـ Response Generator

---

## Sprint 3 — Response Generator + Graceful Degradation
**المدة:** 5 أيام

- `ResponseGeneratorNode` (GPT-4o): يولّد مسودة رد بناءً على `issue_type` + `context`
  - لغة الرد تتطابق تلقائياً مع `language` في الـ state (عربي إذا العميل كتب عربي، إنجليزي إذا إنجليزي)
  - يكتب بلغة واضحة مناسبة للعميل غير التقني
  - يحسب `confidence_score` (0.0 → 1.0) بناءً على اكتمال البيانات

**Graceful Degradation — 3 حالات إلزامية:**

| الحالة | الرد |
|--------|------|
| بيانات كاملة | رد كامل بكل التفاصيل |
| بيانات جزئية | يُقدّم ما هو متاح + "سيتواصل معك فريق الدعم خلال 24 ساعة لـ [المعلومة الناقصة]" |
| لا بيانات | "لم نعثر على [identifier]. يُرجى التأكد من الرقم أو التواصل على [قناة الدعم]" |

**نص الـ partial data template (من البلوبرنت مباشرة — يُستخدم في الـ prompt):**
> "وجدنا فاتورتك رقم INV-890 بتاريخ 15 يناير بإجمالي 3,200 جنيه. بيانات الشحن المرتبطة غير متاحة حالياً في النظام — سيتواصل معك فريق الدعم خلال 24 ساعة لتأكيد حالة التوصيل."

**Repeat Issue Detection:**
- لو `customer_history` يحتوي نفس `issue_type` أكثر من مرتين خلال آخر 180 يوم (Time Window لتفادي الـ false positives) ← `escalation_needed = true` + يُولّد ملخص للحالات السابقة

**Data Confidence Indicator:** يُحسب ويُخزَّن في الـ state:
- `confidence >= 0.8` → 🟢 High
- `0.5 ≤ confidence < 0.8` → 🟡 Medium
- `confidence < 0.5` → 🔴 Low

**قاعدة العرض:** يظهر للموظف في واجهة المراجعة فقط — **لا يظهر للعميل مباشرة**

**المخرج:** مسودة رد جاهزة + confidence score + escalation flag

---

## Sprint 4 — Human Review Gate + Escalation Logic
**المدة:** 4 أيام

**`HumanReviewGateNode` — قواعد التوجيه:**

| الحالة | القرار |
|--------|--------|
| `issue_type == billing_dispute` | `review_required = true` (إلزامي) |
| `issue_type == refund_request` | `review_required = true` (إلزامي) |
| الرد يتضمن التزاماً مالياً أو وعداً بموعد | `review_required = true` (إلزامي) |
| `confidence_score < 0.70` | `review_required = true` (إلزامي) |
| `escalation_needed == true` | تجاوز Review → إحالة مباشرة للمشرف |
| `issue_type == status_inquiry` | `review_required = false` (اختياري، قابل للتشغيل/الإيقاف) |
| أسئلة المعلومات العامة عن المنتج | `review_required = false` (اختياري، قابل للتشغيل/الإيقاف) |

**Auto-send:** لا يحدث تلقائياً — يشترط موافقة صريحة من الموظف حتى لو `review_required = false`

**Reject & Regenerate Loop:**
- تتم عملية الـ Reject & Regenerate بإعادة استدعاء نفس الـ endpoint (`/support`) بدلاً من إنشاء endpoint جديد، مع تمرير سياق الرفض والملاحظات (`rejection_context`) وإضافته إلى الـ graph state لتوجيه عملية التوليد الجديدة وتحسين الرد.

**`EscalationNode`:**
- يُولّد ملخص الحالة: identifier + issue_type + fetched_data + سبب الإحالة
- يُسجّل في Audit Trail

**Audit Trail:**
- كل قرار يُسجَّل: `{ timestamp, issue_type, confidence, review_required, action_taken, agent_id }`

**المخرج:** routing صح لكل حالة + escalation يعمل + audit log كامل

---

## Sprint 5 — Frontend: Customer Input + Human Review Interface
**المدة:** 5 أيام

**Customer Input Interface:**
- حقل identifier (order_id / invoice_id / customer_id) + نوع الـ identifier
- حقل وصف المشكلة (نص حر، عربي/إنجليزي)
- زر إرسال → يستدعي `/support`

**Human Review Interface (للموظف):**
- **Response Preview:** عرض المسودة كاملة قبل الإرسال
- **Transparency Panel:** البيانات التي اعتمد عليها الـ agent (invoice details / order / shipping / history)
- **Confidence Indicator:** 🟢/🟡/🔴 + نسبة مئوية — **يظهر للموظف فقط، لا للعميل**
- **Edit Field:** تعديل نصي مباشر على المسودة
- **3 أزرار الإجراء:**
  - ✅ موافق وإرسال
  - 🔄 رفض وإعادة توليد
  - ⬆️ إحالة لمشرف
- **Escalation View:** عرض ملخص الحالة المُحالة مع سجل التاريخ

**المخرج:** واجهتان كاملتان: إدخال العميل + مراجعة الموظف

---

## Sprint 6 — Integration + Demo Scenarios
**المدة:** 4 أيام

**اختبار الـ 4 Demo Scenarios كاملة:**

| Scenario | الإدخال | المتوقع |
|----------|---------|---------|
| 1 — Order Status | ORD-2024-1567 | Confidence High → auto-send available، رد بتفاصيل الشحن |
| 2 — Invoice Dispute | INV-890 + "أنا ما طلبتش المنتج ده" | `billing_dispute` → Human Review إلزامي |
| 3 — Missing Data | DEL-999 | لا بيانات → Graceful Degradation + Escalation |
| 4 — Repeat Issue | customer قديم + مشكلة توصيل | `customer_history` يكشف 3 تكرارات → auto-escalate للمشرف |

- ربط Frontend بـ `/support` endpoint كامل
- اختبار الـ Audit Trail: كل سيناريو يُسجَّل صح
- اختبار حالة الـ `review_required = false` (auto-send) مقابل `review_required = true`

**المخرج:** M3 شغال end-to-end، الـ 4 scenarios تعمل، جاهز للعرض

---

## ما هو مؤجل (لا يُنفَّذ في MVP)

من البلوبرنت section 3.3 — للرجوع إليها عند التخطيط للمراحل التالية:
- Real-time shipping API (مع شركات شحن فعلية)
- Email / WhatsApp channel integration
- Sentiment analysis للعميل
- Automated resolution بدون مراجعة بشرية
- CRM integration كاملة
- Customer satisfaction rating بعد الحل
- Chat history persistence بين الجلسات

## Limitations يجب الإفصاح عنها في العرض

- الردود تعتمد مباشرة على اكتمال البيانات — بيانات ناقصة = رد جزئي
- لا channel integration في MVP — الواجهة داخل المنصة فقط
- بيانات الشحن static في mock — لا real-time tracking

---

## ملخص الجدول الزمني

| Sprint | المحتوى | المدة |
|--------|---------|-------|
| 0 | Mock Data (order / shipping / history) | 3 أيام |
| 1 | LangGraph + Input Parser + Data Fetcher | 5 أيام |
| 2 | Issue Classifier + Context Builder | 4 أيام |
| 3 | Response Generator + Graceful Degradation | 5 أيام |
| 4 | Human Review Gate + Escalation + Audit Trail | 4 أيام |
| 5 | Frontend: Customer Input + Review Interface | 5 أيام |
| 6 | Integration + 4 Demo Scenarios | 4 أيام |
| **المجموع** | | **~30 يوم** |

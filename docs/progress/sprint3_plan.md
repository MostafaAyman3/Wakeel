```
# Sprint 3 Implementation Plan — Invoice Analysis Tool
## النسخة النهائية المعتمدة (بعد معالجة التعارضات والـ Partial Match)

> **التعديلات الهندسية النهائية:**
> 1. استبدال الـ 4 nodes المنفصلة في Graph بـ Node واحدة (`InvoiceAnalysisToolNode`) — الـ 4 steps تشتغل كـ sequential functions داخلها.
> 2. لا UI (Charts / Metric Cards) في Sprint 3 — المخرج raw_data + narrative فقط.
> 3. **توسيع الـ State الحالي:** لا يتم إضافة حقل جديد للـ `M1State`؛ حقل `extracted_params: dict` موجود بالفعل من Sprint 1، ويتم **توسيعه بنيته داخلياً** لتدعم الـ `invoice_analysis context`.
> 4. **ضبط حقول الثقة (Confidence):** فصل الـ `data_confidence` (التي تقيس جودة وتوافق البيانات بعد جلبها من الـ DB) عن الـ `extraction_confidence` (التي تقيس مدى ثقة استخراج المعاملات بواسطة الـ LLM وتعيش داخل الـ metrics).
> 5. **دعم الـ Partial Match للموردين:** تعديل منطق الـ SQL Lookup ليكون `%vendor_name%` لضمان البحث الجزئي الصحيح.
> 6. **موقع الـ Domain:** حقل الـ `domain` مكانه الصحيح هو **على المستوى الرئيسي (Root Level)** للـ `extracted_params` مباشرة.

---

## 1. Sprint Objectives

Sprint 3 يبني الـ `invoice_analysis_tool` كـ node مُدمج داخل M1 Agent، يُفعَّل تلقائياً لما الـ Router يكتشف `intent = invoice_analysis`. الهدف النهائي: الـ agent يستطيع يستعلم عن أي بيانات فواتير من الـ DB مباشرة ويطلع بـ pattern detection مالي حقيقي — لا OCR، لا PDF، كل حاجة من جداول الـ DB الموجودة.

ما المطلوب إنجازه في نهاية Sprint 3:
- "حللّي فواتير الموردين في الربع الأول"
- "مين أغلى 5 موردين خلال 2025؟"
- "الفاتورة INV-0045 فيها إيه؟"
- "فيه فواتير متأخرة السداد Reef؟"
- "المورد X رفع أسعاره ولا لأ؟"

---

## 2. Functional Requirements

### 2.1 Requirements إلزامية في MVP

**FR-01 — Intent & Parameter Extraction**
الـ node يستخرج من الـ query بالعربي أو الإنجليزي: نطاق زمني، vendor_id أو vendor_name، invoice_id، نوع التحليل (`single_invoice` / `batch_analysis`)، نوع الـ batch analysis (totals, top_vendors, overdue, trend, vendor_comparison, recurring, vat_summary).

**FR-02 — SQL Template Selection:** يختار الـ template الصح — لا يكتب SQL من الصفر.

**FR-03 — Safe DB Execution:** يتصل بـ `READONLY_DB_URL` فقط على جداول `invoices`, `invoice_items`, `vendors`.

**FR-04 — Pattern Detection:** تأخر سداد ممنهج، ارتفاع أسعار مورد، مصاريف متكررة غير معتادة، تركّز الإنفاق.

**FR-05 — Bilingual Output:** الـ narrative بنفس لغة الـ query.

**FR-06 — Integration:** الـ node يشتغل داخل الـ graph الحالي.

### 2.2 Requirements مؤجلة
- OCR أو معالجة PDF
- Real-time streaming
- Scheduled reports
- Charts / Metric Cards / Alert Cards UI ← **Sprint 5**

---

## 3. Architecture Changes

### 3.1 ما الذي يتغير في الـ Graph


```
قبل: Router → invoice_analysis_stub → ValidationEnrichmentNode → OutputFormatterNode
بعد: Router → InvoiceAnalysisToolNode → ValidationEnrichmentNode → OutputFormatterNode
```

**جوه InvoiceAnalysisToolNode (sequential functions):**

```
_extract_invoice_params()   ← GPT-4o-mini
↓
_build_invoice_query()      ← منطق بحت، لا LLM
↓
_execute_invoice_query()    ← DB Read-Only
↓
_analyze_invoice_data()     ← GPT-4o
```

### 3.2 مبدأ التكامل

`InvoiceAnalysisToolNode` هي class بـ `__call__` method — الـ 4 functions private methods جوها، مش nodes في الـ graph.

### 3.3 ملفات جديدة vs ملفات تُعدَّل

| الملف | الحالة | الإجراء |
|-------|--------|---------|
| `agents/m1/nodes/invoice_analysis_tool_node.py` | جديد | ينشأ ← **ملف Node الواحدة** |
| `agents/m1/tools/invoice_templates.py` | جديد | ينشأ |
| `agents/prompts/invoice_analysis.py` | جديد | ينشأ |
| `agents/m1/schemas/m1_state.py` | موجود | يُعدَّل (توسيع بنية الـ `extracted_params` الحالية داخلياً) |
| `agents/m1/graphs/m1_graph.py` | موجود | يُعدَّل (استبدال stub بـ node واحدة) |
| `agents/m1/nodes/stub_nodes.py` | موجود | يُعدَّل (حذف invoice_analysis_stub) |
| `scripts/test_sprint3.py` | جديد | ينشأ |

---

## 4. Node Design — InvoiceAnalysisToolNode

### 4.1 الهيكل العام

```python
class InvoiceAnalysisToolNode:
    """
    State outputs:
    - extracted_params: dict  ← توسيع الحقل الحالي (domain برة + الأنماط بالداخل)
    - raw_data: list          ← نتائج الـ DB (الحقل العام الموجود)
    - narrative: str          ← التحليل اللغوي (الحقل العام الموجود)
    No UI components — that's Sprint 5.
    """

    async def __call__(self, state: M1State) -> dict:
        invoice_params = await self._extract_invoice_params(
            state.query, state.language, state.extracted_params
        )

        # التحقق من ثقة الاستخراج اللغوي للمعاملات
        if invoice_params["metrics"]["extraction_confidence"] < 0.6:
            return {"intent": "clarification_needed", "extracted_params": invoice_params}

        sql, sql_params = self._build_invoice_query(invoice_params)
        invoice_params["intent_details"]["applied_template"] = sql_params["template_name"]
        invoice_params["metrics"]["requires_vendor_lookup"] = sql_params.get("vendor_lookup", False)

        raw_data, exec_error = await self._execute_invoice_query(sql, sql_params)

        # حساب ثقة البيانات المسترجعة بناءً على جودة التنفيذ والنتائج (calculated_after_query)
        data_confidence = 1.0 if (not exec_error and len(raw_data) > 0) else 0.0
        if len(raw_data) == 0:
            data_confidence = 0.5  # استرجاع ناجح لكن النتيجة فارغة (Graceful Empty)

        narrative, invoice_analysis = await self._analyze_invoice_data(
            raw_data, invoice_params, state.language
        )
        invoice_params["metrics"]["anomaly_detected"] = invoice_analysis["anomaly_detected"]

        return {
            "extracted_params": invoice_params,   
            "raw_data": raw_data,
            "narrative": narrative,
            "data_confidence": data_confidence,  # القيمة الفعلية لجودة جلب البيانات وعزلها عن الـ Extraction
        }

```
### 4.2 Function 1 — _extract_invoice_params()
**يستدعي:** GPT-4o-mini | **Output — شكل هيكل الـ extracted_params الموسّع:**
```python
{
    "domain": "invoice_analysis",   # ← على المستوى الرئيسي (Root) لسهولة الـ Routing
    "intent_details": {
        "analysis_type": "single_invoice" | "batch_analysis",
        "subtype": "totals"|"top_vendors"|"overdue"|"trend"|"vendor_comparison"|"recurring"|"vat_summary",
        "applied_template": None   
    },
    "filters": {
        "start_date": str | None,
        "end_date": str | None,
        "vendor_name": str | None,
        "vendor_id": uuid | None,
        "invoice_display_id": str | None,
        "limit": 10
    },
    "metrics": {
        "extraction_confidence": float,   # ثقة استخراج الـ parameters بواسطة الـ LLM
        "requires_vendor_lookup": False,
        "anomaly_detected": False   
    }
}

```
### 4.3 Function 2 — _build_invoice_query()
**لا LLM** — يقرأ من الـ intent_details والـ filters:
```python
if analysis_type == "single_invoice"  → "SINGLE_INVOICE_DETAIL"
elif subtype == "totals"              → "INVOICE_TOTALS_BY_DATE"
elif subtype == "vat_summary"         → "INVOICE_VAT_SUMMARY"
elif subtype == "top_vendors"         → "TOP_VENDORS_BY_COST"
elif subtype == "overdue"             → "OVERDUE_INVOICES"
elif subtype == "vendor_comparison"   → "VENDOR_COST_OVER_TIME"
elif subtype == "trend"               → "INVOICE_TREND_ANALYSIS"
elif subtype == "recurring"           → "RECURRING_EXPENSE_ANALYSIS"

```
**Vendor Name Partial Match Lookup:**
لو filters["vendor_name"] موجود والـ vendor_id مش موجود، يتم بناء الاستعلام الجزئي (Partial Match) كالتالي:
```python
# منطق الـ SQL المعتمد في الـ Template الداخلي للـ Lookup:
# WHERE LOWER(v.name) LIKE LOWER(:vendor_name)
# ويتم تمرير الـ parameter محاطاً بـ % لضمان الـ Partial Match الصحيح عبر SQLAlchemy:
sql_params["vendor_name"] = f"%{invoice_params['filters']['vendor_name']}%"
sql_params["vendor_lookup"] = True

```
### 4.4 Function 3 — _execute_invoice_query()
**Whitelist:** {'invoices', 'invoice_items', 'vendors'} | **LIMIT 500** | AST check (reuse من Sprint 2). لو فاضية → raw_data = [] + رسالة لغوية هادئة.
### 4.5 Function 4 — _analyze_invoice_data()
**يستدعي:** GPT-4o | **Two-Pass:**
 * **Pass 1 (Python):** إجمالي الإنفاق، نسبة التأخر، المورد الأعلى ونسبته، % التغيير بين الفترات.
 * **Pass 2 (LLM):** narrative بلغة الـ user + severity لكل pattern + recommendations.
## 5. State Model Updates
### لا حقول جديدة في الـ M1State
يتم الحفاظ على الحقل الموجود من Sprint 1 كما هو وتوسيع الـ Map الداخلي له:
```python
# agents/m1/schemas/m1_state.py
extracted_params: dict | None   # الحقل الأصلي - يتم توسيع محتواه الشجري فقط

```
### شكل extracted_params النهائي داخل الـ State
```python
state.extracted_params = {
    "domain": "invoice_analysis",   
    "intent_details": {
        "analysis_type": "batch_analysis",
        "subtype": "top_vendors",
        "applied_template": "TOP_VENDORS_BY_COST"
    },
    "filters": {
        "start_date": "2025-01-01",
        "end_date": "2025-03-31",
        "vendor_name": "Al-Rashid Supplies",
        "vendor_id": "uuid-1234-...",
        "invoice_display_id": None,
        "limit": 5
    },
    "metrics": {
        "extraction_confidence": 0.88,   # الـ Parameter/Extraction confidence معزولة هنا
        "requires_vendor_lookup": True,
        "anomaly_detected": True        # الكشف عن الأنماط لـ Sprint 5
    }
}

```
## 6. Intent Extraction Design
### 6.1 أمثلة للتحويل
 * "حللّي فواتير الموردين في الربع الأول من 2025" \rightarrow subtype: "totals" | start_date: "2025-01-01"
 * "مين أغلى 5 موردين خلال السنة اللي فاتت؟" \rightarrow subtype: "top_vendors" | limit: 5
 * "الفاتورة INV-0045 فيها إيه؟" \rightarrow analysis_type: "single_invoice" | invoice_display_id: "INV-0045"
## 7. SQL Template Strategy
| # | Template | الهدف | الجداول | الـ Params |
|---|---|---|---|---|
| 1 | SINGLE_INVOICE_DETAIL | فاتورة واحدة كاملة | invoices, invoice_items, vendors | invoice_display_id |
| 2 | INVOICE_TOTALS_BY_DATE | إجمالي فترة | invoices | start_date, end_date |
| 3 | INVOICE_VAT_SUMMARY | إجمالي VAT | invoices | start_date, end_date |
| 4 | TOP_VENDORS_BY_COST | أعلى N موردين | invoices, vendors | start_date, end_date, limit |
| 5 | OVERDUE_INVOICES | فواتير متأخرة | invoices, vendors | as_of_date, vendor_id? |
| 6 | VENDOR_COST_OVER_TIME | تطور تكلفة مورد | invoices, vendors | vendor_id, start_date, end_date |
| 7 | INVOICE_TREND_ANALYSIS | اتجاه الإنفاق شهرياً | invoices | start_date, end_date |
| 8 | RECURRING_EXPENSE_ANALYSIS | مبالغ متكررة | invoices, vendors | start_date, end_date, vendor_id? |
كل parameters عبر SQLAlchemy bindparam لمنع الـ Injection.
## 8. Database Access Rules
 * **Read-Only URL:** استخدام READONLY_DB_URL فقط.
 * **AST Validation:** العمليات المسموحة هي SELECT فقط (إعادة استخدام طبقة الحماية من Sprint 2).
 * **Whitelist الجداول:** الحصر على {'invoices', 'invoice_items', 'vendors'} فقط.
 * **الحد الأقصى:** تطبيق LIMIT 500.
## 9. Pattern Detection Logic
 * **Payment Delays:** نسبة Overdue > 30% \rightarrow medium | > 50% \rightarrow high
 * **Price Increase:** تغير متوسط سعر الفاتورة/الصنف > 10% \rightarrow medium | > 25% \rightarrow high
 * **Concentration Risk:** مورد واحد يستأثر بـ > 40% \rightarrow medium | > 60% \rightarrow high
## 10. File-by-File Implementation Plan
| # | الملف | الحالة | الأولوية | الإجراء المتبع |
|---|---|---|---|---|
| 1 | agents/m1/tools/invoice_templates.py | جديد | أولاً | كتابة الـ 8 قوالب مع الـ Partial Match للموردين |
| 2 | agents/prompts/invoice_analysis.py | جديد | ثانياً | صياغة الـ Prompts باللغتين العربية والإنجليزية |
| 3 | agents/m1/schemas/m1_state.py | موجود | ثالثاً | مراجعة عدم إضافة حقول والاكتفاء بتوثيق التوسع الداخلي |
| 4 | agents/m1/nodes/invoice_analysis_tool_node.py | جديد | رابعاً | بناء الـ Node والـ 4 دالات الداخلية المتتابعة وفصل الـ Confidence الحسابي |
| 5 | agents/m1/graphs/m1_graph.py | موجود | خامساً | ربط الـ Node الجديدة بالـ Graph وإلغاء الـ Stub |
| 6 | agents/m1/nodes/stub_nodes.py | موجود | سادساً | تنظيف وحذف الـ invoice_analysis_stub |
| 7 | scripts/test_sprint3.py | جديد | سابعاً | كتابة الـ 14 حالة اختبار لضمان الجودة والسلامة |
## 11. Acceptance Criteria
| # | Criterion | الملف المسؤول |
|---|---|---|
| AC-01 | الـ Graph يكتمل ويُبنى بدون Errors تضارب | m1_graph.py |
| AC-02 | بقاء الـ extracted_params كحقل منفرد مع هيكلة الـ Root domain بشكل سليم | invoice_analysis_tool_node.py |
| AC-03 | نجاح الـ 8 templates في العمل والبحث الجزئي عن الموردين بنجاح | invoice_templates.py |
| AC-04 | فصل قيم الـ data_confidence الحسابية عن الـ extraction_confidence بدقة | invoice_analysis_tool_node.py |
| AC-05 | نجاح الـ 14 حالة اختبار بدون أي Regression لـ Sprint 1 و 2 | test_sprint3.py / test_sprint1/2.py |
## 12. Checklist نهاية Sprint 3
```
□ invoice_templates.py — الـ 8 قوالب تدعم الـ LIKE الجزئي الممرر بـ %
□ M1State — الحقل لم يتغير ومحمي من التشتت والتعارض (No Regression)
□ invoice_analysis_tool_node.py — الـ 4 دالات تعمل تتابعياً:
□   ↳ _extract_invoice_params()  — الـ Domain على الـ Root والـ Extraction Confidence بداخل Metrics
□   ↳ _build_invoice_query()     — اختيار الـ Template الصح وضبط الـ SQL Params للبحث الجزئي
□   ↳ _execute_invoice_query()   — حماية كاملة، حساب الـ data_confidence بعد الاستعلام مباشرة
□   ↳ _analyze_invoice_data()    — تحليل ثنائي اللغة وتحديد الـ anomaly_detected بدقة
□ m1_graph.py — الـ compile ينجح بعد استبدال الـ Stub بالـ Node الكبرى
□ stub_nodes.py — invoice_analysis_stub محذوف
□ test_sprint3.py — الـ 14 حالة اختبار تنجح بالكامل (PASS)
□ لا كود واجهات (No UI Code) في هذا الـ Sprint نهائياً

```
## 13. Risks and Mitigations
| Risk | الخطر | التخفيف |
|---|---|---|
| R-01 State Conflict | fields جديدة تكسر الـ graph | total=False + graph.compile() فوراً |
| R-02 Vendor Name | اسم عربي والـ DB إنجليزي | ILIKE '%:vendor_name%' |
| R-03 Large Results | 300+ فاتورة | LIMIT 500 + pre-aggregation > 50 row |
| R-04 False Positives | mock data مش واقعية | thresholds كـ constants قابلة للتعديل |
| R-05 Graph Regression | تعديل m1_graph يكسر intents تانية | تشغيل sprint1/2 tests بعد كل تعديل |
| R-06 DB Timeout | templates على data كبيرة | indexed columns + timeout 30s |
## 14. Detailed Execution Order
**Pre-Sprint (يوم واحد):**
 * Task 0.1: تحقق من Mock Data (invoices بتواريخ/statuses متنوعة، 3+ vendors)
 * Task 0.2: تحقق من AST parser — لو مش importable → agents/shared/sql_validator.py
**اليوم 1:** invoice_templates.py + اختبار يدوي على Supabase
**اليوم 2:** invoice_analysis.py prompts + تعديل m1_state.py (حقل واحد) + تشغيل test_sprint1
**اليوم 3:** invoice_analysis_tool_node.py — functions 1+2 + اختبار مستقل
**اليوم 4:** invoice_analysis_tool_node.py — functions 3+4 + اختبار end-to-end
**اليوم 5:** تعديل m1_graph.py + stub_nodes.py + كتابة test_sprint3.py + تشغيل كل الـ tests + تحديث agent_execution_log.md Step 18
## 15. ما هو مؤجل
**Sprint 5:** Metric Card + Bar/Line Chart + Alert Card UI (الـ anomaly_detected جاهز جوه extracted_params["metrics"] — الـ UI بس مؤجلة)
**بعد MVP:** OCR، streaming، scheduled reports، NL2SQL

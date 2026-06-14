Sprint 3 Implementation Plan — Invoice Analysis Tool


1. Sprint Objectives

Sprint 3 يبني الـ invoice_analysis_tool كـ sub-pipeline مُدمج داخل M1 Agent، يُفعَّل تلقائياً لما الـ Router يكتشف intent = invoice_analysis. الهدف النهائي: الـ agent يستطيع يستعلم عن أي بيانات فواتير من الـ DB مباشرة ويطلع بـ pattern detection مالي حقيقي — لا OCR، لا PDF، كل حاجة من جداول الـ DB الموجودة.

ما المطلوب إنجازه في نهاية Sprint 3:

النظام يقدر يجاوب على أسئلة زي:


"حللّي فواتير الموردين في الربع الأول"
"مين أغلى 5 موردين خلال 2025؟"
"الفاتورة INV-0045 فيها إيه؟"
"فيه فواتير متأخرة السداد؟"
"المورد X رفع أسعاره ولا لأ؟"



2. Functional Requirements

2.1 Requirements إلزامية في MVP

FR-01 — Intent & Parameter Extraction
الـ node يستخرج من الـ query بالعربي أو الإنجليزي:


نطاق زمني (start_date, end_date)
vendor_id أو vendor_name (لو ذُكر)
invoice_id أو display_id (لو ذُكر فاتورة بعينها)
نوع التحليل: single_invoice أو batch_analysis
نوع الـ batch analysis: (totals, top_vendors, overdue, trend, vendor_comparison, recurring, vat_summary)


FR-02 — SQL Template Selection
بناءً على الـ params المستخرجة، يختار الـ template الصح — لا يكتب SQL من الصفر.

FR-03 — Safe DB Execution
يتصل بـ READONLY_DB_URL فقط، على جداول: invoices, invoice_items, vendors — وممنوع أي write operation.

FR-04 — Pattern Detection
الـ Analysis Node يكشف تلقائياً:


تأخر سداد ممنهج
ارتفاع أسعار مورد بعينه
مصاريف متكررة غير معتادة
تركّز الإنفاق (مورد واحد > X% من الإجمالي)


FR-05 — Bilingual Output
الـ narrative يُولَّد بنفس لغة الـ query (عربي/إنجليزي).

FR-06 — Integration مع الـ Graph الموجود
الـ sub-pipeline يشتغل داخل الـ graph الحالي — لا graph جديد، لا agent منفصل.

2.2 Requirements مؤجلة (خارج Sprint 3)


OCR أو معالجة PDF — غير موجودة في البيانات أصلاً
Real-time streaming للـ analysis
Scheduled invoice reports



3. Architecture Changes

3.1 ما الذي يتغير في الـ Graph الموجود

الـ Router Node في Sprint 1 يوجّه invoice_analysis لـ stub node اسمه invoice_analysis_stub. Sprint 3 يستبدل هذا الـ stub بـ sub-pipeline حقيقي من 4 nodes.

قبل Sprint 3 (الوضع الحالي):

Router → invoice_analysis_stub → ValidationEnrichmentNode → OutputFormatterNode

بعد Sprint 3:

Router → InvoiceIntentParamExtractorNode
              ↓
         InvoiceQueryBuilderNode
              ↓
         InvoiceDBExecutionNode
              ↓
         InvoiceAnalysisNode (LLM)
              ↓
         ValidationEnrichmentNode (موجود)
              ↓
         OutputSelectorNode (Sprint 5)

3.2 مبدأ التكامل

الـ sub-pipeline مش graph مستقل — هو سلسلة nodes تُضاف لـ m1_graph.py الموجود وتُربط بالـ conditional edges من الـ Router. الـ State يبقى نفسه M1State مع إضافات للـ invoice context.

3.3 ملفات جديدة vs ملفات تُعدَّل

الملفالحالةالإجراءagents/m1/nodes/invoice_intent_extractor_node.pyجديدينشأagents/m1/nodes/invoice_query_builder_node.pyجديدينشأagents/m1/nodes/invoice_db_execution_node.pyجديدينشأagents/m1/nodes/invoice_analysis_node.pyجديدينشأagents/m1/tools/invoice_templates.pyجديدينشأagents/prompts/invoice_analysis.pyجديدينشأagents/m1/schemas/m1_state.pyموجوديُعدَّل (إضافة invoice fields)agents/m1/graphs/m1_graph.pyموجوديُعدَّل (استبدال stub بـ 4 nodes)agents/m1/nodes/stub_nodes.pyموجوديُعدَّل (حذف invoice_analysis_stub)scripts/test_sprint3.pyجديدينشأ


4. LangGraph Node Design

4.1 Node 1 — InvoiceIntentParamExtractorNode

المسؤولية: استخراج كل الـ parameters اللازمة للاستعلام من الـ query الطبيعية.

Input: state.query, state.language, state.extracted_params (من Sprint 1)

يستدعي: GPT-4o-mini (سريع وكافي لـ extraction مش reasoning)

Output يُكتب في State:

invoice_context: {
  analysis_type: "single_invoice" | "batch_analysis",
  batch_subtype: "totals" | "top_vendors" | "overdue" | "trend" |
                 "vendor_comparison" | "recurring" | "vat_summary",
  start_date: date | null,
  end_date: date | null,
  vendor_id: uuid | null,
  vendor_name: str | null,
  invoice_display_id: str | null,
  limit: int (default: 10),
  extraction_confidence: float
}

منطق المعالجة:


لو Sprint 1 استخرج params مفيدة (date range مثلاً) → يأخذها ويُكمّل عليها، لا يبدأ من الصفر
لو ذُكر اسم مورد بالعربي → يُخزَّن كـ vendor_name للـ Query Builder يعمل lookup
لو الـ confidence < 0.6 → يُوجَّه لـ ClarificationNode الموجود


قرار تصميمي: هذا الـ node يستخدم structured output بنفس الطريقة اللي Sprint 1 استخدمها في IntentClassifierNode — function calling مع schema محددة — لأنها أثبتت نجاحها.


4.2 Node 2 — InvoiceQueryBuilderNode

المسؤولية: اختيار الـ SQL template المناسب وملء الـ parameters بشكل آمن.

Input: state.invoice_context

لا يستدعي LLM — قرار منطقي بحت بناءً على invoice_context.analysis_type و batch_subtype.

منطق الاختيار:

if analysis_type == "single_invoice":
    → template: SINGLE_INVOICE_DETAIL
    → params: {invoice_display_id}

elif analysis_type == "batch_analysis":
    match batch_subtype:
        "totals"            → INVOICE_TOTALS_BY_DATE
        "vat_summary"       → INVOICE_VAT_SUMMARY
        "top_vendors"       → TOP_VENDORS_BY_COST
        "overdue"           → OVERDUE_INVOICES
        "vendor_comparison" → VENDOR_COST_OVER_TIME
        "trend"             → INVOICE_TREND_ANALYSIS
        "recurring"         → RECURRING_EXPENSE_ANALYSIS

Output يُكتب في State:

invoice_query: {
    template_name: str,
    sql: str,
    params: dict,
    requires_vendor_lookup: bool
}

حالة خاصة — Vendor Name Lookup: لو invoice_context.vendor_name موجود وvendor_id مش موجود، الـ node يُضيف sub-query لجلب الـ vendor_id من جدول vendors بناءً على الاسم — WHERE LOWER(name) LIKE LOWER(:vendor_name) — ويُدمجها في الـ template.


4.3 Node 3 — InvoiceDBExecutionNode

المسؤولية: تنفيذ الـ SQL على الـ DB بـ Read-Only connection وإرجاع النتائج.

Input: state.invoice_query

يستخدم: READONLY_DB_URL — نفس الـ pattern اللي Sprint 2 استخدمه في db_query_tool

الجداول المسموح بها: invoices, invoice_items, vendors — فقط.

Validation قبل التنفيذ:


الـ SQL يبدأ بـ SELECT فقط (AST check بنفس طريقة Sprint 2)
أسماء الجداول في الـ query محصورة في القائمة المسموحة
لا DROP, DELETE, UPDATE, INSERT, CREATE


Output يُكتب في State:

raw_invoice_data: list[dict],
invoice_row_count: int,
invoice_execution_error: str | null

Error Handling:


لو query فشلت → invoice_execution_error يُكتب، الـ Analysis Node يتعامل معاه gracefully
لو النتيجة فاضية → raw_invoice_data = [] مع رسالة "لم يتم العثور على فواتير تطابق المعايير"



4.4 Node 4 — InvoiceAnalysisNode

المسؤولية: تحليل بيانات الفواتير المُسترجعة واكتشاف الـ patterns.

Input: state.raw_invoice_data, state.invoice_context, state.language

يستدعي: GPT-4o (مش mini — التحليل يحتاج reasoning حقيقي)

نوعا التحليل:

A — Single Invoice Analysis:


ملخص الفاتورة (المورد، التاريخ، الإجمالي، الضريبة، حالة الدفع)
تفاصيل كل line item
هل هي متأخرة السداد؟ بكم يوم؟
مقارنة بسيطة بمتوسط فواتير نفس المورد (لو متاحة في الـ data)


B — Batch Analysis:
يعمل pattern detection شامل على مجموعة الفواتير المُسترجعة:

Patternكيف يُكتشفتأخر سداد ممنهجpayment_status = 'Overdue' متكرر مع نفس المورد أو في نفس الفترةارتفاع أسعار موردمقارنة متوسط total_amount لنفس المورد عبر فترات زمنية في الـ data المُسترجعةمصاريف متكررة غير معتادةنفس المبلغ ± 5% يظهر أكثر من مرة مع نفس الموردتركّز الإنفاقمورد واحد > 40% من إجمالي الفترةاتجاه تصاعدي في الإنفاقمقارنة مجاميع شهرية أو ربع سنوية

Output يُكتب في State:

invoice_analysis: {
    summary: str,
    patterns_detected: list[{
        pattern_type: str,
        description: str,
        severity: "high" | "medium" | "low",
        affected_vendor: str | null,
        evidence: str
    }],
    key_metrics: dict,
    recommendations: list[str],
    has_anomaly: bool
}

قرار تصميمي مهم: الـ InvoiceAnalysisNode يضع has_anomaly = True في الـ State لو اكتشف أي pattern بـ severity "high" — وده يُفعّل الـ Alert Card في Sprint 5 تلقائياً.


5. State Model Updates

الـ M1State الموجود في agents/m1/schemas/m1_state.py يحتاج إضافة الـ fields دي:

Fields الجديدة المطلوبة:

# Invoice Sub-Pipeline Context
invoice_context: dict | None          ← output من InvoiceIntentParamExtractorNode
invoice_query: dict | None            ← output من InvoiceQueryBuilderNode
raw_invoice_data: list | None         ← output من InvoiceDBExecutionNode
invoice_row_count: int | None         ← عدد الصفوف المُسترجعة
invoice_execution_error: str | None   ← خطأ التنفيذ لو حصل
invoice_analysis: dict | None         ← output من InvoiceAnalysisNode

ملاحظة على التوافق:

الـ raw_data الموجودة في الـ State من Sprint 2 خاصة بـ db_query_tool — نحتفظ بيها كما هي. الـ invoice pipeline يستخدم raw_invoice_data منفصلة لتجنب التعارض. ValidationEnrichmentNode الموجود يحتاج تعديل بسيط يخليه يقرأ من raw_invoice_data لو intent == invoice_analysis.


6. Intent Extraction Design

6.1 الـ Prompt Strategy

الـ InvoiceIntentParamExtractorNode يستخدم system prompt مُختلف عن الـ Intent Classifier — هو متخصص 100% في invoice parameters.

أمثلة على الاستخراج الصحيح:

Query: "حللّي فواتير الموردين في الربع الأول من 2025"
→ analysis_type: "batch_analysis"
→ batch_subtype: "totals"
→ start_date: "2025-01-01"
→ end_date: "2025-03-31"
→ vendor_id: null

Query: "مين أغلى 5 موردين خلال السنة اللي فاتت؟"
→ analysis_type: "batch_analysis"
→ batch_subtype: "top_vendors"
→ start_date: (last year start)
→ end_date: (last year end)
→ limit: 5

Query: "الفاتورة INV-0045 فيها إيه؟"
→ analysis_type: "single_invoice"
→ invoice_display_id: "INV-0045"

Query: "Vendor price increases for Al-Rashid Supplies in Q4?"
→ analysis_type: "batch_analysis"
→ batch_subtype: "vendor_comparison"
→ vendor_name: "Al-Rashid Supplies"
→ start_date: (Q4 start)
→ end_date: (Q4 end)

6.2 تحديد الـ batch_subtype الافتراضي

لو الـ query غامض ومش واضح الـ subtype، الـ node يختار "totals" كـ default آمن.

6.3 التعامل مع التواريخ النسبية

الـ Prompt يُوضّح للـ model إن التاريخ الحالي هو {current_date} ويطلب منه يحوّل:


"الربع الأول" → 2025-01-01 to 2025-03-31
"السنة اللي فاتت" → 2024-01-01 to 2024-12-31
"آخر 3 أشهر" → يحسب من current_date



7. SQL Template Strategy

7.1 الـ Templates الثمانية

كل template عبارة عن string بـ named placeholders (:param_name) تُملأ بشكل آمن من قِبَل SQLAlchemy — لا string concatenation، لا f-strings في الـ SQL.

#اسم الـ Templateالهدفالجداولالـ Params1SINGLE_INVOICE_DETAILتفاصيل فاتورة واحدة كاملةinvoices, invoice_items, vendorsinvoice_display_id2INVOICE_TOTALS_BY_DATEإجمالي الفواتير في فترةinvoicesstart_date, end_date3INVOICE_VAT_SUMMARYإجمالي ضريبة القيمة المضافةinvoicesstart_date, end_date4TOP_VENDORS_BY_COSTأعلى N موردين تكلفةًinvoices, vendorsstart_date, end_date, limit5OVERDUE_INVOICESالفواتير المتأخرةinvoices, vendorsas_of_date, vendor_id (optional)6VENDOR_COST_OVER_TIMEتطور تكلفة مورد عبر الزمنinvoices, vendorsvendor_id, start_date, end_date7INVOICE_TREND_ANALYSISاتجاه الإنفاق الإجمالي شهرياًinvoicesstart_date, end_date8RECURRING_EXPENSE_ANALYSISالفواتير ذات المبالغ المتكررةinvoices, vendorsstart_date, end_date, vendor_id (optional)

7.2 ملف التخزين

كل الـ templates تُعرَّف في ملف واحد agents/m1/tools/invoice_templates.py كـ dictionary:

pythonINVOICE_TEMPLATES = {
    "SINGLE_INVOICE_DETAIL": "SELECT ...",
    "INVOICE_TOTALS_BY_DATE": "SELECT ...",
    ...
}


8. Database Access Rules

8.1 قواعد لا استثناء فيها

القاعدة 1: كل DB calls من InvoiceDBExecutionNode تستخدم READONLY_DB_URL فقط.

القاعدة 2: كل SQL يمر بـ AST validation قبل التنفيذ — يُرفض أي statement غير SELECT.

القاعدة 3: الجداول المسموح بها محددة بـ whitelist: {'invoices', 'invoice_items', 'vendors'}.

القاعدة 4: لا string formatting في الـ SQL — كل الـ parameters تُمرَّر عبر SQLAlchemy's bindparam.

القاعدة 5: نتائج الـ query تُحدَّد بـ LIMIT 500 لتجنب استعلامات ضخمة.

8.2 Reuse من Sprint 2

Sprint 3 يستورد ويُعيد استخدام نفس الـ validation functions من Sprint 2 — لا يُعيد كتابتها. الاختلاف الوحيد: يُضيف whitelist check للجداول المسموحة للـ invoice pipeline.


9. Analysis Engine Design

9.1 مبدأ الـ Two-Pass Analysis

Pass 1 — Rule-Based Pre-Analysis (بدون LLM):
قبل ما يبعت أي حاجة للـ LLM، الـ node نفسه يحسب metrics بسيطة من الـ raw data في Python:


إجمالي الإنفاق
عدد الفواتير المتأخرة ونسبتها
المورد الأعلى تكلفة ونسبته من الإجمالي
هل في مورد بيمثل > 40% من الإجمالي؟
حساب % التغيير بين أول وآخر period في trend data


Pass 2 — LLM Narrative + Deep Pattern Analysis:
يبعت للـ LLM الـ raw data + نتائج Pass 1 ويطلب منه:


يكتب narrative analysis بلغة الـ user
يُحدد severity لكل pattern
يكتب recommendations قابلة للتنفيذ


9.2 Context Window Management

لو raw_invoice_data كبيرة (> 100 row)، الـ node يعمل pre-aggregation في Python قبل إرسالها للـ LLM.


10. Pattern Detection Logic

10.1 الـ Patterns المطلوبة وكيف تُكتشف

Pattern A — Systematic Payment Delays

إذا: (عدد الفواتير المتأخرة / إجمالي الفواتير) > 0.3
أو: نفس المورد له أكثر من 2 فاتورة متأخرة
→ severity: "high" لو > 50%، "medium" لو 30-50%

Pattern B — Vendor Price Increase

احسب % التغيير في avg_per_invoice بين أول period وآخر period
إذا: التغيير > 10% → severity: "medium"
إذا: التغيير > 25% → severity: "high"

Pattern C — Unusual Recurring Expenses

إذا: occurrence_count > 2 لنفس المبلغ من نفس المورد
→ severity: "medium"

Pattern D — Spending Concentration Risk

احسب: top_vendor_amount / total_period_amount
إذا: النسبة > 40% → severity: "medium"
إذا: النسبة > 60% → severity: "high"

Pattern E — Abnormal Spending Trend

إذا: معدل النمو > 20% شهرياً لـ 3 أشهر متتالية
→ severity: "medium"

10.2 Severity Thresholds (constants قابلة للتعديل)

pythonCONCENTRATION_RISK_THRESHOLD = 0.40
PRICE_INCREASE_MEDIUM_THRESHOLD = 0.10
PRICE_INCREASE_HIGH_THRESHOLD = 0.25
PAYMENT_DELAY_MEDIUM_THRESHOLD = 0.30
PAYMENT_DELAY_HIGH_THRESHOLD = 0.50
TREND_ALERT_MONTHLY_GROWTH = 0.20
TREND_ALERT_CONSECUTIVE_MONTHS = 3


11. File-by-File Implementation Plan

الترتيب الإلزامي للتنفيذ

#الملفالحالةالأولوية1agents/m1/tools/invoice_templates.pyجديدأولاً — لا dependencies2agents/prompts/invoice_analysis.pyجديدثانياً — لا dependencies3agents/m1/schemas/m1_state.pyيُعدَّلثالثاً — قبل أي node4agents/m1/nodes/invoice_intent_extractor_node.pyجديدرابعاً5agents/m1/nodes/invoice_query_builder_node.pyجديدخامساً6agents/m1/nodes/invoice_db_execution_node.pyجديدسادساً7agents/m1/nodes/invoice_analysis_node.pyجديدسابعاً8agents/m1/graphs/m1_graph.pyيُعدَّلثامناً9agents/m1/nodes/stub_nodes.pyيُعدَّلتاسعاً10scripts/test_sprint3.pyجديدعاشراً


12. Testing Strategy

12.1 Test Cases المطلوبة في test_sprint3.py

اختبارات Single Invoice:

#الـ QueryالمتوقعTC-01"الفاتورة INV-0045 فيها إيه؟" (AR)analysis_type=single_invoice, بيانات الفاتورةTC-02"Show me details for invoice INV-0100" (EN)نفس النتيجة بالإنجليزيTC-03فاتورة مش موجودة "INV-9999"graceful error message

اختبارات Batch Analysis:

#الـ QueryالمتوقعTC-04"إيه إجمالي فواتير الربع الأول؟"batch_subtype=totalsTC-05"مين أغلى 5 موردين السنة دي؟"batch_subtype=top_vendors, 5 موردينTC-06"فيه فواتير متأخرة السداد؟"batch_subtype=overdueTC-07"Analyze vendor cost trends for last quarter"batch_subtype=vendor_comparisonTC-08"كام ضريبة قيمة مضافة دفعنا في 2025؟"batch_subtype=vat_summary

اختبارات Pattern Detection:

#السيناريوالمتوقعTC-09بيانات فيها مورد > 60% من الإنفاقconcentration_risk pattern مكتشفTC-10بيانات فيها ارتفاع أسعار > 25%price_increase بـ severity "high"

اختبارات Safety:

#السيناريوالمتوقعTC-11محاولة استعلام عن جدول customersالـ node يرفض بـ whitelist errorTC-12extraction_confidence < 0.6يُعيد توجيهه لـ ClarificationNode

اختبارات Bilingual:

#السيناريوالمتوقعTC-13Query عربيnarrative بالعربيTC-14Query إنجليزيnarrative بالإنجليزي


13. Acceptance Criteria

Sprint 3 يُعتبر مكتملاً فقط لما كل النقاط دي تتحقق:

#Criterionالملف المسؤولAC-01الـ M1 Graph يُكمَّل بدون errors بعد إضافة الـ 4 nodesm1_graph.pyAC-02الـ intent extractor يستخرج params صحيحة بـ confidence > 0.7 في TC-01→TC-08invoice_intent_extractor_node.pyAC-03الـ 8 templates تُولَّد SQL صحيح وتُنفَّذ بنجاح على Supabaseinvoice_templates.pyAC-04الـ DB execution node يرفض أي SQL يحتوي على جداول خارج الـ whitelistinvoice_db_execution_node.pyAC-05الـ analysis node يكشف على الأقل واحد من الـ patterns لما البيانات تحتويهاinvoice_analysis_node.pyAC-06الـ has_anomaly flag يُعيَّن صح لما في patterns بـ severity "high"invoice_analysis_node.pyAC-07الـ graceful degradation يشتغل لما الفاتورة مش موجودةinvoice_db_execution_node.pyAC-08كل الـ 14 test cases في test_sprint3.py تعدي (PASS)test_sprint3.pyAC-09الـ ValidationEnrichmentNode الموجود يشتغل صح بعد الـ invoice pipelinem1_graph.pyAC-10لا regression في Sprint 1 و Sprint 2 teststest_sprint1.py, test_sprint2.py


14. Risks and Mitigations

RiskالخطرالتخفيفR-01 — State Fields Conflictإضافة fields جديدة للـ M1State قد تكسر الـ graphمراجعة total=False في TypedDict + تشغيل graph.compile() فوراً بعد كل تعديلR-02 — Vendor Name Lookupالمستخدم يكتب اسم عربي والـ DB فيها اسم إنجليزياستخدام ILIKE '%:vendor_name%' مش exact match + graceful message لو مفيش نتيجةR-03 — Large Result Setsاستعلام على سنة كاملة يرجع 300+ فاتورةLIMIT 500 في كل query + pre-aggregation في Python لأي result > 50 rowR-04 — Pattern False Positivesالـ mock data مش واقعية كفايةمراجعة الـ mock data قبل البدء + thresholds كـ constants قابلة للتعديلR-05 — Graph Regressionتعديل m1_graph.py يكسر الـ routing للـ intents التانيةتشغيل test_sprint1.py و test_sprint2.py بعد كل تعديل في الـ graphR-06 — DB Timeoutبعض الـ templates على بيانات كبيرة قد تستغرق وقتكل templates بتستخدم indexed columns + query timeout = 30 ثانية


15. Detailed Execution Order

Pre-Sprint Tasks (يوم واحد قبل البدء)

Task 0.1 — تحقق من الـ Mock Data
شغّل query بسيط على Supabase للتأكد:


جدول invoices فيه بيانات بتواريخ متنوعة
جدول invoices فيه payment_status values متنوعة (Paid, Unpaid, Overdue)
جدول invoices فيه فواتير مربوطة بـ vendor_id
جدول vendors فيه على الأقل 3 vendors مختلفين
لو البيانات ناقصة → يُضاف seed data قبل البدء


Task 0.2 — تحقق من Sprint 2 Validation Layer
تأكد إن الـ AST parser الموجود accessible كـ importable function — لو مش كده، يُعاد هيكلته لملف مشترك agents/shared/sql_validator.py قبل Sprint 3.


Sprint 3 Execution Order (5 أيام)

اليوم 1 — Data Layer


✅ agents/m1/tools/invoice_templates.py — كل الـ 8 templates
اختبار يدوي: تشغيل كل SQL على Supabase مباشرة للتأكد إنه صح


اليوم 2 — Prompts + State


✅ agents/prompts/invoice_analysis.py — الـ 2 prompts
✅ تعديل agents/m1/schemas/m1_state.py — إضافة 6 fields
تشغيل test_sprint1.py للتأكد من عدم الـ regression


اليوم 3 — Node 1 + Node 2


✅ agents/m1/nodes/invoice_intent_extractor_node.py
✅ agents/m1/nodes/invoice_query_builder_node.py
اختبار مستقل لكل node بدون graph


اليوم 4 — Node 3 + Node 4


✅ agents/m1/nodes/invoice_db_execution_node.py
✅ agents/m1/nodes/invoice_analysis_node.py
اختبار pipeline الـ 4 nodes مع بعض بدون graph


اليوم 5 — Graph Integration + Testing


✅ تعديل agents/m1/graphs/m1_graph.py
✅ تعديل agents/m1/nodes/stub_nodes.py
✅ كتابة scripts/test_sprint3.py
تشغيل كل الـ tests (sprint1 + sprint2 + sprint3)
تحديث docs/progress/agent_execution_log.md بـ Step 18



Checklist نهاية Sprint 3

□ invoice_templates.py — 8 templates، قابلة للاستيراد
□ invoice_analysis.py prompts — ثنائي اللغة
□ M1State — 6 fields جديدة، لا regression
□ invoice_intent_extractor_node.py — structured output يعمل
□ invoice_query_builder_node.py — template selection صح
□ invoice_db_execution_node.py — readonly، whitelist، error handling
□ invoice_analysis_node.py — two-pass، pattern detection، bilingual narrative
□ m1_graph.py — 4 nodes مضافة، stub محذوف، compile ينجح
□ test_sprint3.py — 14 test cases، كلها PASS
□ test_sprint1.py — كلها PASS (no regression)
□ test_sprint2.py — كلها PASS (no regression)
□ agent_execution_log.md — Step 18 مُضاف
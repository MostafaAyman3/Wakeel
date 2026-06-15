# M1 — Sprint Plan: AI ERP Intelligence Agent

---

## Sprint 0 — Infrastructure & DB Setup
**المدة:** 4 أيام

**DB Schema — الجداول الإلزامية:**
`clients, invoices, invoice_items, orders, products, transactions, payments, vendors`

حقول `invoices` الأساسية: `vendor_id, invoice_date, total_amount, tax_amount, due_date, payment_status, line_items`

- seed بيانات mock واقعية ومتسقة (لا بيانات عشوائية — العلاقات بين الجداول متسقة)
- إنشاء Read-Only DB user (SELECT فقط — خط الدفاع الأول)
- تفعيل `pgvector` extension على PostgreSQL (مطلوب للـ Tax RAG لاحقاً)
- FastAPI project setup + LangGraph + SQLAlchemy async pool
- LLM Client: instance واحدة مُهيأة (GPT-4o + GPT-4o-mini) تُستخدم من كل الـ nodes
- Shared Services: JWT auth skeleton + logging layer + error handler موحّد
- `user_context` يُستخرج من الـ JWT عند كل request ويُمرَّر كحقل في الـ LangGraph State — لا يُعاد جلبه في كل node
- `.env` للـ API keys والـ DB connection

**المخرج:** DB شغالة + project skeleton + shared services جاهزة

---

## Sprint 1 — LangGraph Skeleton + Intent Classifier
**المدة:** 5 أيام

**قرار معماري (من البلوبرنت section 2.4):** Single Orchestrator (LangGraph StateGraph) — لا Multi-Agent في MVP. كل العمل sequential عبر Tool Nodes داخل orchestrator واحد.

**LangGraph State Schema (كامل مع الأنواع):**
```python
{
  query:            str,
  language:         "ar" | "en",      # auto-detect من النص
  intent:           IntentType,        # financial_query | operational_query | invoice_analysis | tax_reasoning | clarification_needed
  extracted_params: dict,              # تاريخ، customer_id، فئة...
  raw_data:         list,              # النتائج الخام من DB أو RAG
  data_confidence:  float,             # 0.0 → 1.0
  output_format:    OutputType,        # direct_text | metric_card | table | bar_chart | line_chart | narrative | alert
  narrative:        str,               # التحليل اللغوي المُولَّد
  final_response:   dict,              # { format, data, chart_config, narrative, alert, disclaimer? }
  user_context:     dict               # اختياري — { user_id, role, permissions } من الـ JWT
}
```

**توثيق routing الـ executive_summary:**
`executive_summary` ليس intent مستقل — يُروَّت عبر `financial_query` ويُنفَّذ بـ Template 10 (ملخص تنفيذي: مبيعات + مصروفات + صافي). لا يحتاج node أو routing إضافي.

- `IntentClassifierNode` (GPT-4o-mini): يصنف إلى `financial_query / operational_query / invoice_analysis / tax_reasoning / clarification_needed`
- `RouterNode`: يوجّه لكل tool بناءً على الـ intent
- `ClarificationNode`: يطلب توضيح لو intent غير واضح أو params ناقصة
- `ValidationEnrichmentNode`: يتحقق من اكتمال البيانات المُسترجعة ويُثريها بالسياق — يأتي بعد كل tool مباشرة
- endpoint `/query` يستقبل `{ query, language }` ويرجع JSON

**المخرج:** agent يصنّف، يوجّه، ويتحقق — بدون data retrieval بعد

---

## Sprint 2 — Dynamic Query Builder (Templates)
**المدة:** 5 أيام

**قائمة الـ 10 Templates الإلزامية:**
1. إيرادات فترة زمنية محددة
2. أداء منتج/فئة (مقارنة بفترة سابقة)
3. عملاء متأخرون في السداد — Aging Buckets (30/60/90+ يوم)
4. فواتير مورد بعينه (فترة / مبلغ / حالة)
5. إجمالي ضريبة القيمة المضافة في فترة
6. أعلى / أدنى N عملاء أو منتجات
7. اكتشاف شذوذات المصاريف (مقارنة بالمتوسط — يُطلق Alert)
8. أداء المبيعات على فترة زمنية (time series للـ Line Chart)
9. مقارنة فئات المنتجات بالإيراد
10. ملخص تنفيذي (مبيعات + مصروفات + صافي في فترة)

- `db_query_tool`: يُطابق intent مع template، يستخرج params من الـ LLM، يُنفّذ على DB
- Validation Layer: AST check (SELECT only) + مقارنة columns بالـ schema الفعلي
- اختبار كل template بأسئلة عربية وإنجليزية حقيقية

**آلية الـ confidence المنخفض (MVP solution):**
لو `data_confidence < 0.70` في الـ `ValidationEnrichmentNode` → يُحوَّل الـ intent إلى `clarification_needed` ويطلب من المستخدم إعادة الصياغة. لا approval UI معقدة في MVP.

**الطبقة الثالثة — NL2SQL (مؤجلة بعد MVP):**
البلوبرنت صريح: "ابدأ بـ Templates فقط. أضف NL2SQL لاحقاً بعد اختبار Templates." — لا تُنفَّذ في هذا الـ Sprint.

**المخرج:** M1 يجيب على الاستعلامات المالية والتشغيلية — مع anomaly detection أساسي

---

## Sprint 3 — Invoice Analysis Tool
**المدة:** 4 أيام

**الـ Sub-Pipeline (4 nodes):**
- `IntentParamExtractorNode`: يستخرج نطاق زمني، vendor_id، نوع التحليل (فاتورة واحدة / batch)
- `QueryBuilderNode`: يختار template مناسب أو يُولّد SQL من params
- `DBExecutionNode` (Read-Only): يُنفّذ على `invoices, invoice_items, vendors`
- `AnalysisNode` (GPT-4o): يكتشف patterns — تأخر الدفع الممنهج، ارتفاع أسعار مورد بعينه، تكاليف متكررة غير معتادة

**Templates خاصة بالفواتير:**
- مجموع فواتير فترة (مع VAT منفصل)
- أعلى vendors بالتكلفة
- فواتير متأخرة السداد
- مقارنة تكلفة مورد بعينه عبر الزمن (Pattern Detection)

**ملاحظة:** الـ `QueryBuilderNode` يعمل بـ Templates فقط في هذا الـ Sprint — الجزء الخاص بتوليد SQL للحالات غير المغطاة مؤجل بعد MVP (نفس مبدأ Sprint 2).

**المخرج المتوقع من الـ sub-pipeline:** `Metric Card + Pattern Insights + Chart` — كما هو محدد في البلوبرنت section 2.6

**المخرج:** agent يحلل الفواتير من DB ويكتشف patterns مالية

---

## Sprint 4 — Tax RAG
**المدة:** 4 أيام

- تجهيز 3-5 مستندات قواعد ضريبية (PDF/text) من مصادر رسمية
- chunking + text-embedding-3-small → pgvector (الـ extension جاهز من Sprint 0)
- `tax_rag_tool`: retrieval للقواعد الأكثر صلة → GPT-4o يستنتج الإجابة
- كل رد ضريبي يُرجع: `{ answer, legal_reference, disclaimer }`
- disclaimer ثابت: "توجيه استرشادي — استشر مستشاراً ضريبياً للقرارات الرسمية"

**قيود إلزامية في التنفيذ (من البلوبرنت section 2.7 — ما نتجنبه):**
- ❌ لا ادعاء بحساب ضريبة بدقة مطلقة — كل رد تقريبي واسترشادي
- ❌ لا إجابة على أسئلة خارج نطاق القواعد المُحمَّلة — الـ agent يُقرّ بعدم معرفته
- ❌ لا تقديم المخرج كاستشارة قانونية ملزمة — disclaimer إلزامي في كل رد

**اختبار edge cases:**
- سؤال خارج نطاق القواعد المُحمَّلة → الـ agent يرفض بدل ما يخترع
- سؤال غامض → يطلب توضيح قبل الإجابة

**المخرج:** M1 يجيب على الأسئلة الضريبية بمرجع قانوني وحدود واضحة

---

## Sprint 5 — Adaptive Output Selector + Narrative Generator
**المدة:** 5 أيام

**`OutputSelectorNode` — مبدأ القرار المزدوج (من البلوبرنت section 2.8):**
القرار يعتمد على **نية السؤال + شكل البيانات الفعلي المُسترجع معاً** — ليس أحدهما وحده.

**8 أنواع مخرجات:**

| Trigger | Output |
|---------|--------|
| row=1, col=1 | Direct Text |
| scalar + context | Metric Card (رقم كبير + مقارنة) |
| 1-5 rows | Formatted Text List |
| N rows × M cols (>5) | Sortable Table |
| categorical + values, ≤ 12 item | Bar Chart + mini table |
| categorical + values, > 12 item | Sortable Table (Bar Chart غير قابل للقراءة) |
| time_column موجود | Line Chart + narrative |
| intent = explanation/analysis | Narrative Text فقط |
| anomaly_detected = true | Alert Card (ملون) + تفسير + توصية |

- `NarrativeGeneratorNode` (GPT-4o): تحليل لغوي للنتائج — مش عرض بيانات خام
- Proactive Anomaly Detection: يشتغل على كل query تشغيلية ومالية — لو شذوذ يُطلق Alert Card تلقائياً
- response schema موحّد: `{ format, data, chart_config, narrative, alert, disclaimer? }`

**المخرج:** كل رد بالشكل الصح تلقائياً + anomaly detection فعّال

---

## Sprint 6 — Frontend Chat UI + Integration
**المدة:** 5 أيام

**Components:**
- Chat interface (React + TypeScript + shadcn/ui): input ثنائي اللغة + conversation history
- Output renderers: Apache ECharts (Line/Bar) + Sortable Table + Metric Card + Alert Card
- ربط كل الـ components بـ `/query` endpoint

**اختبار الـ 5 Demo Scenarios:**
1. "إيه أداء المبيعات في الربع الثاني مقارنة بالأول؟" → Line Chart + Narrative
2. "مين العملاء المتأخرين في السداد أكتر من 30 يوم؟" → Aging Table
3. "حللّي فواتير الموردين في الربع الأول" → Pattern Detection + Metric Card
4. "فاتورتي بـ 50,000 جنيه، القيمة المضافة إيه؟" → Narrative + Legal Reference
5. شذوذ تلقائي: ارتفاع 340% في فئة الصيانة → Alert Card

**المخرج:** M1 شغال end-to-end، الـ 5 scenarios تعمل، جاهز للعرض

---

## ما هو مؤجل (لا يُنفَّذ في MVP)

من البلوبرنت section 2.3 — للرجوع إليها عند التخطيط للمراحل التالية:
- Real-time streaming responses (SSE / WebSocket)
- Predictive analytics وتوقعات الإيرادات المستقبلية
- Fine-tuned local model خاص بـ ERP domain
- Custom dashboard builder (drag and drop)
- Integration مع APIs رسمية خارجية (مثل مصلحة الضرائب)
- Scheduled automated reports (cron job فوق الـ API)
- Multi-user permissions granularity
- NL2SQL (الطبقة الثالثة للـ Query Builder) — تُضاف بعد اختبار Templates

## Limitations يجب الإفصاح عنها في العرض

- لا real-time integration مع أنظمة ERP خارجية في MVP
- دقة استعلامات SQL المعقدة تعتمد على جودة schema والـ prompt engineering
- التحليل الضريبي استرشادي وليس ملزماً قانونياً
- أداء اللغة العربية يعتمد على capabilities اللغوية للـ LLM المُختار

---

## ملخص الجدول الزمني

| Sprint | المحتوى | المدة |
|--------|---------|-------|
| 0 | DB + Shared Services + Setup | 4 أيام |
| 1 | LangGraph + Intent Classifier + Validation Node | 5 أيام |
| 2 | Query Builder — 10 Templates | 5 أيام |
| 3 | Invoice Analysis Tool | 4 أيام |
| 4 | Tax RAG | 4 أيام |
| 5 | Output Selector (8 أنواع) + Narrative + Anomaly | 5 أيام |
| 6 | Frontend + Integration + Demo Scenarios | 5 أيام |
| **المجموع** | | **~32 يوم** |

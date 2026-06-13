# ERP Agentic AI Platform — وثيقة تصميم المنتج والهندسة المعمارية

> **الإصدار:** 1.0 | **الفريق:** 6 أشخاص | **السياق:** مشروع تخرج / منحة موجّهة للشركات

---

## أولاً: رؤية المنتج وإعادة الصياغة

### ما هو المنتج فعلاً؟

**ERP Agentic AI Platform** ليست chatbot مُضافة فوق نظام ERP. هي **Agentic Intelligence Layer** — طبقة ذكاء تعمل داخل بيئة ERP الموجودة، تفهم السياق التجاري، وتُحوّل الاستعلامات اللغوية الطبيعية إلى رؤى قابلة للتنفيذ، مع أتمتة دعم العملاء وتمكين القرارات التشغيلية.

**الفارق الجوهري عن المنافسين:** الأنظمة التقليدية تعرض البيانات فقط. هذه المنصة تُحلل، تُفسّر، وتتصرف — والقرار النهائي يبقى دائماً بيد الإنسان.

### خريطة الموديولات

| الموديول | الأولوية | الهدف الجوهري | حالة التنفيذ |
|---------|---------|--------------|-------------|
| M1 — AI ERP Intelligence Agent | عالية جداً | تحليل البيانات والاستعلامات اللغوية | **ينفّذ الآن** |
| M3 — Customer Support Agent | عالية جداً | دعم العملاء وحل المشكلات | **ينفّذ الآن** |
| M2 — Purchasing/Inventory Agent | مؤجل | أتمتة المشتريات والمخزون | **تصميم جاهز، تنفيذ مشروط** |

---

## ثانياً: الموديول الأول — AI ERP Intelligence Agent

### 2.1 هدف الموديول

تحويل أي سؤال تجاري باللغة الطبيعية (عربي/إنجليزي) إلى رؤية تحليلية كاملة مُستخرجة من بيانات ERP الفعلية، مع تقديم المخرج بالشكل الأنسب لنوع السؤال ومستوى المستخدم — دون أن يحتاج المستخدم لكتابة سطر استعلام واحد.

### 2.2 Use Cases الأساسية (مجمّعة في 4 مجاميع)

**المجموعة الأولى — Financial Intelligence**
- تقارير الإيرادات والمصروفات الدورية (يومي / شهري / ربعي)
- تحليل العملاء المتأخرين في السداد مع تحليل أعمار الديون (Aging Analysis)
- أداء المنتجات والفئات خلال فترة زمنية محددة
- ملخصات تنفيذية للأداء المالي الشامل

**المجموعة الثانية — Operational Intelligence**
- استعلامات حالة الطلبات والعمليات الجارية
- تحليل أنماط المبيعات واكتشاف الاتجاهات
- مقارنة الأداء بين فترات زمنية مختلفة
- اكتشاف الشذوذات وإطلاق تنبيهات تلقائية

**المجموعة الثالثة — Invoice Intelligence**
- استعلام وتحليل بيانات الفاتورة مباشرةً من جداول DB — لا OCR، لا معالجة PDF
- تلخيص مجموعة فواتير في فترة زمنية في رؤية واحدة
- اكتشاف أنماط: تأخر الدفع، الموردون الأعلى تكلفة، التكاليف المتكررة
- توليد تقارير الفواتير المالية والتشغيلية

**المجموعة الرابعة — Tax Reasoning (محدود وآمن)**
- الإجابة على أسئلة ضريبية معيارية بناءً على قواعد مُحمَّلة مسبقاً
- تقدير الضريبة على سيناريوهات محددة
- كل إجابة ضريبية تحمل disclaimer واضح: "توجيه استرشادي، استشر مستشاراً ضريبياً للقرارات الرسمية"

### 2.3 Features: أساسي vs مؤجل

**المجموعة الإلزامية في MVP**

- **Intent Classifier:** تصنيف نية المستخدم إلى: financial_query، operational_query، invoice_analysis، tax_reasoning، clarification_needed
- **Dynamic Query Builder:** توليد SQL آمن بناءً على النية المكتشفة — Template-First Strategy تغطي 80% من الحالات، مع NL2SQL + Validation Layer للـ 20% المتبقية، وطبقة Read-Only DB User كحماية إلزامية
- **Invoice Analysis Tool:** استعلام مباشر من جداول الفواتير في DB → تجميع وتحليل → اكتشاف أنماط — لا OCR، لا معالجة PDF
- **RAG Engine for Tax:** تحميل مستندات القواعد الضريبية في vector store، الإجابة بالاسترجاع مع الإشارة للمصدر
- **Adaptive Output Selector:** اختيار تلقائي للشكل الأنسب (جدول، chart، نص، بطاقة dashboard، تنبيه)
- **Narrative Generator:** توليد تحليل لغوي حقيقي للنتائج، وليس عرض بيانات خام
- **Bilingual Support:** عربي/إنجليزي في الإدخال والمخرج بشكل طبيعي

**مؤجل للمرحلة التالية**

- Real-time streaming responses (SSE / WebSocket)
- Predictive analytics وتوقعات الإيرادات المستقبلية
- Fine-tuned local model خاص بـ ERP domain
- Custom dashboard builder (drag and drop)
- Integration مع APIs رسمية خارجية (مثل مصلحة الضرائب)
- Scheduled automated reports (يمكن لاحقاً كـ cron job مُضافة فوق الـ API)
- Multi-user permissions granularity (في MVP: صلاحية واحدة للمستخدمين كلهم)

### 2.3.1 Dynamic Query Builder — طبقات الأمان (Template-First Approach)

الخطر الحقيقي في أي NL2SQL: الـ model يكتب SQL خاطئ منطقياً، يُخطئ في الـ schema، أو — الأخطر — يكتب destructive queries. الحل: ثلاث طبقات حماية مُتراكمة.

**الطبقة الأولى — Read-Only DB User (إلزامية وغير قابلة للتجاوز)**

الـ agent يتصل بـ PostgreSQL عبر user يملك `SELECT` فقط على مستوى قاعدة البيانات. حتى لو الـ model كتب `DROP TABLE` أو `DELETE`، قاعدة البيانات ترفضه قبل التنفيذ. هذا خط الدفاع الأساسي.

**الطبقة الثانية — Query Templates للـ 80% من الحالات (الاستراتيجية الأساسية في MVP)**

بدلاً من أن يكتب الـ model SQL من الصفر، تُعرَّف مسبقاً مجموعة Templates للاستعلامات الشائعة. الـ model يملأ المعاملات فقط (تاريخ، customer_id، فئة...) — لا يكتب SQL.

```sql
-- Template: top_products_by_revenue
-- Parameters: {start_date, end_date, limit}
SELECT product_name, SUM(amount) AS revenue
FROM invoices
WHERE invoice_date BETWEEN :start_date AND :end_date
GROUP BY product_name
ORDER BY revenue DESC
LIMIT :limit
```

قائمة Templates المقترحة لـ MVP (10-15 template تغطي معظم الأسئلة التجارية الحقيقية):
- إيرادات فترة زمنية محددة
- أداء منتج/فئة (مقارنة بفترة سابقة)
- عملاء متأخرون في السداد (Aging Buckets)
- فواتير مورد بعينه (فترة / مبلغ / حالة)
- إجمالي ضريبة القيمة المضافة في فترة
- أعلى / أدنى N عملاء أو منتجات
- اكتشاف شذوذات المصاريف (مقارنة بالمتوسط)

**الطبقة الثالثة — NL2SQL مع Validation للـ 20% المتبقية**

للأسئلة التي لا يغطيها أي template، الـ model يكتب SQL لكن تمر بـ Validation Layer قبل التنفيذ:
- التحقق من أن الـ query `SELECT` فقط (SQL AST parser)
- مقارنة أسماء الجداول والـ columns بالـ schema الفعلي
- لو confidence منخفض → يعرض الـ SQL على المستخدم للموافقة قبل التنفيذ

**توصية MVP:** ابدأ بـ Templates فقط. أضف NL2SQL لاحقاً بعد اختبار Templates.



**التوصية القاطعة: Single Orchestrator (LangGraph) مع Tool Nodes**

المبرر التقني:
- الاستعلامات في هذا الموديول غالباً sequential، لا تحتاج parallel execution في MVP
- LangGraph StateGraph يوفر مرونة كافية مع tool routing واضح
- أسهل في debugging، testing، وshowcase أمام لجان التقييم
- يقلل التعقيد على فريق من 6 أشخاص بشكل كبير

متى نذهب لـ Multi-Agent؟ فقط لو احتجنا parallel data fetching من مصادر 3+ في نفس الوقت — هذا خارج نطاق MVP.

### 2.5 Agent Workflow التفصيلي

```
User Query (AR/EN)
       │
       ▼
┌─────────────────────────────────────────────┐
│           Intent Classifier Node            │
│  (يحدد: نوع السؤال + المعاملات المطلوبة)   │
└──────────────────┬──────────────────────────┘
                   │
       ┌───────────▼───────────┐
       │ يحتاج توضيح؟          │
       │ YES → Clarification   │
       │ NO  → continue        │
       └───────────┬───────────┘
                   │
    ┌──────────────▼──────────────────────┐
    │           Router Node               │
    ├─ financial/operational → DB Query   │
    ├─ invoice_analysis → Invoice Analysis│
    └─ tax_reasoning → RAG Agent          │
    └─────────────────────────────────────┘
                   │
    ┌──────────────▼──────────────────────┐
    │      Data Retrieval (Tools)         │
    ├─ db_query_tool (SQL → PostgreSQL)   │
    ├─ invoice_analysis_tool (SQL → DB)  │
    └─ tax_rag_tool (Query → Vector DB)   │
    └─────────────────────────────────────┘
                   │
    ┌──────────────▼──────────────────────┐
    │   Validation & Enrichment Node      │
    │  (يتحقق من اكتمال البيانات وسياقها) │
    └─────────────────────────────────────┘
                   │
    ┌──────────────▼──────────────────────┐
    │      Output Formatter Node          │
    ├─ يختار الشكل: table/chart/text/card │
    └─ يُولّد narrative analysis           │
    └─────────────────────────────────────┘
                   │
                   ▼
          Response to User
```

**LangGraph State Schema**
```
{
  query: str,
  language: "ar" | "en",
  intent: IntentType,
  extracted_params: dict,
  raw_data: list,
  data_confidence: float,
  output_format: OutputType,
  narrative: str,
  final_response: dict
}
```

### 2.6 Invoice Analysis — Sub-Pipeline داخل الموديول

هذا مسار فرعي مُدمج داخل الـ Agent وليس موديول منفصل. يُفعَّل عند كشف intent من نوع invoice_analysis. الفواتير مُخزَّنة بالفعل في جداول DB — لا OCR، لا معالجة PDF، لا file uploads.

```
Invoice Query (NL من المستخدم)
       │
       ▼
┌─────────────────────────────────────────────┐
│         Intent & Param Extractor            │
│  يستخرج: نطاق زمني، vendor_id، filters،    │
│  نوع التحليل (فاتورة واحدة / batch)        │
└──────────────────┬──────────────────────────┘
                   │
    ┌──────────────▼──────────────────────┐
    │     Query Builder Node              │
    │  يختار Template المناسب أو يُولّد   │
    │  SQL مباشرة بناءً على الـ params    │
    └──────────────┬──────────────────────┘
                   │
    ┌──────────────▼──────────────────────┐
    │    DB Execution Node (Read-Only)    │
    │  يُنفّذ الاستعلام على جداول:        │
    │  invoices، invoice_items، vendors   │
    └──────────────┬──────────────────────┘
                   │
    ┌──────────────▼──────────────────────┐
    │         Analysis Node (LLM)         │
    ├─ Single invoice: summary + metrics  │
    └─ Batch: pattern detection           │
    │  ├─ تأخر الدفع الممنهج              │
    │  ├─ ارتفاع أسعار مورد بعينه         │
    │  └─ تكاليف متكررة غير معتادة        │
    └─────────────────────────────────────┘
                   │
                   ▼
    Output: Metric Card + Pattern Insights + Chart
```

**القرار التصميمي:** الفواتير في DB = لا تعقيد إضافي. الـ invoice_analysis_tool هو في جوهره db_query_tool مُخصَّص لجداول الفواتير، مع prompt مُحسَّن لاكتشاف الأنماط المالية.

### 2.7 Tax Reasoning — النهج الآمن والعملي

**النهج المقترح: RAG-based Tax Reasoning مع Scoped Context**

التنفيذ خطوة بخطوة:
- تحميل مستندات القوانين الضريبية ذات الصلة (PDFs أو نصوص منسقة) كـ knowledge base
- تقسيمها إلى chunks وتخزينها في vector store
- عند سؤال ضريبي: استرجاع القواعد الأكثر صلة → LLM يستنتج الإجابة بناءً عليها
- كل رد ضريبي يتضمن: الإجابة + المرجع القانوني المستخدم + disclaimer إلزامي

**ما نتجنبه تحديداً:**
- ادعاء القدرة على حساب الضريبة بدقة مطلقة
- الإجابة عن أسئلة ضريبية خارج نطاق القواعد المُحمَّلة
- تقديم المخرج كاستشارة قانونية ملزمة

### 2.8 Adaptive Output Selector — منطق اختيار الشكل

**مبدأ التصميم:** القرار يعتمد على اثنين معاً: **نية السؤال + شكل البيانات الفعلي المُسترجع**. ليس نية السؤال وحدها، وليس شكل البيانات وحده.

**خريطة السيناريوهات السبعة:**

| نوع السؤال | شكل البيانات | Output المناسب |
|------------|-------------|----------------|
| سؤال مباشر — "إيه نسبة الضريبة؟" | نص قصير أو رقم واحد | **نص مباشر** — لا chart، لا جدول |
| KPI واحد — "كام إجمالي المبيعات؟" | scalar + context | **Metric Card** — رقم كبير + مقارنة بالفترة السابقة |
| قائمة صغيرة ≤ 5 عناصر | 1-5 rows | **نص منسّق** أو قائمة نصية بسيطة |
| قائمة كبيرة > 5 عناصر، columns متعددة | N rows × M cols | **Table** قابلة للفرز |
| مقارنة فئات (منتجات، عملاء...) | categorical + values | **Bar Chart** + table مصغّر |
| اتجاه زمني | time series | **Line Chart** + narrative |
| تحليل نصي — "وضّح الوضع المالي" | insights معقدة | **Narrative Text** فقط |
| شذوذ أو تنبيه | condition triggered | **Alert Card** ملونة + تفسير + توصية |

**منطق اتخاذ القرار (Pseudo-code):**

```python
if result.row_count == 1 and result.col_count == 1:
    → Direct Text / Metric Card

elif query.intent == "trend" or result.has_time_column:
    → Line Chart

elif query.intent == "comparison" and result.row_count > 1:
    → Bar Chart (if ≤ 12 items) else Table

elif result.row_count > 5 and result.col_count > 2:
    → Sortable Table

elif query.intent in ["explanation", "analysis", "summary"]:
    → Narrative Text

elif anomaly_detected:
    → Alert Card
```

**ملاحظة تصميمية:** إذا سأل المستخدم "كام مجموع فواتير العميل ده؟" — الجواب رقم واحد، يُعرض كـ Metric Card أو نص مباشر. لا يُفرض عليه chart لا يحتاجها. هذا ما يجعل الـ agent يبدو ذكياً وليس آلياً.



### 2.9 Demo Scenarios القوية للشركات

**Scenario 1 — Executive Financial Query**
المدير يكتب: "إيه أداء المبيعات في الربع الثاني مقارنة بالأول؟"
النظام يُنتج: Line chart مقارن + جدول مفصّل + Narrative: "ارتفعت المبيعات 18% مع انخفاض ملحوظ في قطاع الإلكترونيات بنسبة 7%، يُنصح بمراجعة سياسة التسعير في هذه الفئة."

**Scenario 2 — Collections Intelligence**
"مين العملاء المتأخرين في السداد أكتر من 30 يوم؟"
النظام يُنتج: جدول مرتب حسب Aging Buckets (30/60/90+ يوم) + تحليل: "أعلى 3 عملاء يمثلون 65% من إجمالي المتأخرات. مجموع المستحق: X جنيه."

**Scenario 3 — Invoice Batch Intelligence**
استعلام: "حللّي فواتير الموردين في الربع الأول" → النظام يستعلم مباشرة من DB ويُنبّه: "المورد X رفع أسعاره بمعدل 12% خلال الأشهر الثلاثة الماضية. إجمالي ضريبة القيمة المضافة في هذه الدفعة: Y جنيه."

**Scenario 4 — Tax Advisory**
"فاتورتي بـ 50,000 جنيه، القيمة المضافة المستحقة إيه؟"
النظام: يسترجع القاعدة المناسبة من knowledge base → "بناءً على القانون رقم X، المادة Y: ضريبة القيمة المضافة المستحقة = 7,500 جنيه (15%). ملاحظة: هذا توجيه استرشادي."

**Scenario 5 — Proactive Anomaly Detection**
النظام يُطلق تنبيهاً تلقائياً: "🔴 لاحظ الذكاء الاصطناعي مصروفاً غير معتاد في فئة الصيانة: ارتفاع بنسبة 340% مقارنة بالمتوسط. يُنصح بمراجعة الفواتير المرتبطة."

### 2.10 البيانات المطلوبة والـ Assumptions

**البيانات الإلزامية لـ MVP**
- ERP Mock Database: schema مُصمَّمة تشمل جداول: clients، invoices، invoice_items، orders، products، transactions، payments، vendors
- بيانات mock واقعية ومتسقة داخلياً (لا بيانات عشوائية)
- الفواتير مُخزَّنة كـ structured records في DB — لا حاجة لملفات PDF
- مستندات قواعد ضريبية: 3-5 قوانين أو أنظمة محددة من مصادر رسمية

**Assumptions الجوهرية**
- نتحكم في database schema ونُصمّمها لتدعم الاستعلامات المستهدفة
- بيانات الفواتير مُهيكَلة بالكامل في جداول DB (vendor، date، total_amount، line_items، tax، due_date، payment_status)
- LLM يتولى Arabic NLP بدون حاجة لـ custom Arabic pipeline
- المستخدم لديه صلاحية الوصول للبيانات التي يسأل عنها

**Limitations (يجب الإفصاح عنها في التقديم)**
- لا real-time integration مع أنظمة ERP خارجية في MVP
- دقة استعلامات SQL المعقدة تعتمد على جودة schema والـ prompt engineering
- التحليل الضريبي استرشادي وليس ملزماً
- أداء اللغة العربية يعتمد على capabilities اللغوية للـ LLM المُختار

---

## ثالثاً: الموديول الثالث — Customer Support / Issue Resolution Agent

### 3.1 هدف الموديول

بناء وكيل دعم عملاء ذكي يستطيع فهم مشكلة العميل، جمع بياناته الكاملة من ERP في ثوانٍ، وتكوين رد دقيق وواضح — مع الحفاظ على نقطة مراجعة بشرية في الحالات الحساسة. النتيجة: تسريع حل المشكلات وتحسين تجربة العميل بشكل قابل للقياس.

### 3.2 Core Use Cases

- استعلام حالة الطلب أو الشحنة بالتفصيل
- الاستفسار عن تفاصيل فاتورة محددة
- الاعتراض على رسوم أو خطأ في الفاتورة
- طلب إرجاع أو استرداد مالي
- الاستفسار عن تاريخ العميل مع الشركة
- الإبلاغ عن مشكلة في منتج أو خدمة

### 3.3 Features: أساسي vs مؤجل

**المجموعة الإلزامية في MVP**

- **Customer Identifier Input:** قبول order_id أو invoice_id أو customer_id كـ entry point
- **ERP Data Fetcher:** جلب بيانات الفاتورة (حقيقية) + الطلب والشحن (mock منظّم)
- **Issue Classifier:** تصنيف نوع المشكلة إلى: status_inquiry، billing_dispute، shipping_issue، refund_request، general_complaint
- **Context Builder:** دمج جميع البيانات في context مُهيكَل ومتماسك يُغذي اللغوي
- **Response Generator:** توليد رد ذكي، واضح، ومناسب للعميل غير التقني
- **Confidence Score:** مؤشر اكتمال البيانات وجودة الرد (High / Medium / Low)
- **Human Review Interface:** واجهة مراجعة كاملة للموظف قبل الإرسال
- **Escalation Path:** مسار إحالة واضح للحالات التي لا يستطيع الـ agent حلها
- **Graceful Degradation:** الرد يبقى مفيداً حتى عند البيانات الناقصة

**مؤجل للمرحلة التالية**

- Real-time shipping API integration (مع شركات شحن فعلية)
- Email / WhatsApp channel integration
- Sentiment analysis للعميل (تحليل مزاجه وأولوية الرد)
- Automated resolution بدون مراجعة بشرية (يحتاج ثقة عالية في النظام)
- CRM integration كاملة
- Customer satisfaction rating بعد الحل
- Chat history persistence بين الجلسات

### 3.4 Agent Workflow التفصيلي

```
Customer Input
(مشكلة + identifier)
       │
       ▼
┌─────────────────────────────────────────────┐
│           Input Parser Node                 │
│  Extract: identifier_type + identifier_value│
│  + issue_description (in natural language)  │
└──────────────────┬──────────────────────────┘
                   │
    ┌──────────────▼──────────────────────┐
    │       Data Fetcher Node             │
    ├─ invoice_data       → REAL from DB  │
    ├─ order_status       → MOCK          │
    ├─ shipping_status    → MOCK          │
    └─ customer_history   → MOCK          │
    └─────────────────────────────────────┘
                   │
    ┌──────────────▼──────────────────────────┐
    │     Data Completeness Check Node        │
    ├─ All data found   → proceed normally    │
    ├─ Partial data     → flag missing fields │
    └─ No data found    → escalate + explain  │
    └─────────────────────────────────────────┘
                   │
    ┌──────────────▼──────────────────────┐
    │      Issue Classifier Node          │
    │  يحدد نوع المشكلة والأولوية         │
    └──────────────┬──────────────────────┘
                   │
    ┌──────────────▼──────────────────────┐
    │       Context Builder Node          │
    │  يُجمّع كل البيانات في سياق متماسك  │
    └──────────────┬──────────────────────┘
                   │
    ┌──────────────▼──────────────────────┐
    │    Response Generator Node (LLM)    │
    │  يُولّد مسودة رد + confidence score  │
    └──────────────┬──────────────────────┘
                   │
    ┌──────────────▼──────────────────────────────────────┐
    │              Human Review Gate                      │
    ├─ Billing dispute / Refund   → Mandatory Review      │
    ├─ Confidence < 70%           → Mandatory Review      │
    ├─ Simple Status Inquiry      → Optional (configurable│
    └─ Agent can auto-send        → Only with explicit OK │
    └─────────────────────────────────────────────────────┘
                   │
                   ▼
        Final Response to Customer
    + Escalation Path (if unresolved)
```

**LangGraph State Schema**
```
{
  customer_identifier: dict,
  issue_description: str,
  issue_type: IssueType,
  fetched_data: dict,
  data_completeness: float,
  confidence_score: float,
  draft_response: str,
  review_required: bool,
  escalation_needed: bool,
  final_response: str
}
```

### 3.5 Handling Missing Data — استراتيجية الـ Graceful Degradation

هذا أحد أهم القرارات التصميمية لأن بياناتنا الحقيقية محدودة في MVP.

**المبدأ:** لا نعرض خطأ تقنياً للعميل. دائماً نعطيه ما لدينا + شرح واضح لما لم يُجَد + مسار بديل.

**أمثلة تطبيقية:**

حالة البيانات الجزئية: "وجدنا فاتورتك رقم INV-890 بتاريخ 15 يناير بإجمالي 3,200 جنيه. بيانات الشحن المرتبطة غير متاحة حالياً في النظام — سيتواصل معك فريق الدعم خلال 24 ساعة لتأكيد حالة التوصيل."

حالة البيانات المعدومة: "لم نعثر على رقم الطلب ORD-999 في نظامنا. يُرجى التأكد من الرقم أو التواصل مع فريق الدعم على [رقم/بريد]."

**Data Confidence Indicator:** كل رد يحمل: 🟢 High (بيانات كاملة) / 🟡 Medium (بيانات جزئية) / 🔴 Low (بيانات محدودة جداً). يظهر للموظف في واجهة المراجعة، لا للعميل مباشرة.

### 3.6 Human-in-the-Loop — تصميم واجهة المراجعة

**متى يكون الـ Human Review إلزامياً؟**
- جميع ردود نزاعات الفواتير
- طلبات الاسترداد أو التعويض
- أي رد يتضمن التزاماً مالياً أو وعداً بموعد
- الحالات التي confidence_score < 0.70

**متى يكون اختيارياً (قابل للتشغيل/الإيقاف)؟**
- استعلامات الحالة البسيطة
- أسئلة المعلومات العامة عن المنتج

**مكونات واجهة المراجعة:**
- Preview كامل للرد المُولَّد قبل الإرسال
- عرض البيانات التي اعتمد عليها الـ agent (Transparency Panel)
- حقل تعديل نصي مباشر على المسودة
- ثلاثة خيارات: "موافق وإرسال" / "رفض وإعادة توليد" / "إحالة لمشرف"
- سجل كامل لكل قرار (Audit Trail)

### 3.7 Demo Scenarios القوية

**Scenario 1 — Order Status Inquiry**
العميل: "أين طلبي رقم ORD-2024-1567؟"
الـ agent يجلب: Order (mock) + Shipping (mock) → يرد: "طلبك في مرحلة الشحن مع شركة X، متوقع التسليم الأربعاء 15 يناير. رقم التتبع: TRK-789456." — Confidence: High → Auto-send available.

**Scenario 2 — Invoice Dispute**
العميل: "الفاتورة رقم INV-890 غلط، أنا ما طلبتش المنتج ده."
الـ agent يجلب الفاتورة الفعلية → يعرض التفاصيل كاملة → يُنشئ رد: "وجدنا الفاتورة تتضمن [تفاصيل]. فريق المبيعات سيتواصل معك خلال 48 ساعة للمراجعة." → Human Review إلزامي.

**Scenario 3 — Graceful Handling for Missing Data**
العميل: "مشكلة في توصيلة رقم DEL-999."
الـ agent: لا يجد هذا الرقم → "لم نتمكن من العثور على هذا الرقم. يُرجى التأكد من رقم الطلب أو التواصل مباشرة مع..." → Escalation مع logging كامل.

**Scenario 4 — Repeat Issue Detection**
العميل: "أنا عميل قديم وعندي مشكلة متكررة في التوصيل."
الـ agent يجلب تاريخ العميل (mock) → يكتشف pattern: "هذه المشكلة تكررت 3 مرات خلال 6 أشهر." → يُصعّد تلقائياً لمدير خدمة العملاء مع ملخص كامل للحالات السابقة.

### 3.8 البيانات المطلوبة والـ Assumptions

**البيانات الحقيقية في MVP**
- Invoice data (من DB الفعلية التي يمتلكها الفريق)
- Customer profiles المرتبطة بالفواتير

**Mock Data المطلوب بناؤها (مرة واحدة بشكل منظّم)**
- جدول order_status: (order_id، status، created_at، estimated_delivery، items)
- جدول shipping: (tracking_id، order_id، status، carrier، location، last_update)
- جدول customer_history: (customer_id، interaction_type، issue_type، resolution، date)

**تنبيه مهم:** Mock data يجب أن يكون متسقاً داخلياً — customer_id في جدول الفواتير يجب أن يُطابق customer_id في جدول التاريخ.

**Limitations**
- الردود تعتمد مباشرة على اكتمال البيانات
- لا channel integration في MVP (الواجهة فقط داخل المنصة)
- لا real-time في MVP — بيانات الشحن static في mock

---

## رابعاً: الموديول الثاني — Purchasing/Inventory/Supplier Agent

### ملاحظة تنفيذية

هذا الموديول **مؤجل**. التصميم هنا موجود بالكامل للاستعداد، لكن لا يُبدأ في تنفيذه إلا بعد اكتمال M1 وM3 واختبارهما، وتبقّى أكثر من 3 أسابيع فعلية قبل التقديم.

### 4.1 هدف الموديول

أتمتة دورة المشتريات من الكشف إلى الطلب: رصد مستويات المخزون، التنبؤ بالنقص، توليد RFQs، وتحليل عروض الموردين — مع توصيات ذكية للتسعير في حالة المخزون البطيء أو المنتهي الصلاحية.

### 4.2 الحد الأدنى القابل للتنفيذ إذا كان الوقت محدوداً

لو تبقّت أسبوعان فقط، نبني ثلاثة عناصر فقط:
- **Inventory Dashboard:** عرض مستويات المخزون مع تنبيهات الحد الأدنى (visual + alert)
- **Low Stock Alert Agent:** يُنبّه عند الاقتراب من reorder point مع تفسير AI لسبب النقص
- **RFQ Draft Generator:** يُولّد مسودة طلب شراء أو رسالة مورد تلقائياً بناءً على المنتج الناقص

### 4.3 المجموعة الكاملة (Full Build إذا توفّر الوقت الكافي)

**Inventory Intelligence Layer**
- مراقبة مستمرة لمستويات المخزون (scheduled polling)
- رصد البضائع البطيئة الحركة (slow-moving inventory) بناءً على معدل الدوران
- رصد البضائع قريبة انتهاء الصلاحية مع تحذير مبكر
- توقع النقص بناءً على معدل الاستهلاك التاريخي

**Procurement Agent**
- توليد RFQ تلقائي للعناصر التي وصلت لـ reorder point
- صياغة رسائل موردين احترافية (قابلة للتعديل قبل الإرسال)
- استقبال عروض الموردين وتحليلها مقارنةً

**Pricing Advisor (اختياري — أقل أولوية)**
- اقتراح خفض سعر مدروس للبضائع البطيئة أو قريبة الانتهاء
- هذا توصية للمدير فقط، وليس dynamic pricing تلقائياً
- Input: product_id، days_in_stock، expiry_date، avg_daily_sales
- Output: "يُوصى بخفض السعر 15% لتصريف المخزون قبل انتهاء الصلاحية في 30 يوماً"

### 4.4 Architecture & Agent Design

```
[Inventory Monitor]
(Scheduled / On-demand Trigger)
       │
       ▼ (stock < reorder_point OR expiry_approaching)
[Alert & Analysis Agent]
│  يشرح سبب التنبيه
│  يقترح الكمية المناسبة للطلب
       │
       ▼
[RFQ Generator Agent]
│  يختار المورد المناسب من السجل التاريخي
│  يُنشئ مسودة RFQ أو رسالة مورد
       │
       ▼
[Human Review & Approval]
│  الموظف يراجع ويعتمد أو يعدّل
       │
       ▼
[Send to Supplier] (manual أو automated بإذن)
       │
       ▼ (عند استلام رد المورد)
[Supplier Offer Analyzer]
   يقارن العروض
   يوصي بالأفضل مع مبرر
```

**LangGraph Flow للموديول الثاني:**
- InventoryCheckNode → AlertGenerationNode → RFQBuilderNode → HumanApprovalNode → (Optional) OfferAnalysisNode → PricingAdvisorNode

**ملاحظة:** هذا الموديول يستخدم نفس LLM Client وnفس Database من البنية المشتركة — لا بنية تحتية جديدة.

---

## خامساً: البنية التقنية الشاملة للنظام

### 5.1 الطبقات الرئيسية

```
┌──────────────────────────────────────────────────────────┐
│                   Frontend Layer                         │
│           React + TypeScript + shadcn/ui                 │
│   ┌──────────────┐  ┌───────────────┐  ┌─────────────┐  │
│   │  M1 Chat UI  │  │  M3 Support   │  │ M2 Inventory│  │
│   │  + Dashboard │  │  Interface    │  │ (Standby)   │  │
│   └──────────────┘  └───────────────┘  └─────────────┘  │
└────────────────────────┬─────────────────────────────────┘
                         │  REST API / WebSocket
┌────────────────────────▼─────────────────────────────────┐
│                   Backend Layer                          │
│                  FastAPI (Python)                        │
│   ┌──────────────┐  ┌───────────────┐  ┌─────────────┐  │
│   │  M1 Router   │  │  M3 Router    │  │  M2 Router  │  │
│   └──────┬───────┘  └───────┬───────┘  └──────┬──────┘  │
│          └──────────────────┼─────────────────┘          │
│                             │                            │
│   ┌─────────────────────────▼──────────────────────────┐ │
│   │           LangGraph Agent Engine                   │ │
│   │    StateGraph | Tool Registry | Shared State       │ │
│   └────────────────────────┬───────────────────────────┘ │
│                            │                             │
│   ┌────────────┐  ┌────────▼────────┐                │
│   │ PostgreSQL │  │  pgvector       │                │
│   │ (ERP Data) │  │ (RAG / Embeds)  │                │
│   └────────────┘  └─────────────────┘                │
└────────────────────────────┬─────────────────────────────┘
                             │
                  ┌──────────▼──────────┐
                  │    LLM Provider     │
                  │  GPT-4o (Primary)   │
                  │  GPT-4o-mini (Fast) │
                  └─────────────────────┘
```

### 5.2 Shared Services المشتركة بين الموديولات

- **Auth Layer:** JWT-based authentication — user context يُمرَّر لكل agent request
- **LLM Client:** Instance واحدة مُهيأة، يُستخدم من جميع الموديولات
- **Database Connection Pool:** SQLAlchemy async pool لـ PostgreSQL
- **Logging & Observability:** كل tool call، LLM call، وuser action يُسجَّل
- **Error Handling Layer:** يُحوّل كل خطأ تقني إلى رسالة مفهومة للمستخدم

---

## سادساً: Tech Stack الموصى به

### Primary Stack (الاختيار الأول)

| Layer | Technology | السبب |
|-------|-----------|-------|
| Frontend | React + TypeScript | مرونة، ecosystem واسع، TypeScript يمنع أخطاء كثيرة |
| UI Components | shadcn/ui | مظهر enterprise احترافي، قابل للتخصيص الكامل |
| Charts | Apache ECharts | أغنى بكثير من Recharts للتصورات المعقدة، دعم عربي |
| Backend | FastAPI (Python) | تكامل مباشر مع LangChain/LangGraph، async support، سريع |
| Agent Orchestration | LangGraph + LangChain | الأنسب للـ stateful agentic flows مع human-in-the-loop |
| Primary Database | PostgreSQL | الأقوى للبيانات العلائقية، دعم JSON، transaction safety |
| Vector Search | pgvector (extension) | حل موحّد: relational + vector في DB واحدة، أبسط deployment |
| LLM — Complex Tasks | GPT-4o | أفضل multilingual + reasoning في الوقت الحالي |
| LLM — Simple Tasks | GPT-4o-mini | أسرع وأرخص للاستعلامات الروتينية |
| Embeddings | text-embedding-3-small | تكلفة منخفضة جداً + جودة ممتازة |
| Auth | FastAPI + python-jose (JWT) | بسيط، كافٍ للـ MVP، يمتد لاحقاً |

### البدائل المحتملة (متى تختارها)

| البديل | متى تختاره بدلاً من الأساسي |
|--------|---------------------------|
| Gemini 1.5 Pro بدل GPT-4o | لو أردت تكلفة أقل قليلاً مع دعم سياق أطول (2M token) |
| Qdrant بدل pgvector | لو احتجت vector search متخصصة بـ scale كبير — غير ضروري في MVP |
| Django REST بدل FastAPI | لو الفريق مُرتاح معه — لكن iteration أبطأ |
| Local Model (Qwen2.5-7B) | للعمل offline في demo — جودة أقل خاصة بالعربية |
| Recharts بدل ECharts | لو الـ charts بسيطة ومحدودة — أسهل في التكامل مع React |

### LLM Strategy المقترحة للمشروع

**Hybrid Approach بناءً على التعقيد:**
- **GPT-4o:** التحليل العميق، توليد Narrative، Tax Reasoning، الأسئلة المركّبة
- **GPT-4o-mini:** تصنيف النية، استعلامات الحالة البسيطة، ردود Customer Support الاعتيادية
- **Local Model (future):** Qwen2.5 للاستعلامات الروتينية المتكررة لتخفيض التكلفة

**للـ Demo:** GPT-4o API مباشرة — لا حاجة لـ Azure في MVP. Azure مفيد لاحقاً للـ enterprise deployment.

---

## سابعاً: MVP النهائي — ما يجب أن يكون جاهزاً قبل التقديم

### Module 1 — AI ERP Intelligence Agent

- Chat interface ثنائي اللغة مع history واضح
- 5 أنواع استعلامات مدعومة: financial، operational، invoice، tax، executive_summary
- Invoice DB query + analysis + batch pattern detection (لا file upload، لا OCR)
- Tax RAG مع 3-5 قواعد ضريبية محددة ومحملة
- Output formats: table + basic chart + narrative text + alert card
- LangGraph orchestration مع 4 tool nodes رئيسية
- Mock ERP database مُصمَّمة بواقعية عالية (ليست عشوائية)

### Module 3 — Customer Support Agent

- Customer input interface: identifier + issue description
- Invoice data lookup من DB الفعلية
- Mock order/shipping/history data integration متسقة ومنظّمة
- Response generation مع confidence indicator واضح
- Human review interface كاملة (preview + edit + approve/reject/escalate)
- Graceful degradation عند البيانات الناقصة
- Escalation path واضح ومُصمَّم

### Module 2 — غير مطلوب في MVP

التصميم كامل، التنفيذ مشروط بتوفر الوقت.

---

## ثامناً: استراتيجية التقديم أمام الشركات

### كيف تُقدّم المشروع

لا تُقدّمه كـ "chatbot للـ ERP". قدّمه كـ **Agentic Intelligence Layer** — طبقة ذكاء تعمل فوق بيانات ERP الموجودة دون الحاجة لاستبدال النظام الحالي أو تغيير أي شيء في البنية القائمة.

**نقاط القوة الجاهزة للعرض:**
- يعمل على بيانات الشركة الفعلية — لا migration، لا إعادة هيكلة
- يدعم العربية بشكل طبيعي — لا مفاتيح ترجمة أو تحريف لغوي
- Human-in-the-loop: القرار يبقى بيد الإنسان دائماً
- كل موديول مستقل: يمكن تشغيل M1 وحده أو M3 وحده حسب احتياج الشركة
- ROI قابل للقياس: M1 يختصر ساعات تحليل يدوي، M3 يخفض وقت معالجة تذاكر الدعم

**تحذيرات يجب تجنبها في التقديم:**
- لا تعد بـ real-time integration مع أنظمة ERP خارجية في المرحلة الأولى
- لا تقل "يتكامل مع أي ERP" — قل "مُصمَّم للتكامل مع قواعد البيانات القياسية وقابل للتخصيص"
- لا تقدّم الحساب الضريبي كنظام مُعتمَد قانونياً
- أظهر الـ limitations بشفافية — هذا يزيد المصداقية أمام الشركات

### الـ Demo الأمثل (ترتيب العرض المقترح)

- يبدأ بـ M1: سؤال بالعربية عن أداء المبيعات → النتيجة تظهر في ثوانٍ كـ chart + narrative
- ثم Invoice batch analysis: استعلام عن فواتير آخر 3 أشهر → ملخص + اكتشاف pattern "المورد X رفع أسعاره 12%"
- ثم M3: عميل يسأل عن طلب → الـ agent يُحضر البيانات → Human review → إرسال
- يُختتم بـ anomaly detection: النظام يُنبّه من تلقاء نفسه على مصروف غير معتاد

هذا الترتيب يُظهر ثلاثة قدرات مختلفة تماماً في 10 دقائق — كافٍ لإقناع أي صانع قرار.

---

*وثيقة حيّة — تُحدَّث مع تطور القرارات التقنية والتصميمية*

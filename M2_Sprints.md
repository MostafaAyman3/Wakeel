# M2 — Sprint Plan: Purchasing & Inventory Agent

> **ملاحظة:** تم إعداد هذه الخطة المعمارية بواسطة (مهندس المعمارية / Planner)، وتم تقسيم مهام التنفيذ (Sprints) ليتم العمل عليها بشكل متوازي بواسطة مطورين اثنين (Developer A & Developer B).

---

## Sprint 0 — Architecture & Planning (بواسطة الـ Architect)
**المدة:** 3 أيام

**المهام:**
- إعداد البنية المعمارية (Architecture) الخاصة بـ M2 بناءً على وثيقة البلوبرنت.
- تصميم حالة الوكيل الذكي (LangGraph State Schema) وتحديد مهام الـ Nodes.
- تصميم آلية دمج أدوات (n8n) لأتمتة سير العمل.
- تصميم تجربة التفاعل الصوتي (Speech-to-Speech) وتحديد الـ Prompts المطلوبة للهجة المصرية العامية واللغة الإنجليزية.
- إنشاء الـ `implementation_plan.md` التفصيلي ليكون مرجعاً للمطورين.

**المخرج:** خطة واضحة ومسار هندسي جاهز للتنفيذ.

---

## Sprint 1 — Backend & Inventory Check (بواسطة Developer A)
**المدة:** 4 أيام

**المهام:**
- إنشاء `agents/m2/schemas/m2_state.py` لتعريف حالة الوكيل.
- برمجة `inventory_tools.py` للاتصال بـ PostgreSQL وقراءة أرصدة المخزون وتحديد المنتجات التي وصلت لـ (Reorder Point).
- برمجة `inventory_check_node.py` كأول خطوة في مسار الذكاء الاصطناعي.
- إنشاء المسار `GET /api/v1/m2/inventory` لإرجاع بيانات المخزون الحالية.

**المخرج:** Endpoint قادرة على إرجاع حالة المخزون واكتشاف النواقص من قاعدة البيانات.

---

## Sprint 2 — LLM Nodes: Alerts & RFQs (بواسطة Developer B)
**المدة:** 5 أيام

**المهام:**
- برمجة `alert_generation_node.py` لتحليل النواقص وتوليد توصيات استباقية.
- هندسة الـ Prompts في `rfq_builder_node.py` بحيث يقوم الوكيل بكتابة مسودة إيميل رسمية للمورد، مع مراعاة لغة المستخدم (مصرية عامية أو إنجليزية).
- ربط الـ Nodes معاً لإنشاء `agents/m2/graphs/m2_graph.py`.
- إنشاء المسار `POST /api/v1/m2/analyze` لتشغيل مسار الذكاء الاصطناعي وإرجاع التنبيهات ومسودات طلبات الشراء.

**المخرج:** وكيل M2 كامل يعمل في الخلفية (Backend) وقادر على توليد التنبيهات والطلبات الذكية.

---

## Sprint 3 — Frontend Dashboard (عمل مشترك: Dev A & Dev B)
**المدة:** 5 أيام

**المهام:**
- **Dev A:** تصميم وبناء الصفحة الرئيسية `frontend/app/m2/page.tsx` ومكوّن `InventoryTable.tsx` وعرض حالات المخزون بالألوان (مخزون منخفض / آمن).
- **Dev B:** تصميم وبناء مكوّن `AlertsPanel.tsx` لعرض تنبيهات الذكاء الاصطناعي، ومكوّن `RFQDraftView.tsx` لعرض مسودات طلبات الشراء مع زر "Approve & Send".
- دمج المكونات وربطها مع الـ API Endpoints التي تم بناؤها في Sprints 1 & 2.

**المخرج:** لوحة تحكم M2 مرئية ومتكاملة تعرض الأرصدة والتنبيهات.

---

## Sprint 4 — Speech-to-Speech Integration (بواسطة Developer A)
**المدة:** 4 أيام

**المهام:**
- برمجة مكوّن `VoiceAssistantPanel.tsx` في الواجهة الأمامية.
- دمج خدمة تحويل الصوت لنص (Speech-to-Text) لالتقاط سؤال مدير المشتريات (مثل: "إيه المنتجات اللي ناقصة في المخزن؟").
- إرسال النص للـ Backend لتشغيل M2 Agent.
- دمج خدمة تحويل النص لصوت (Text-to-Speech باستخدام OpenAI Audio API أو ElevenLabs) لنطق الرد باللهجة المصرية العامية أو الإنجليزية بشكل طبيعي.

**المخرج:** مساعد مخزون تفاعلي يعمل بالأوامر الصوتية والردود الصوتية.

---

## Sprint 5 — n8n Automation & Webhooks (بواسطة Developer B)
**المدة:** 4 أيام

**المهام:**
- إنشاء مسارات (Webhooks) في الـ Backend أو مباشرة من الـ Frontend لاستقبال أمر "إرسال طلب الشراء".
- تصميم Workflow 1 في n8n: الجدولة اليومية (Cron) لفحص المخزون كل صباح وإرسال رسالة WhatsApp أو Email للمدير بالتنبيهات.
- تصميم Workflow 2 في n8n: استلام الـ Webhook الخاص بطلب الشراء (RFQ) المعتمد، واستخدام (Email Node) لإرساله تلقائياً للمورد الحقيقي.

**المخرج:** نظام مخزون يعمل بشكل آلي بالكامل لخدمة المشتريات دون تدخل يدوي إضافي.

---

## ملخص الجدول الزمني لموديول M2

| Sprint | المحتوى | المسؤول | المدة |
|--------|---------|---------|-------|
| 0 | Architecture & Planning | Architect | 3 أيام |
| 1 | Backend & Inventory Check | Developer A | 4 أيام |
| 2 | LLM Nodes: Alerts & RFQs | Developer B | 5 أيام |
| 3 | Frontend Dashboard | Dev A & Dev B | 5 أيام |
| 4 | Speech-to-Speech Integration | Developer A | 4 أيام |
| 5 | n8n Automation & Webhooks | Developer B | 4 أيام |
| **المجموع** | | | **~25 يوم** |

> **توزيع متوازي:** يمكن العمل على Sprint 1 و Sprint 2 بشكل متوازي، وكذلك Sprint 4 و Sprint 5، مما يقلل الوقت الفعلي للمشروع (Time-to-Market) بحوالي 40%.

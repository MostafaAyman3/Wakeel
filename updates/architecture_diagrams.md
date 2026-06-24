# تطور البنية المعمارية (Architecture Evolution)

فيما يلي رسم توضيحي بيقارن بين البنية القديمة (Legacy) والبنية الجديدة (Stratified) للنظام.

## 1. البنية القديمة (Legacy Architecture)
كانت البنية القديمة بسيطة وتعتمد على تصنيف النية (Intent) بشكل مباشر لتوجيه السؤال، وكانت تفتقر للذاكرة التحليلية المتقدمة.

```mermaid
graph TD
    %% Styling
    classDef startEnd fill:#1E293B,stroke:#94A3B8,stroke-width:2px,color:#F8FAFC,shape:round
    classDef router fill:#B45309,stroke:#F59E0B,stroke-width:2px,color:#F8FAFC
    classDef tool fill:#334155,stroke:#64748B,stroke-width:1px,color:#F8FAFC
    classDef generator fill:#0D9488,stroke:#14B8A6,stroke-width:2px,color:#F8FAFC

    START((START)):::startEnd
    END_NODE((END)):::startEnd

    IntentClassifier{Intent Classifier}:::router
    Clarification[Clarification Node]:::tool
    DBQuery[DB Query Tool]:::tool
    InvoiceAnalysis[Invoice Analysis Tool]:::tool
    TaxRAG[Tax RAG Node]:::tool
    Validation[Validation & Enrichment]:::tool
    OutputSelector[Output Selector]:::tool
    Narrative[Narrative Generator]:::generator

    START --> IntentClassifier
    IntentClassifier -->|Missing Info| Clarification
    IntentClassifier -->|SQL Template| DBQuery
    IntentClassifier -->|Invoice Request| InvoiceAnalysis
    IntentClassifier -->|Tax Rule| TaxRAG

    Clarification --> END_NODE
    
    DBQuery --> Validation
    InvoiceAnalysis --> Validation
    TaxRAG --> Validation
    
    Validation --> OutputSelector
    OutputSelector --> Narrative
    Narrative --> END_NODE
```

---

## 2. البنية الجديدة المتقدمة (New Stratified Architecture)
البنية الحالية تعمل بمسارات طبقية (Tiers) وتحتوي على ذاكرة للسياق، مقيّم للنتائج، وقدرة على إنشاء أوامر SQL بشكل ديناميكي (NL2SQL) مع تصحيحها ذاتياً.

```mermaid
graph TD
    %% Styling
    classDef startEnd fill:#1E293B,stroke:#94A3B8,stroke-width:2px,color:#F8FAFC,shape:round
    classDef router fill:#B45309,stroke:#F59E0B,stroke-width:2px,color:#F8FAFC
    classDef context fill:#0284C7,stroke:#38BDF8,stroke-width:2px,color:#F8FAFC
    classDef tool fill:#334155,stroke:#64748B,stroke-width:1px,color:#F8FAFC
    classDef t3 fill:#7E22CE,stroke:#A855F7,stroke-width:2px,color:#F8FAFC
    classDef generator fill:#0D9488,stroke:#14B8A6,stroke-width:2px,color:#F8FAFC
    classDef evaluator fill:#C2410C,stroke:#FB923C,stroke-width:2px,color:#F8FAFC

    START((START)):::startEnd
    END_NODE((END)):::startEnd

    ContextLoader[Context Loader]:::context
    IntentRouter{Intent Router}:::router
    
    %% Tiers
    T0[T0: Conversation]:::tool
    T1{T1: Dispatcher}:::router
    T1_DB[T1: DB Query]:::tool
    T1_Inv[T1: Invoice Analysis]:::tool
    T1_Tax[T1: Tax RAG]:::tool
    
    T2[T2: Follow-up Resolver]:::tool
    
    T3_Plan[T3: Analytical Planner]:::t3
    T3_Exec[T3: SQL Executor & Repair]:::t3
    T3_Agg[T3: Aggregator]:::t3
    
    T4[T4: Clarification]:::tool
    T5[T5: Out of Scope]:::tool
    T6[T6: Delegate to M3]:::tool

    %% Shared Flow
    Evaluator[Result Evaluator]:::evaluator
    Validation[Validation & Enrichment]:::tool
    OutputSelector[Output Selector]:::tool
    Narrative[Narrative Generator]:::generator
    ContextSaver[Context Saver]:::context

    %% Routing
    START --> ContextLoader
    ContextLoader --> IntentRouter
    
    IntentRouter -->|General Chat| T0
    IntentRouter -->|Known Templates| T1
    IntentRouter -->|Contextual Question| T2
    IntentRouter -->|Complex Analysis| T3_Plan
    IntentRouter -->|Missing Info| T4
    IntentRouter -->|Irrelevant| T5
    IntentRouter -->|Customer Support| T6

    %% T1 Flow
    T1 -->|Database| T1_DB
    T1 -->|Invoice| T1_Inv
    T1 -->|Tax| T1_Tax

    %% T2 Flow
    T2 -->|Explain Previous| OutputSelector
    T2 -->|Needs New Data| T3_Plan

    %% T3 Flow (NL2SQL)
    T3_Plan --> T3_Exec
    T3_Exec --> T3_Agg

    %% Evaluation
    T1_DB --> Evaluator
    T1_Inv --> Evaluator
    T1_Tax --> Evaluator
    T3_Agg --> Evaluator

    Evaluator -->|Valid Data| Validation
    Validation --> OutputSelector
    OutputSelector --> Narrative

    %% Context Saving
    T0 --> ContextSaver
    T4 --> ContextSaver
    T5 --> ContextSaver
    T6 --> ContextSaver
    Narrative --> ContextSaver

    ContextSaver --> END_NODE
```

### أبرز الفروق الجوهرية اللي هتلاحظها في الرسمتين:
1. **الذاكرة (Context Loader & Saver):** في البنية الجديدة، الدورة بتبدأ بتحميل السياق من الداتا بيز وبتنتهي بحفظ الإطار التحليلي الجديد، عشان النظام يفتكر انتوا كنتوا بتتكلموا في إيه.
2. **المسارات (Tiers):** بدل ما كل الأسئلة تروح على نفس الأداة، بقى فيه مسارات متخصصة (زي T3 للتحليل المعقد، و T6 لتحويل أسئلة الدعم الفني).
3. **مقيّم النتائج (Result Evaluator):** خطوة أمان جديدة في النص بتقيّم الداتا اللي طالعة من الـ Database قبل ما توصل لمرحلة توليد النص، عشان تتأكد إن الإجابة مدعومة بأرقام حقيقية.

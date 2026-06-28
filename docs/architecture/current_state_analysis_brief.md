# Wakeel / ERP Agentic AI — Current State, Problems, and Analysis Prompt

> **Purpose of this document**
>
> This document is meant to be handed to another model as a **deep project understanding brief**.
> It explains:
> 1. what the project is doing now,
> 2. how the current system is working,
> 3. what problems we are trying to solve,
> 4. what scenarios must be handled,
> 5. what still needs to change or be strengthened,
> 6. and the exact prompt that should be given to the model to analyze the system deeply and propose the best solution.
>
> This file intentionally does **not** lock the project into a final architecture decision.  
> Its job is to describe the current state and the decision space clearly, so a model can reason about the best next step.

---

## 1) Project Summary

The project is an **ERP Agentic AI layer** that sits on top of business data and behaves like a human analyst / assistant.

The user should be able to talk to it naturally in Arabic or English, for example:

- casual conversation and greetings,
- direct business questions,
- follow-up questions on the same analysis,
- deeper analytical questions,
- support / case-related questions,
- clarification requests,
- and out-of-scope questions.

The intended experience is not “a fixed query bot” only.  
It should feel like the user is speaking to a real analyst who can:
- understand intent,
- ask for clarification if the question is unclear,
- query the database safely,
- combine multiple data sources when needed,
- analyze the results,
- explain what the numbers mean,
- and choose the right presentation format.

---

## 2) What the Project Is Trying to Solve

The core problem is that real ERP usage is not only about exact questions like:

- “What was the total revenue in Q2?”
- “Show top 5 products.”
- “Which customers are overdue?”

Real users also ask:

- “صباح الفل، عامل إيه؟”
- “إنت بتعرف تعمل إيه؟”
- “ليه الأرباح زادت في الفترة دي؟”
- “إيه الأسباب اللي خلت النتيجة دي تحصل؟”
- “اعمللي تحليل أعمق.”
- “هل في مشكلة في المصاريف؟”
- “وريني اللي ورا الكلام ده.”
- “طيب بعد التحليل ده، تنصح بإيه؟”

So the system must solve **two different kinds of work**:

1. **Direct business retrieval**
   - structured questions
   - predictable queries
   - safe database access
   - deterministic outputs

2. **Analytical reasoning**
   - follow-up analysis
   - root-cause reasoning
   - multi-step comparison
   - combining several results
   - explanation and recommendations

It also needs to handle:
- ambiguity,
- missing data,
- incomplete questions,
- support-style requests,
- and irrelevant/out-of-domain questions.

---

## 3) Current Working Style of the System

Based on the project notes and the current file set, the system is already being treated as a **business intelligence assistant** rather than a simple chatbot.

The current thinking is:

### A. The user can start with casual talk
Example:
- “صباح الفل”
- “عامل إيه”
- “إنت مين؟”
- “بتعمل إيه؟”

The assistant should respond naturally and explain that it is a data / ERP analysis assistant.

### B. The user can then ask a direct question
Example:
- “كام أرباحنا في الفترة الفلانية؟”
- “إيه إجمالي المبيعات في الربع الثاني؟”
- “أكتر 5 منتجات مبيعًا؟”

The assistant should answer from the database.

### C. The user can continue with follow-up analysis
Example:
- “ليه كده؟”
- “إيه الأسباب؟”
- “اعمل breakdown”
- “فهمني أكتر”
- “وريني تفاصيل الفئة دي”

The assistant should use the previous answer and the same context to continue the analysis.

### D. The user can ask multi-step analysis from the beginning
Example:
- “حلللي الأرباح ووريني الأسباب.”
- “قارن بين فترتين وفسر ليه الفرق ده حصل.”
- “اديني تحليل للموردين مع اكتشاف الشذوذات.”
- “اعمل summary تنفيذي مع توصيات.”

These questions may require:
- more than one database query,
- one or more tools,
- aggregation of outputs,
- and a reasoning step after retrieval.

---

## 4) Current System Behavior Being Targeted

The desired behavior is that the assistant should not behave like a rigid template engine only.

It should instead act like a real analyst that can:

- speak naturally,
- understand the user’s level of specificity,
- pick the right path,
- ask for clarification if needed,
- fetch facts from ERP data,
- combine multiple outputs,
- judge whether the returned data is enough,
- decide whether more querying is required,
- explain the result in simple language,
- and choose the best final format.

This means the model is expected to do more than “just answer.”

It should:
- interpret,
- plan,
- inspect outputs,
- validate sufficiency,
- then decide whether to stop or continue.

---

## 5) The Current Working Assumptions We Are Using

These are the assumptions behind the current project direction:

### 5.1 Most business questions are repetitive
A large percentage of real ERP questions belong to recurring patterns such as:
- revenue,
- top products,
- aging,
- VAT,
- vendor analysis,
- customer support,
- operational counts,
- trends,
- and anomaly detection.

### 5.2 Some questions are covered by known templates
The system already expects that many common questions can be handled by predefined templates rather than unrestricted SQL generation.

### 5.3 Some questions are not covered by templates
Some user requests will not match any known template, or will require extra reasoning or a different query pattern.

### 5.4 The answer should be judged after data retrieval
It is not enough to just fetch data.  
The system should inspect the returned result and decide:
- is this enough,
- does it fully answer the question,
- or is more work needed?

### 5.5 The system must remain safe
The database interaction must remain read-only.  
Destructive or write operations are not allowed.

### 5.6 The system must remain explainable
Because this is an ERP-facing assistant, it needs traceability and predictable behavior.  
The logic should be inspectable, testable, and debuggable.

---

## 6) Current Problems We Are Trying to Solve

### Problem 1: The user may ask casual conversational openings
The system should not feel robotic when the user says:
- “صباح الفل”
- “عامل إيه؟”

It must understand that this is not a database query, but a conversational start.

### Problem 2: The user may ask a known business question
For example:
- revenue,
- aging,
- VAT,
- top N,
- product performance,
- vendor performance,
- customer support status.

The system should use the correct template and should not overcomplicate this with unnecessary reasoning.

### Problem 3: The user may ask a follow-up on the previous analysis
Example:
- “ليه الأرباح زادت؟”
- “فهمني أكتر.”
- “ما السبب؟”
- “اعمل تفصيل للفئة دي.”

The system must preserve context and continue the same analytical thread.

### Problem 4: The user may ask a multi-source analysis
Some questions need:
- more than one database query,
- multiple tools,
- aggregation of several outputs,
- and then a final analysis step.

### Problem 5: The system may return incomplete data
Sometimes a template result alone is not enough.  
The model must determine whether:
- the answer is complete,
- the template satisfied the user,
- or another query is needed.

### Problem 6: The user may ask an ambiguous question
Example:
- “وريني الأرقام”
- “اعمللي تحليل”
- “قارن”
- “وريني اللي حصل”

The system should not guess too aggressively.  
It must know when to ask for clarification.

### Problem 7: The user may ask something outside the project scope
Example:
- sports,
- entertainment,
- random unrelated requests.

The system should detect that this is out of domain and respond accordingly.

### Problem 8: The model may need to decide between stopping and continuing
The system should not always stop after the first result.  
It may need to:
- accept a result and answer,
- or continue by generating another query,
- or switch into deeper reasoning.

### Problem 9: The answer format must match the data
For example:
- one key number may need a metric card,
- comparison may need a chart,
- top N may need a table,
- anomaly may need an alert,
- explanation may need narrative.

### Problem 10: The system must handle support-oriented flows
Some questions are not pure analytics.  
They may involve:
- customer status,
- invoice dispute,
- shipping issue,
- missing identifier,
- repeated issue,
- or human review / escalation.

---

## 7) Scenarios We Must Explicitly Support

Below is the set of scenarios we want the model to reason about in detail.

### 7.1 Greeting / small talk
Examples:
- “صباح الفل”
- “عامل إيه”
- “إنت مين”
- “بتعمل إيه”

Expected handling:
- conversational response,
- explain the assistant’s role,
- no database query needed.

### 7.2 Direct known business query
Examples:
- revenue in a time period,
- product/category performance,
- customer aging buckets,
- VAT totals,
- top N customers/products,
- vendor analysis,
- anomaly detection,
- operational counts.

Expected handling:
- use known template if available,
- execute safe data retrieval,
- inspect result sufficiency,
- then answer.

### 7.3 Follow-up question on the previous analysis
Examples:
- “ليه كده؟”
- “ما الأسباب؟”
- “وريني التفاصيل”
- “احلل أكثر”
- “اعمل breakdown”
- “فهمني النتيجة”

Expected handling:
- preserve context,
- use previous results,
- decide whether to query more data,
- and then reason over it.

### 7.4 Multi-step analysis from the beginning
Examples:
- “حلل الأرباح وفسرها”
- “قارن بين فترتين ووضح السبب”
- “اعمل summary تنفيذي”
- “افحص الموردين واكتشف الشذوذ”
- “وريني العلاقات بين المبيعات والمخزون”

Expected handling:
- planning,
- multiple queries or tools,
- aggregation,
- reasoning,
- final explanation.

### 7.5 Ambiguous question
Examples:
- “وريني الأرقام”
- “اعمل تحليل”
- “قارن”
- “وريني اللي حصل”

Expected handling:
- ask for clarification,
- do not assume a specific meaning too early.

### 7.6 Out-of-scope question
Examples:
- sports,
- movies,
- unrelated general knowledge.

Expected handling:
- polite out-of-domain reply,
- explain the assistant’s scope,
- optionally redirect to supported ERP/business topics.

### 7.7 Missing or incomplete data
Examples:
- wrong identifier,
- missing invoice,
- missing order,
- missing support record.

Expected handling:
- explain that data is missing,
- ask for the correct identifier or more detail,
- avoid hallucination.

### 7.8 Question requiring more than one data source
Examples:
- revenue plus expenses,
- inventory plus orders,
- vendor cost plus invoice history,
- customer support history plus current case.

Expected handling:
- multi-tool planning,
- collect outputs in structured form,
- combine results into final reasoning.

### 7.9 Query result must be judged before final answer
Examples:
- template returns partial data,
- query result is too small,
- query result doesn’t fully cover the requested period,
- the result doesn’t prove the asked conclusion.

Expected handling:
- evaluate sufficiency,
- decide whether to answer or run more work.

### 7.10 Support / human review scenarios
Examples:
- shipping issue,
- billing dispute,
- refund request,
- repeated complaint,
- missing support data.

Expected handling:
- classification,
- confidence handling,
- possible escalation or review,
- preserve support history context.

---

## 8) Important Behavioral Requirements

The system should behave as if it is a real analyst.

That means the model should be able to:

- speak naturally,
- keep context,
- understand when a question is enough to answer,
- know when it is not enough,
- know when to ask for clarification,
- know when to query again,
- know when to continue reasoning,
- know when the topic is outside scope,
- know when to summarize,
- know when to present a chart versus a table versus narrative,
- and know when the returned data is incomplete.

The goal is not only correctness.  
The goal is **useful analyst behavior**.

---

## 9) Current Gaps / Things That Need to Be Strengthened

These are the kinds of things the next model should examine deeply:

### 9.1 Insufficient post-query judgment
After data is returned, the model may need a dedicated decision step to determine whether the answer is enough.

### 9.2 Weak handling of follow-ups
The system must be able to continue a thread intelligently after the first answer.

### 9.3 Template coverage boundaries
We need to know which questions are well covered by templates and which ones fall outside template coverage.

### 9.4 Safe fallback for unknown questions
For questions that do not fit a template, there must be a safe path.

### 9.5 Multi-tool orchestration
Some scenarios require several tools or repeated queries.

### 9.6 Better distinction between:
- direct retrieval,
- analytic reasoning,
- clarification,
- and out-of-scope handling.

### 9.7 Need to decide what kind of reasoning mechanism is best
The model should analyze whether:
- the current approach is enough,
- a ReAct-style reasoning loop is necessary,
- a different reasoning pattern is better,
- or a hybrid of methods is needed.

### 9.8 Need to understand the role of NL2SQL
The model should assess whether unrestricted or semi-restricted SQL generation should be used for edge cases and how it should be validated.

---

## 10) What We Want the Next Model to Analyze

We do **not** want the next model to just summarize the project.

We want it to deeply analyze:
- the current working style,
- the system’s strengths,
- the system’s weaknesses,
- the edge cases,
- the role of templates,
- the role of reasoning,
- the role of SQL generation,
- the role of post-query judgment,
- the handling of conversational mode,
- the handling of clarification,
- the handling of out-of-scope inputs,
- and the handling of multi-step analysis.

We want it to determine:
- what is enough as-is,
- what is missing,
- what should be changed,
- and what solution is the most appropriate.

---

## 11) What the Next Model Should Not Do

The next model should not:
- jump to a shallow architecture decision,
- ignore the conversational use case,
- ignore follow-up analysis,
- ignore post-result validation,
- treat everything as a simple template lookup,
- or assume that one reasoning style fits all questions.

It must analyze the project as a realistic ERP analytical copilot.

---

## 12) Analysis Prompt for the Next Model

Use the following prompt with the next model.

---

### Prompt to the Next Model

You are analyzing an ERP Agentic AI project that behaves like a real data analyst assistant.

Your task is to deeply analyze the current system behavior, the problems we are trying to solve, and the scenarios we must support.

Do **not** give a shallow summary.  
Do **not** assume a final architecture too early.  
Do **not** focus on one mechanism only.

You must read the project description carefully and reason about it in depth.

#### What you must analyze
1. How the current system is working conceptually.
2. The kinds of user inputs it must handle, including:
   - greetings and casual conversation,
   - direct business questions,
   - follow-up questions,
   - multi-step analytical questions,
   - ambiguous questions,
   - out-of-scope questions,
   - missing-data cases,
   - and support-oriented cases.
3. Whether the current approach is enough for each scenario.
4. Where template-based handling is sufficient.
5. Where more flexible query generation is needed.
6. Where a reasoning loop is needed.
7. Whether a ReAct-style mechanism is useful, and if so, where.
8. Whether a different reasoning style is better.
9. Whether a hybrid strategy is needed, and why.
10. How the model should decide after receiving query results:
    - answer immediately,
    - ask clarification,
    - issue another query,
    - or enter deeper reasoning.
11. What must be improved so the system feels like a real analyst, not a rigid bot.
12. What safety, traceability, and reliability issues must be respected.

#### Important constraints
- The database must stay read-only.
- The system must remain safe and controlled.
- The assistant should be able to continue a conversation naturally.
- The assistant should be able to inspect whether returned data is sufficient before answering.
- The assistant should be able to decide whether more querying is required.
- The assistant should be able to distinguish between:
  - direct retrieval,
  - deeper analysis,
  - clarification,
  - and out-of-scope requests.

#### What your output must include
- A deep explanation of the project behavior.
- A breakdown of all important scenarios.
- A list of current problems and gaps.
- A discussion of what kind of reasoning is needed.
- A discussion of whether ReAct is appropriate or not.
- A discussion of whether a hybrid approach is better.
- A clear recommendation for the best solution after analyzing the tradeoffs.
- A detailed explanation of why that recommendation is best for this project.

#### How to think about it
You must think carefully and use the maximum depth of reasoning available.  
You should compare options honestly and explain the tradeoffs.

You should explicitly answer:
- Is the current approach enough?
- Where does it fail?
- Is ReAct the right default?
- Should the system mix ReAct with another approach?
- Or is another solution better?

Your analysis should be detailed, practical, and grounded in the project’s actual behavior.

---

## 13) Final Goal of This Brief

This brief is meant to let another model fully understand:
- what the project is,
- how it currently behaves,
- what cases it must handle,
- what pain points exist,
- and what analysis we expect from it.

The expected result from the next model is not a generic answer.  
It is a deep, practical, project-specific technical analysis.

---

## 14) Suggested Use

Use this document as the input file for the next model when you want it to:
- understand the current project behavior,
- evaluate the current logic,
- assess weak points,
- and propose the best solution after deep analysis.

The model should read this file before making any architecture or reasoning recommendation.

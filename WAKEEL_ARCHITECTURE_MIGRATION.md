# Wakeel Architecture Migration Plan
## From ERP Chatbot to Context-Aware Data Analyst Copilot

**Status:** Approved for implementation planning  
**Architecture:** Option C — Hybrid Stratified Routing with Bounded Analytical Execution  
**Last updated:** 2026-06-22  
**Primary scope:** M1 Intelligence Agent  
**Support boundary:** M1 delegates support requests to M3; M1 does not implement support logic.

---

## 1. Objective

Wakeel must behave as a business data analyst, not as a chatbot that only maps questions to ERP queries.

The target system must:

- Understand Arabic, Egyptian Arabic, and English business questions.
- Preserve analytical context across conversation turns.
- Distinguish simple retrieval from follow-up reasoning and multi-step analysis.
- Prefer existing SQL templates, while supporting validated NL2SQL for uncovered questions.
- Inspect query results before answering and decide whether the returned data actually answers the question.
- Repair invalid SQL through a bounded feedback loop.
- Explain findings, comparisons, anomalies, assumptions, and data gaps naturally.
- Remain read-only and enforce strict schema and SQL policies.
- Keep M1 focused on analytics and delegate customer support to M3.

This document supersedes generic file and node assumptions from earlier migration drafts. All paths and migration steps below match the current repository.

---

## 2. Confirmed Architecture Decisions

| Decision | Approved approach |
|---|---|
| Main architecture | Option C: stratified routing with bounded analytical execution |
| M1 responsibility | Business analytics, data retrieval, comparison, explanation, tax RAG |
| T6 responsibility | Delegation to M3 only |
| Conversation persistence | Reuse `conversations.metadata`; no new migration in V1 |
| Query strategy | Existing templates first, validated NL2SQL second |
| NL2SQL correction | Bounded generate → validate → execute → evaluate → repair loop |
| M1 table whitelist | `customers`, `inventory`, `invoice_items`, `invoices`, `order_items`, `orders`, `payments`, `products`, `transactions`, `vendors` |
| M3-only tables | `shipments`, `customer_interactions` |
| Database protection | Read-only DB role plus AST/schema validation |
| Existing test bank | Extend and automate `ERP_Test_Questions.md`; do not create another question-bank document |
| Existing frontend/API | Preserve the current response contract where possible |

---

## 3. Current Baseline

The repository already contains valuable production foundations that must be reused:

- `agents/m1/schemas/m1_state.py`: current `M1State`, `IntentType`, and `OutputType`.
- `agents/m1/graphs/m1_graph.py`: current LangGraph entry and routing.
- `agents/m1/nodes/intent_classifier_node.py`: bilingual intent classification and basic history use.
- `agents/m1/tools/db_query_tool.py`: 10 SQL templates and comparison execution.
- `agents/m1/nodes/invoice_analysis_tool_node.py`: invoice analysis templates and narrative analysis.
- `agents/m1/nodes/tax_rag_node.py`: tax retrieval path.
- `agents/m1/nodes/validation_enrichment_node.py`: confidence and anomaly checks.
- `agents/m1/nodes/output_selector_node.py`: adaptive output selection.
- `agents/m1/nodes/narrative_generator_node.py`: bilingual response generation.
- `backend/services/conversation_service.py`: conversation persistence.
- `backend/core/database.py`: separate read-only engine for M1.
- `ERP_Test_Questions.md`: single-turn, conversational, M1, and M3 scenarios.

The migration is evolutionary. Existing templates, Tax RAG, invoice analysis, output rendering, frontend contracts, JWT context, LangSmith tracing, and the read-only database user must not be discarded.

---

## 4. Target Routing Model

Every request receives two independent classifications:

1. `domain_intent`: what business subject the user is asking about.
2. `assigned_tier`: how the request should be executed.

This separation prevents analytical complexity from being confused with business intent.

### 4.1 Domain intents

Initial domain intents:

- `financial`
- `sales`
- `collections`
- `inventory`
- `orders`
- `invoice`
- `tax`
- `support`
- `conversation`
- `out_of_scope`
- `ambiguous`

These may map internally to the existing intent values during migration to preserve compatibility.

### 4.2 Execution tiers

| Tier | Name | Purpose |
|---|---|---|
| T0 | Conversational | Greeting, identity, capability, and natural non-data conversation |
| T1 | Template Query | A known query pattern covered by an approved template |
| T2 | Follow-Up Analysis | Reason over, refine, compare, or drill into previous analytical context |
| T3 | Analytical Execution | Multi-step analysis and questions requiring templates and/or validated NL2SQL |
| T4 | Clarification | Missing required slots or multiple materially different interpretations |
| T5 | Out of Scope | Requests outside current analytical capabilities |
| T6 | Support Delegation | Delegate the request and context to M3 |

### 4.3 Router precedence

The router must apply the following order:

1. Resume pending clarification.
2. Detect support and delegate to T6.
3. Detect greetings, capability questions, and out-of-scope requests.
4. Detect a follow-up against stored analytical context.
5. Detect analytical complexity.
6. Match a known template.
7. Request clarification when required information is missing.
8. Use T3 for a valid analytical request not covered by a template.

Complexity is evaluated before final template dispatch. A question may contain a template-covered metric while still requiring T3 because it asks for multiple entities, drivers, causes, comparisons, or sequential analysis.

---

## 5. Target Graph

```text
START
  |
  v
Context Loader
  |
  v
Intent Router
  |
  +--> T0 Direct Response ------------------------------+
  +--> T1 Template Pipeline ----------------------------+
  +--> T2 Follow-Up Resolver ---------------------------+
  +--> T3 Analytical Planner ---------------------------+
  +--> T4 Clarification --------------------------------+
  +--> T5 Out-of-Scope Response ------------------------+
  +--> T6 M3 Delegation --------------------------------+
                                                        |
                                                        v
                                                Context Saver
                                                        |
                                                        v
                                                       END
```

All M1 database execution paths use the same query gateway:

```text
Query Request
  → Template Registry or NL2SQL Generator
  → SQL AST and Schema Validator
  → Read-Only Executor
  → Result Evaluator
  → Continue / Repair / Clarify / Respond
```

---

## 6. State Contract

Update `agents/m1/schemas/m1_state.py` additively. Existing fields remain available until all consumers have migrated.

### 6.1 Routing state

```python
assigned_tier: Literal["T0", "T1", "T2", "T3", "T4", "T5", "T6"]
domain_intent: str
router_confidence: float
router_reasoning: str
route_signals: list[str]
```

### 6.2 Analytical frame

```python
analysis_frame: dict
```

The frame uses a stable shape:

```json
{
  "metric": "sales_revenue",
  "entities": [{"type": "product_category", "value": "Electronics"}],
  "dimensions": ["month", "product_category"],
  "filters": {},
  "date_range": {"start": "2024-04-01", "end": "2024-06-30"},
  "comparison_range": {"start": "2024-01-01", "end": "2024-03-31"},
  "grain": "month",
  "analysis_type": "comparison",
  "requested_output": null
}
```

This frame is the authoritative conversational memory. Raw conversation text remains supporting context, not the only source of truth.

### 6.3 Query execution state

```python
query_mode: Literal["template", "nl2sql", "none"]
matched_template: str
template_confidence: float
pending_sql: str
sql_parameters: dict
sql_validation: dict
sql_attempt: int
query_artifacts: list[dict]
```

Every query artifact records:

- source: template or NL2SQL
- purpose/subtask
- SQL fingerprint
- parameters
- referenced tables and columns
- validation result
- execution status
- row count
- duration
- bounded result sample
- error class

Do not persist unrestricted SQL results in conversation metadata.

### 6.4 Result evaluation state

```python
result_status: Literal[
    "complete", "partial", "empty", "suspicious", "invalid", "failed"
]
result_coverage: float
result_evidence: list[str]
result_gaps: list[str]
result_needs_requery: bool
result_format_hint: OutputType
```

### 6.5 T2/T3 state

```python
followup_mode: Literal[
    "reason_only", "refine", "drill_down", "compare", "requery", "summarize"
]
react_plan: list[dict]
react_iteration: int
react_done: bool
react_exit_reason: str
tool_results: list[dict]
```

### 6.6 Clarification and delegation

```python
clarification_pending: bool
clarification_original_query: str
clarification_missing_slots: list[str]
clarification_question: str
m3_delegation_payload: dict
```

---

## 7. Conversation Memory in `conversations.metadata`

No database migration is required for V1.

### 7.1 Assistant-turn metadata

Persist a bounded structure:

```json
{
  "schema_version": 1,
  "assigned_tier": "T3",
  "domain_intent": "sales",
  "analysis_frame": {},
  "matched_template": null,
  "query_mode": "nl2sql",
  "result_summary": {
    "status": "complete",
    "row_count": 6,
    "columns": ["month", "revenue"],
    "key_metrics": {}
  },
  "output_format": "line_chart",
  "clarification": null
}
```

### 7.2 Persistence rules

- Keep narrative text in `content`.
- Store structured analytical context in `metadata`.
- Load metadata for recent assistant turns.
- Do not store full raw result sets.
- Cap samples and summaries by configurable limits.
- Add `schema_version` for future migrations.
- If metadata is missing or malformed, fall back safely to text history.

`backend/services/conversation_service.py` must therefore return both message content and metadata.

---

## 8. Central Query Gateway

Create a shared query execution layer used by T1, T2, T3, and invoice analysis.

### 8.1 Query policy

Approved M1 tables:

```python
M1_APPROVED_TABLES = {
    "customers",
    "customer_interactions",
    "inventory",
    "invoice_items",
    "invoices",
    "order_items",
    "orders",
    "payments",
    "products",
    "shipments",
    "transactions",
    "vendors",
}
```

Explicitly blocked from M1:

```python
M1_BLOCKED_TABLES = {
    "audit_log",
    "conversations",
    "tax_chunks",
}
```

Tax RAG continues to access `tax_chunks` through its dedicated retrieval implementation, not through NL2SQL.

### 8.2 Validation layers

Every SQL statement must pass all gates:

1. Parse successfully with PostgreSQL dialect in `sqlglot`.
2. Contain exactly one statement.
3. Root statement is `SELECT`, `UNION`, or a `WITH` expression ending in a read query.
4. Reject DDL, DML, transaction, command, procedure, and permission expressions.
5. Extract every physical table referenced by the AST.
6. Allow only `M1_APPROVED_TABLES`.
7. Resolve every referenced column against `db_schema_reference.json`.
8. Reject wildcard selection unless explicitly allowed for a bounded detail query.
9. Reject access to `pg_catalog`, `information_schema`, and non-public schemas.
10. Apply a maximum join count.
11. Apply a maximum subquery/CTE depth.
12. Enforce a row limit for detail queries.
13. Enforce statement timeout.
14. Execute exclusively through `get_readonly_session()`.
15. Redact literals and sensitive values from logs.

String keyword checks are defense-in-depth only; they are not the main validator.

### 8.3 Schema source

Use `docs/architecture/db_schema_reference.json` as the machine-readable schema contract. Regenerate it through the existing connection verification script when the database schema changes.

---

## 9. Template Registry

The existing templates remain the preferred path.

Convert template definitions into a registry with:

- ID and business name.
- Supported domain intents.
- Required and optional slots.
- SQL text.
- Approved tables.
- Expected result columns.
- Result grain.
- Comparison capability.
- Output hint.
- Evaluation rules.

Do not silently default a required date range to `2000-01-01` through `2100-01-01`. If the template semantically requires a period and none can be inferred safely, route to T4.

Invoice templates must use the same query gateway rather than maintaining a separate partially duplicated SQL validator.

---

## 10. T3 Validated NL2SQL

NL2SQL is an approved part of this migration. It handles analytical questions that are valid for M1 but are not sufficiently covered by existing templates.

### 10.1 When NL2SQL is allowed

Use NL2SQL only when:

- The router selected T3.
- No template or composition of templates can answer the subtask cleanly.
- The required entities and metrics exist in the M1 schema.
- Required ambiguity has been resolved.
- The planner defines a specific subtask and expected result shape.

Do not use NL2SQL for greetings, support, tax RAG retrieval, or out-of-scope requests.

### 10.2 NL2SQL input contract

The generator receives:

- User question.
- Resolved `analysis_frame`.
- Current subtask.
- Only the relevant schema slice.
- Approved tables and relationships.
- Existing query artifacts when repairing.
- Expected columns and grain.
- Explicit instruction to return SQL plus structured rationale, not prose.

The model must not receive database credentials or unrestricted conversation history.

### 10.3 Generation output

```python
class GeneratedQuery(BaseModel):
    sql: str
    purpose: str
    expected_columns: list[str]
    expected_grain: str
    referenced_tables: list[str]
    assumptions: list[str]
    confidence: float
```

### 10.4 Bounded SQL repair loop

```text
Generate SQL
  → Static Validation
      → invalid: classify error → repair
      → valid: execute read-only
          → DB error: sanitize error → repair
          → success: evaluate result
              → incomplete/invalid: create semantic feedback → repair or replan
              → complete: accept artifact
```

Limits:

- Maximum SQL attempts per subtask: 3.
- Maximum T3 iterations per request: 5.
- Maximum DB executions per request: configurable; initial value 4.
- Never retry an identical SQL fingerprint.
- Never broaden tables after a security-policy failure.
- Security violations terminate the SQL subtask; they are not repair hints.

### 10.5 Error taxonomy

The repair loop classifies errors before sending feedback:

- `syntax_error`
- `unknown_table`
- `unknown_column`
- `ambiguous_column`
- `type_mismatch`
- `invalid_aggregation`
- `invalid_grouping`
- `execution_timeout`
- `empty_result`
- `result_shape_mismatch`
- `semantic_coverage_gap`
- `security_policy_violation`

Only sanitized, minimal error details are sent back to the model.

### 10.6 Repair prompt contract

The repair model receives:

- Previous SQL.
- Error category.
- Sanitized database or validator message.
- Relevant schema slice.
- Original subtask and expected shape.
- Previous assumptions.

It must return a complete replacement query. The system must not perform unsafe string patching on model-generated SQL.

### 10.7 Result correctness evaluation

Successful execution does not mean the query is correct.

`ResultEvaluatorNode` checks:

- Required columns are present.
- Result grain matches the planned grain.
- Filters and periods are represented.
- Comparison questions include all required periods/groups.
- Percentage-change questions include baseline and comparison values.
- Breakdown questions are not answered with an unexplained scalar.
- Aggregated values are not duplicated by incorrect joins.
- Null/zero dominance is plausible.
- Row count is plausible for the requested shape.
- The result can support the final claims.

For high-risk logical checks, use:

- deterministic rules first;
- a bounded LLM semantic-coverage call second;
- an optional verification query for totals or row duplication when justified.

The evaluator must never invent a cause from the returned data. It may label a statement as an inference and state what evidence supports it.

---

## 11. T2 Follow-Up Analysis

T2 resolves the new message against `analysis_frame` and recent assistant metadata.

### 11.1 Follow-up modes

- `reason_only`: explain an already available result.
- `refine`: modify filters without changing the analytical subject.
- `drill_down`: add a dimension or move to a finer grain.
- `compare`: add a baseline or second group.
- `requery`: retrieve data not available in prior artifacts.
- `summarize`: combine established findings from the conversation.

### 11.2 Context sufficiency

Before reusing prior results, verify:

- the prior metric matches;
- required dimensions exist;
- filters and time period are compatible;
- result summary has sufficient evidence;
- the user did not introduce a new entity.

If evidence is insufficient, T2 creates a targeted T1 or T3 subquery rather than asking the LLM to guess from the previous narrative.

---

## 12. Result Evaluation and Response Intelligence

`ResultEvaluatorNode` replaces the assumption that any non-empty result is sufficient.

### 12.1 Status behavior

| Status | Behavior |
|---|---|
| complete | Continue to output selection and response generation |
| partial | Query again if the missing evidence is obtainable within budget |
| empty | Explain the data gap and preserve the applied filters |
| suspicious | Warn about data quality and avoid strong conclusions |
| invalid | Repair or replan |
| failed | Return a controlled failure after bounded retries |

### 12.2 Analyst response contract

The final narrative should include, when applicable:

1. Direct answer.
2. Key numbers and comparison.
3. Main drivers supported by evidence.
4. Anomalies or material changes.
5. Assumptions and data limitations.
6. A useful next analytical step.

Facts, calculations, and inferences must remain distinguishable.

---

## 13. T4 Clarification

Clarification is triggered by missing required slots or materially different interpretations, not merely because model confidence is imperfect.

The clarification response must:

- State what is missing.
- Offer two or three likely interpretations.
- Preserve the original query and resolved slots.
- Save pending clarification in conversation metadata.
- Merge the next user response with the original analytical frame.
- Re-enter the router and clear the pending state after resolution.

---

## 14. T6 Delegation to M3

M1 must not query M3-only tables or implement support classification, handoff, refund, dispute, shipment, or case-management logic.

T6 creates a delegation payload:

```json
{
  "source": "m1",
  "session_id": "...",
  "user_query": "...",
  "language": "ar",
  "user_context": {},
  "conversation_summary": "...",
  "detected_support_signals": [],
  "identifier_candidates": []
}
```

Implementation options, in preferred order:

1. Invoke the M3 graph through an internal Python service boundary.
2. Invoke the internal M3 service endpoint.
3. If M3 is unavailable, return a controlled delegation-unavailable response.

The M1 response schema must remain stable while carrying M3 output and delegation metadata.

---

## 15. Files to Create

| File | Responsibility |
|---|---|
| `agents/m1/config/constants.py` | Tier thresholds, iteration budgets, row limits, approved tables |
| `agents/m1/schemas/analysis_models.py` | Pydantic contracts for analytical frame, plans, queries, validation, and evaluation |
| `agents/m1/nodes/context_loader_node.py` | Load structured context from conversation metadata |
| `agents/m1/nodes/intent_router_node.py` | Assign domain intent and execution tier |
| `agents/m1/nodes/context_saver_node.py` | Build bounded assistant metadata |
| `agents/m1/nodes/result_evaluator_node.py` | Result completeness and semantic coverage |
| `agents/m1/nodes/followup_resolver_node.py` | T2 mode and context resolution |
| `agents/m1/nodes/t0_conversation_node.py` | Direct natural conversation |
| `agents/m1/nodes/t5_oos_node.py` | Out-of-scope response |
| `agents/m1/nodes/t6_m3_delegation_node.py` | M3 delegation adapter |
| `agents/m1/nodes/t3_planner_node.py` | Structured analytical plan |
| `agents/m1/nodes/t3_executor_node.py` | Bounded step execution |
| `agents/m1/nodes/t3_aggregator_node.py` | Evidence and result aggregation |
| `agents/m1/tools/query_gateway.py` | Central validated read-only execution |
| `agents/m1/tools/sql_policy.py` | AST, schema, table, column, and complexity policy |
| `agents/m1/tools/schema_catalog.py` | Load and expose relevant schema slices |
| `agents/m1/tools/template_registry.py` | Unified template metadata and lookup |
| `agents/m1/tools/nl2sql_generator.py` | Structured SQL generation |
| `agents/m1/tools/nl2sql_repair.py` | Error-aware bounded SQL repair |
| `agents/prompts/m1_router.py` | Router prompt and examples |
| `agents/prompts/m1_planner.py` | Analytical planning prompt |
| `agents/prompts/nl2sql.py` | Generation and repair prompts |
| `scripts/test_architecture_migration.py` | Automated tier and regression suite |
| `scripts/test_nl2sql_safety.py` | Adversarial SQL and policy tests |
| `scripts/test_nl2sql_repair.py` | Syntax/schema/execution/result repair tests |
| `scripts/test_conversational_analysis.py` | Multi-turn tests based on existing question chains |

No new question-bank Markdown file should be created.

---

## 16. Files to Modify

| File | Required change |
|---|---|
| `agents/m1/schemas/m1_state.py` | Add the new state fields while preserving current fields |
| `agents/m1/graphs/m1_graph.py` | Replace the current entry routing with the stratified graph |
| `agents/m1/tools/db_query_tool.py` | Move templates into the registry and execution into the gateway |
| `agents/m1/nodes/invoice_analysis_tool_node.py` | Use the shared query gateway and evaluator |
| `agents/m1/nodes/validation_enrichment_node.py` | Retain anomaly enrichment; move result completeness into the evaluator |
| `agents/m1/nodes/output_selector_node.py` | Accept evaluator format hints and aggregated T3 result shapes |
| `agents/m1/nodes/narrative_generator_node.py` | Generate evidence-bound analyst responses |
| `agents/m1/nodes/clarification_node.py` | Use missing slots and persist clarification context |
| `backend/services/conversation_service.py` | Read and write metadata, not only role/content |
| `backend/api/v1/m1_query.py` | Initialize new state, persist structured metadata, support T6 result |
| `backend/core/config.py` | Add configurable budgets and feature flags |
| `ERP_Test_Questions.md` | Add tier/expected execution annotations only where needed |
| `docs/progress/agent_execution_log.md` | Record each completed migration phase |

---

## 17. Implementation Phases

### Phase 0 — Baseline and feature flags

**Estimated effort:** 2 days

- Freeze current behavioral baseline.
- Run existing Sprint 1–6 tests.
- Classify `ERP_Test_Questions.md` cases by expected tier and query mode.
- Add `M1_STRATIFIED_ROUTER_ENABLED` and `M1_NL2SQL_ENABLED`.
- Capture current latency, LLM calls, and failures.

**Exit gate:** Existing tests pass and rollback flags work.

### Phase 1 — State, models, constants, and context metadata

**Estimated effort:** 3 days

- Add state fields and Pydantic contracts.
- Upgrade conversation service to return metadata.
- Implement context loader/saver.
- Keep metadata bounded and versioned.

**Exit gate:** A three-turn chain restores the same analytical frame after persistence.

### Phase 2 — Central query gateway and SQL policy

**Estimated effort:** 4 days

- Implement AST and schema validation.
- Apply the confirmed whitelist.
- Add timeout, limits, fingerprints, and sanitized errors.
- Route existing template execution through the gateway.
- Route invoice SQL through the same gateway.

**Exit gate:** All safe templates pass; all destructive, cross-domain, malformed, and unauthorized queries are blocked before DB execution.

### Phase 3 — Template registry and result evaluator

**Estimated effort:** 3 days

- Convert templates into registry entries.
- Define required slots and expected shapes.
- Implement evaluator statuses and coverage rules.
- Add data-gap and suspicious-data responses.

**Exit gate:** Empty data, missing comparison periods, wrong grains, and invalid result shapes are detected deterministically.

### Phase 4 — Router in shadow mode

**Estimated effort:** 4 days

- Implement domain and tier classification.
- Add Arabic normalization for signal matching.
- Run old and new routing decisions side by side.
- Log disagreements without changing production behavior.
- Tune against `ERP_Test_Questions.md`.

**Exit gate:** Agreed routing accuracy threshold is met with no critical T6/T5 leakage.

### Phase 5 — Activate T0, T1, T4, T5, and T6

**Estimated effort:** 3 days

- Activate the router entry point for low-risk tiers.
- Preserve the existing template path for T1.
- Implement clarification lifecycle.
- Implement M3 delegation adapter.

**Exit gate:** Greetings make no DB call; support does not query M1 tables; template regression remains green.

### Phase 6 — T2 analytical memory

**Estimated effort:** 4 days

- Implement follow-up mode classification.
- Resolve references through structured frames.
- Reuse evidence only when sufficient.
- Requery through T1/T3 when needed.

**Exit gate:** All conversational chains in `ERP_Test_Questions.md` retain period, entity, filter, and metric context.

### Phase 7 — T3 planner and validated NL2SQL

**Estimated effort:** 7 days

- Implement structured planning.
- Add template-first tool selection.
- Implement NL2SQL generation.
- Implement static validation and execution.
- Implement categorized repair feedback.
- Add result evaluation and replan behavior.
- Enforce all attempt and execution budgets.

**Exit gate:** Uncovered analytical questions can be answered safely; injected, invalid, or semantically wrong SQL cannot escape the bounded loop.

### Phase 8 — Aggregation and analyst narrative

**Estimated effort:** 3 days

- Combine multiple artifacts.
- Compute comparisons in Python where possible.
- Generate evidence-bound findings and caveats.
- Support aggregated chart/table payloads.

**Exit gate:** Multi-step answers identify findings and drivers without unsupported causal claims.

### Phase 9 — Full evaluation and rollout

**Estimated effort:** 4 days

- Run single-turn and conversational banks.
- Run adversarial SQL tests.
- Measure tier latency and LLM/DB budgets.
- Enable staged rollout: shadow → internal → partial → full.
- Record implementation results in the execution log.

**Exit gate:** All critical acceptance criteria pass and rollback remains available.

**Total estimate:** approximately 34 working days for one developer, excluding M3 implementation itself.

---

## 18. Testing Strategy

### 18.1 Existing question bank

`ERP_Test_Questions.md` is the canonical business scenario source.

Use:

- Financial questions for T1 and T3 comparisons.
- Aging questions for filtering and result-shape evaluation.
- Invoice questions for shared-gateway regression.
- Anomaly questions for evaluator/enrichment interaction.
- Clarification questions for T4.
- Conversational chains for T2 and T3.
- M3 questions for T6 delegation boundaries.

### 18.2 Additional automated test categories

These are code-level tests, not a new question-bank document:

- Valid SELECT and CTE queries.
- Multiple statements.
- DDL/DML hidden in CTEs or comments.
- Unauthorized tables and schemas.
- Unknown and ambiguous columns.
- Invalid joins and duplicate aggregation.
- Missing GROUP BY.
- Timeout and excessive complexity.
- Empty but valid results.
- Comparison returning one period.
- Repair success on attempt two.
- Repeated identical SQL rejection.
- Exhausted retry budget.
- Security violations that must not be repaired.
- Metadata truncation and malformed metadata fallback.

### 18.3 Metrics

- Tier routing accuracy.
- Domain-intent accuracy.
- Template selection accuracy.
- SQL static-validation precision.
- SQL execution success after repair.
- Result-completeness accuracy.
- Follow-up context resolution rate.
- Unsupported-claim rate.
- Average LLM calls per tier.
- P50/P95 latency per tier.
- Average DB executions per T3 request.

---

## 19. Acceptance Criteria

The migration is complete when:

1. Existing Sprint 1–6 behavior remains available or is intentionally superseded.
2. Every message receives a domain intent and execution tier.
3. M1 never queries `shipments` or `customer_interactions`.
4. T6 delegates to M3 without rebuilding support logic in M1.
5. Every M1 SQL statement passes the central gateway.
6. All M1 SQL executes with the read-only database role.
7. Template-covered questions continue to use templates.
8. Non-template analytical questions can use validated NL2SQL.
9. Invalid SQL receives bounded, categorized repair feedback.
10. Security-policy violations never become repair attempts.
11. A successful DB query is not accepted until result evaluation passes.
12. Partial comparison results trigger targeted requery or an explicit limitation.
13. T3 terminates within configured iteration and DB-call budgets.
14. Follow-up chains preserve metric, period, entity, and filters through metadata.
15. Clarification resumes the original request correctly.
16. Empty and suspicious results produce controlled explanations.
17. Final narratives distinguish facts from inferences.
18. `ERP_Test_Questions.md` scenarios pass their routing, data, and output expectations.
19. LangSmith traces expose route, plan, SQL validation, attempts, evaluator result, and exit reason.
20. Feature flags can return the system to the pre-migration graph.

---

## 20. Recommended Commit Sequence

1. `chore(m1): add migration feature flags and baseline tests`
2. `feat(m1): add analytical state contracts and metadata context`
3. `feat(m1): centralize schema-aware readonly query execution`
4. `refactor(m1): move templates to registry and shared gateway`
5. `feat(m1): add result evaluator and data-gap handling`
6. `feat(m1): add stratified router in shadow mode`
7. `feat(m1): activate direct clarification oos and m3 delegation tiers`
8. `feat(m1): add structured follow-up resolution`
9. `feat(m1): add bounded analytical planner and nl2sql`
10. `feat(m1): add sql repair and semantic result feedback`
11. `feat(m1): add multi-result aggregation and analyst narrative`
12. `test(m1): complete migration evaluation and rollout gates`

Each commit must update `docs/progress/agent_execution_log.md` after verification.

---

## 21. Risks and Controls

| Risk | Control |
|---|---|
| NL2SQL generates destructive SQL | AST policy, approved-table policy, read-only DB role |
| SQL executes but is logically wrong | Expected-shape contract, result evaluator, optional verification query |
| Repair loop increases cost | Strict attempt, iteration, and DB-call budgets |
| Router sends simple queries to T3 | Template confidence and shadow-mode evaluation |
| Router sends complex questions to T1 | Complexity check before template dispatch |
| Conversation metadata grows indefinitely | Bounded summaries, no full datasets, schema versioning |
| M1/M3 responsibility overlap | Explicit table and delegation boundaries |
| Existing frontend breaks | Preserve unified response schema and add optional metadata |
| LLM claims unsupported causes | Evidence-bound prompt and fact/inference separation |
| Schema changes invalidate generation | Machine-readable schema catalog and regeneration process |

---

## 22. Definition of Done

Implementation is done only when code, tests, traces, documentation, and rollback controls all agree with this plan. Completing node files without proving routing accuracy, SQL safety, result correctness, and multi-turn context retention is not considered completion.

# M3 — Customer Support Agent: Module Map

> Quick reference for developers working on M3. All file locations post-migration.
> Read docs/architecture/erp_architecture_memory.md §M3 for full context.
> M3 depends on M1's shared services and DB infrastructure — Sprint 0 of M1 must complete first.

---

## Sprint 0 — Mock Data Setup (M3-specific)

| Task | File Location | Notes |
|------|--------------|-------|
| order_status mock table | database/migrations/ | order_id, customer_id, status, created_at, estimated_delivery, items |
| shipping mock table | database/migrations/ | tracking_id, order_id, status, carrier, location, last_update |
| customer_history mock table | database/migrations/ | customer_id, interaction_type, issue_type, resolution, date |
| Mock data seeder | database/seeds/ | Must include: 1 repeat-issue customer, 1 not-found order (DEL-999 equivalent) |

**Critical consistency rule:** customer_id in order_status MUST match customer_id in invoices and customer_history.

---

## LangGraph Graph

| File | Status | Implements |
|------|--------|-----------|
| agents/m3/graphs/m3_graph.py | PLACEHOLDER | Full M3 LangGraph StateGraph |

---

## M3 State Schema

| File | Status | Content |
|------|--------|---------|
| agents/m3/schemas/m3_state.py | PLACEHOLDER | Create M3State TypedDict |

Fields required:
```python
customer_identifier: dict  # { type: "order_id"|"invoice_id"|"customer_id", value: str }
issue_description: str
issue_type: Literal["status_inquiry", "billing_dispute", "shipping_issue", "refund_request", "general_complaint"]
fetched_data: dict  # { invoice: dict, order: dict, shipping: dict, history: list }
data_completeness: float  # 0.0 → 1.0
confidence_score: float   # 0.0 → 1.0
draft_response: str
review_required: bool
escalation_needed: bool
final_response: str
```

---

## M3 Nodes

| Node | File | Status | LLM | Sprint |
|------|------|--------|-----|--------|
| InputParserNode | agents/m3/nodes/input_parser_node.py | PLACEHOLDER | GPT-4o-mini | 1 |
| DataFetcherNode | agents/m3/nodes/data_fetcher_node.py | PLACEHOLDER | None | 1 |
| DataCompletenessCheckNode | agents/m3/nodes/data_completeness_node.py | PLACEHOLDER | None | 1 |
| IssueClassifierNode | agents/m3/nodes/issue_classifier_node.py | PLACEHOLDER | GPT-4o-mini | 2 |
| ContextBuilderNode | agents/m3/nodes/context_builder_node.py | PLACEHOLDER | None | 2 |
| ResponseGeneratorNode | agents/m3/nodes/response_generator_node.py | PLACEHOLDER | GPT-4o | 3 |
| HumanReviewGateNode | agents/m3/nodes/human_review_node.py | PLACEHOLDER | None | 4 |

---

## M3 Tools

| Tool | File | Status | Data Source | Sprint |
|------|------|--------|-------------|--------|
| invoice_fetcher_tool | agents/m3/tools/invoice_fetcher_tool.py | PLACEHOLDER | REAL PostgreSQL invoices table | 1 |
| mock_data_tool | agents/m3/tools/mock_data_tool.py | PLACEHOLDER | MOCK tables (order_status, shipping, customer_history) | 1 |

---

## Human Review Gate Logic

| Condition | Review Decision |
|-----------|----------------|
| issue_type == billing_dispute | MANDATORY review |
| issue_type == refund_request | MANDATORY review |
| confidence_score < 0.70 | MANDATORY review |
| escalation_needed == True | SKIP review → direct escalation |
| issue_type == status_inquiry | OPTIONAL (configurable on/off) |
| issue_type == general_complaint + high confidence | OPTIONAL (can auto-send) |

---

## M3 Backend Files

| File | Status | Purpose |
|------|--------|---------|
| backend/api/v1/m3_support.py | PLACEHOLDER | POST /support endpoint |
| backend/services/m3_orchestrator.py | PLACEHOLDER | Invokes m3_graph |
| backend/services/human_review_service.py | RENAMED (was confirmation_service.py) | Human review coordination |
| backend/services/audit_service.py | KEPT | Audit trail logging |
| backend/models/m3_case.py | PLACEHOLDER | Case persistence |
| backend/models/confirmation_token.py | KEPT | Human approval tokens |
| backend/schemas/m3_support.py | PLACEHOLDER | M3 Pydantic schemas |

---

## M3 Frontend Files

| File | Status | Purpose |
|------|--------|---------|
| frontend/app/m3/page.tsx | PLACEHOLDER | M3 customer support page |
| frontend/components/m3/CustomerInputForm.tsx | PLACEHOLDER | Customer input interface |
| frontend/components/m3/HumanReviewPanel.tsx | PLACEHOLDER | Employee review interface |
| frontend/components/m3/TransparencyPanel.tsx | PLACEHOLDER | Data source visibility |
| frontend/components/m3/ConfidenceIndicator.tsx | PLACEHOLDER | Green/Yellow/Red badge |
| frontend/components/m3/EscalationView.tsx | PLACEHOLDER | Escalated case display |
| frontend/components/review/confirmation/ | MOVED (was components/confirmation/) | Review panel base — adapt for M3 |
| frontend/hooks/useM3Support.ts | PLACEHOLDER | M3 state management hook |
| frontend/types/m3.ts | PLACEHOLDER | M3 TypeScript types |

---

## M3 Graceful Degradation Strategy

| data_completeness | Response Strategy | Confidence |
|-------------------|-----------------|-----------|
| 1.0 (all data) | Full detailed response | 🟢 High |
| 0.5 (partial) | Available data + "Support will contact you within 24h for [missing field]" | 🟡 Medium |
| 0.0 (no data) | "Could not find [identifier]. Please verify or contact support at [channel]" | 🔴 Low + Escalation |

---

## M3 Demo Scenarios (Sprint 6)

| # | Input | Expected Behavior |
|---|-------|------------------|
| 1 | Order ORD-2024-1567 status | Confidence High → auto-send available with shipping details |
| 2 | Invoice INV-890 dispute | billing_dispute → Human Review mandatory |
| 3 | Delivery DEL-999 (not found) | Graceful degradation → Escalation |
| 4 | Repeat issue customer | customer_history shows 3+ same issue → auto-escalate to manager |

---

## Audit Trail (Sprint 4)

Every M3 decision is logged with:
```json
{
  "timestamp": "...",
  "case_id": "...",
  "issue_type": "...",
  "confidence_score": 0.0,
  "review_required": true,
  "action_taken": "approved|rejected|escalated",
  "reviewed_by": "...",
  "agent_id": "..."
}
```
Stored via: backend/services/audit_service.py → backend/models/audit_log.py

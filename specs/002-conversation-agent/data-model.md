# Data Model: Conversation Agent (Small-Talk Route)

This feature adds no new persistent storage. It extends one enum-like field and
reuses existing state and persistence from feature 001.

## Entities / State

### RouteClassification (extended)

The router's decision attached to the graph state (`M3State`).

| Field | Type | Change | Notes |
|-------|------|--------|-------|
| `route` | enum | **extended** | now `greeting \| general_knowledge \| customer_issue \| hybrid` |
| `route_confidence` | float 0..1 | unchanged | low confidence → `customer_issue` fallback |
| `rag_collection` | enum | unchanged | `support_kb \| tax \| none`; always `none` for `greeting` |

Validation / rules:
- `route == "greeting"` ⇒ `rag_collection == "none"`, `review_required == False`,
  `escalation_needed == False`, `rag_sources == []`.
- Default on low confidence remains `customer_issue` (never `greeting`).

### M3State fields touched by greeting_node

| Field | Type | Set by greeting_node |
|-------|------|----------------------|
| `draft_response` | str | friendly reply text |
| `final_response` | str | same as draft (no review) |
| `review_required` | bool | `False` |
| `escalation_needed` | bool | `False` |
| `confidence_score` | float | a high constant (e.g. 1.0) — no data uncertainty |

### ConversationTurn (reused, unchanged)

Existing `conversations` table from feature 001. A greeting exchange is persisted
identically (user turn + assistant turn) when a `session_id` is supplied. No
schema change.

## Route lifecycle (state transition)

```text
intent_router
   ├─ greeting          → greeting_node            → END
   ├─ general_knowledge → rag_node → response_gen  → review_gate → END/escalate
   ├─ customer_issue    → input_parser → …         → review_gate → END/escalate
   └─ hybrid            → rag_node → input_parser → … → review_gate → END/escalate
```

The greeting branch is terminal after `greeting_node` and deliberately does not
traverse `rag_node`, the CRM pipeline, or `human_review_gate`.

# Module 3 (M3) — Customer Support / Issue Resolution Agent

This module is a placeholder directory structure prepared for the Customer Support Agent implementation.

## Agent Workflow
```
Customer Input (Identifier + Problem Description)
       │
       ▼
[InputParserNode] (GPT-4o-mini)
       │
       ▼
[DataFetcherNode] (Real Invoice + Mock Order/Shipping/History)
       │
       ▼
[DataCompletenessCheckNode]
       │
       ├─ (Complete/Partial) ──► [IssueClassifierNode] ──► [ContextBuilderNode] ──► [ResponseGeneratorNode] ──► [HumanReviewGateNode]
       │                                                                                                                  │
       └─ (No Data Found) ────────────────────────────────────────────────────────────────────────────────────────► [EscalationNode]
```

## LangGraph State Schema
```python
class M3State(TypedDict):
    customer_identifier: dict      # { type: "order_id" | "invoice_id" | "customer_id", value: str }
    issue_description: str
    issue_type: str                # "status_inquiry" | "billing_dispute" | "shipping_issue" | "refund_request" | "general_complaint"
    fetched_data: dict             # { invoice: dict, order: dict, shipping: dict, history: list }
    data_completeness: float       # 0.0 to 1.0
    confidence_score: float        # 0.0 to 1.0
    draft_response: str
    review_required: bool
    escalation_needed: bool
    final_response: str
```

## Directory Structure
- `graphs/`: StateGraph definitions and routing logic.
- `nodes/`: Workflow nodes (`InputParserNode`, `DataFetcherNode`, etc.).
- `schemas/`: State schema Pydantic definitions.
- `tools/`: Retreival and integration tools.

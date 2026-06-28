# Contract Delta: `POST /api/v1/support`

This feature does not add new endpoints. It changes the *behavior* of `/support`
for record-dependent messages that lack a reference, and adds one optional
response field so the caller can tell a clarifying question from a final answer.

## Request (unchanged)

```json
{
  "query": "string (1–2000 chars)",
  "identifier": { "type": "order_id|invoice_id|customer_id", "value": "string" } | null,
  "session_id": "string | null",
  "rejection_context": { } | null
}
```

- `session_id` is what makes multi-turn clarification work. A caller that wants
  the clarify→answer loop **MUST** send a stable `session_id` across turns.
  Without it, each message is single-turn (the assistant can still ask, but the
  follow-up reply won't be tied to the original question).

## Response (additive)

Existing fields are unchanged. One new optional field:

| Field | Type | Meaning |
|-------|------|---------|
| `clarification_pending` | `bool` (default `false`) | `true` when this reply is a follow-up **question** asking for a missing/ambiguous reference — not a final answer and not an escalation. |

```json
{
  "draft_response": "string",
  "final_response": "string",         // the clarifying question, in the customer's language
  "confidence_score": 0.0,
  "confidence_label": "High|Medium|Low",
  "review_required": false,
  "escalation_needed": false,         // false while still clarifying
  "clarification_pending": true,      // NEW
  "escalation_summary": {},
  "issue_type": null,                 // not classified until data is available
  "route": "customer_issue|hybrid",
  "rag_sources": [],
  "transparency_data": { "invoice": null, "order": null, "shipping": null, "history": null },
  "missing_fields": []
}
```

## Behavioral contract

| Input situation | Before (today) | After (this feature) |
|-----------------|----------------|----------------------|
| Record question **with** valid reference | Answers from data | Unchanged — answers from data |
| Record question **without** reference, 1st/2nd turn | `escalation_needed=true`, generic escalation text | `clarification_pending=true`, a question asking for the exact reference (AR/EN) |
| Bare ambiguous number ("1567") | Escalation | Question: "Is this an order, invoice, or customer number?" |
| Reference supplied in a later turn (same `session_id`) | n/a | Answers the original question from the looked-up data |
| Still no reference after 2 asks | — | `escalation_needed=true`, handed to a human with context |
| Reference supplied but **not found** | Generic escalation | Graceful "couldn't find <ref>, please verify" (FR-008) |
| Greeting / general-knowledge | Direct answer | Unchanged — never asks for a reference (SC-004) |
| Billing dispute / refund (once data known) | `review_required=true` | Unchanged — still mandatory human review (FR-013) |

## Compatibility

- Additive only: clients that ignore `clarification_pending` still function; the
  clarifying question is delivered in `final_response` like any assistant turn,
  so the existing frontend renders it without changes.

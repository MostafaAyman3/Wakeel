# Contract: Intent Router (extended) + `/support` response delta

## Router classification contract

The router LLM (structured output) returns one classification per message.

**Output schema (unchanged shape, extended `route` enum):**

```json
{
  "route": "greeting | general_knowledge | customer_issue | hybrid",
  "collection": "support_kb | tax | none",
  "confidence": 0.0,
  "reasoning": "one sentence"
}
```

**Routing rules (precedence, highest first):**

1. Message contains an order/invoice reference OR complaint/issue signal →
   `customer_issue` (or `hybrid` if it also needs policy knowledge).
2. Message asks a knowledge/policy/FAQ/tax question → `general_knowledge`
   (or `hybrid`).
3. Message is pure social/small-talk (greeting, well-wishing, thanks, farewell)
   with no actionable request → `greeting`, `collection = none`.
4. Confidence `< 0.5` → fall back to `customer_issue` (NEVER `greeting`).

**Examples:**

| Message | route | collection |
|---------|-------|-----------|
| "Hi" / "السلام عليكم" | greeting | none |
| "how are you?" / "كيف حالك" | greeting | none |
| "thanks!" / "شكراً" | greeting | none |
| "What is your return policy?" | general_knowledge | support_kb |
| "Hi, what is your return policy?" | general_knowledge | support_kb |
| "Where is order ORD-2024-0001?" | customer_issue | none |
| "Hello, I want a refund for INV-5" | customer_issue | none |
| "My order is late, refund per policy?" | hybrid | support_kb |

## Greeting reply contract

When `route == greeting`, the response satisfies:

- `final_response`: short (1–2 sentences), friendly, in the customer's language,
  ends by inviting the customer to ask their question / describe their issue.
- `route`: `"greeting"`.
- `rag_sources`: `[]`.
- `review_required`: `false`.
- `escalation_needed`: `false`.
- No internal data, no held draft, no escalation notice.

## `POST /support` response delta

`SupportResponse.route` may now be `"greeting"` in addition to the existing
values. All other fields keep their existing types. No request-schema change.

```jsonc
// Example response to "Hi"
{
  "route": "greeting",
  "final_response": "Hello! 👋 How can I help you today?",
  "rag_sources": [],
  "review_required": false,
  "escalation_needed": false,
  "issue_type": null
}
```

# Contract: Conversation Memory Behavior

No new endpoints and no API schema changes. `POST /api/v1/support` already accepts
`session_id` and returns the existing response. This contract describes the
**behavioral change** for a given `session_id` and the frontend session-id rule.

## Request (unchanged)

```json
{ "query": "string", "session_id": "uuid-string", "identifier": null }
```

- `session_id` ties turns into one conversation. It MUST be a stable id reused
  across the turns of a conversation. Without it, no recall (single-turn).

## Behavioral contract (same `session_id`)

| Situation | Before | After (this feature) |
|-----------|--------|----------------------|
| "my name is Kareem" then "what's my name?" | replies "give me your order number" | replies "Kareem" |
| "اسمي كريم" then "اسمي ايه؟" | generic greeting | replies "كريم" (Arabic) |
| name never stated → "what's my name?" | asks for an order number | "I don't have your name yet — what should I call you?" (no fabrication) |
| "Kareem" then "actually Khaled" → "what's my name?" | n/a | "Khaled" (most recent) |
| "what's my name?" in a **different** `session_id` | — | does not know it (no leak) |
| record question ("where is my order ORD-…") | answers from data | unchanged (still CRM path) |
| greeting / general-knowledge | answers | unchanged, now also memory-aware |

## Routing contract

- A question answerable from the conversation itself (personal recall, "what did I
  say", chit-chat referencing earlier turns) routes to the **conversational**
  (greeting) path — NOT `customer_issue`.
- An actionable record request still routes to `customer_issue` / `hybrid` and is
  unaffected.

## Frontend session-id contract (FR-010)

- On load: read `session_id` from `localStorage`; if absent, generate one and store it.
- Reuse the stored id for every turn (memory survives page reload).
- "New chat": generate a new id, overwrite storage (fresh memory).

## Compatibility

- Additive/behavioral only. No response field added or removed. Clients and the
  existing frontend continue to work; recall simply starts functioning when a
  stable `session_id` is sent.

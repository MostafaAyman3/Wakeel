# Phase 1 Data Model: Clarifying Follow-up for Missing Identifiers

No database schema changes. This feature adds in-flight fields to the LangGraph
state (`M3State`) and reuses the existing `conversations` table for memory.

## Graph state additions (`agents/m3/schemas/m3_state.py`)

| Field | Type | Set by | Meaning |
|-------|------|--------|---------|
| `clarification_needed` | `bool` (default `False`) | `input_parser` | A required reference is missing and attempts remain → take the clarification branch instead of escalating. |
| `missing_slot` | `str \| None` | `input_parser` | What is missing / why: `"identifier"` (no reference at all) or `"ambiguous_type"` (value present, type unknown). Drives the wording of the question. |
| `clarification_attempts` | `int` (default `0`) | `clarification_node` (computed from `chat_history`) | How many times the assistant has already asked in this conversation. Compared against the limit (2). |
| `pending_value` | `str \| None` | `input_parser` | For `ambiguous_type`: the raw value the customer gave (e.g. `"1567"`) so the next turn can bind it to a type. |

These are partial-update keys on the existing `TypedDict` state; defaults are
initialized in `build_initial_state`.

### Derived / reused (no new field)

- **Attempt count** is *computed* by `clarification_node` from `chat_history`
  (count of prior assistant clarification turns), then surfaced as
  `clarification_attempts` for routing/telemetry. It is not persisted separately.
- **Original question / intent** is inherited via the existing conversation-aware
  `intent_router_node` (last 3 `chat_history` turns); no new slot needed (research D4).

## Existing entities reused

- **`conversations` table** (`backend/repositories/conversations.py`): stores each
  user/assistant turn for a `session_id`. Read via `load_conversation_history`,
  written via `append_conversation_turn`. The clarification question and the
  customer's reference reply are ordinary turns here.
- **Customer reference** (`customer_identifier = {type, value}`): unchanged shape;
  `type ∈ {order_id, invoice_id, customer_id}`.
- **Fetched record set** (`fetched_data = {invoice, order, shipping, history}`):
  unchanged; produced once a valid reference is known.

## State transitions (clarification sub-flow)

```text
input_parser
  ├─ identifier present ............................ → data_fetcher (existing flow)
  ├─ value present but type unknown ................ missing_slot="ambiguous_type",
  │                                                   clarification_needed=True
  ├─ no reference, attempts < 2 ................... missing_slot="identifier",
  │                                                   clarification_needed=True
  └─ no reference, attempts ≥ 2 ................... escalation_needed=True (existing escalation)

clarification_needed == True
  → clarification_node
       • compute clarification_attempts from chat_history
       • if attempts ≥ 2 → set escalation_needed=True, route to escalation_node
       • else compose AR/EN question for missing_slot → final_response, END turn
         (review_required=False, escalation_needed=False)
```

## Validation rules

- `clarification_needed` and `escalation_needed` are mutually exclusive outcomes
  for a turn (never both True on exit).
- A turn that asks a clarification MUST end without running `data_fetcher` /
  `response_generator` (no fabricated data, FR-008-adjacent).
- The clarification limit (2) is configurable via a single constant/setting; the
  count is always re-derived from `chat_history`, never trusted from the client.

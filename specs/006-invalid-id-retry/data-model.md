# Phase 1 Data Model: Invalid Identifier Retry & Guidance

No database schema changes. All new data lives in the in-flight `M3State` (a
`TypedDict`, total=False) and in the existing `conversations.metadata` JSON column.

## New `M3State` fields

Added to `agents/m3/schemas/m3_state.py` and seeded in `build_initial_state`.

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `invalid_id_attempts` | `int` | `0` | Trailing count of consecutive invalid-ID failures in this conversation, recomputed each turn from `chat_history`. The current failure is reflected as `prior_streak + 1`. |
| `invalid_id_pending` | `bool` | `False` | This turn's reply is an invalid-ID retry message or escalation menu (drives the API metadata tag). |
| `invalid_id_menu_shown` | `bool` | `False` | This turn presented the 3rd-attempt escalation menu (tagged so the next turn can interpret a menu choice). |
| `alt_lookup_choice` | `Optional[str]` | `None` | Set when the customer picked "search by phone/email" and alternate lookup is enabled; carries the collected contact value for a future contact-based lookup. Unused when `m3_alt_lookup_enabled=False`. |

These follow the same shape and conventions as Feature 004's
`clarification_*` fields. No existing field changes meaning.

## Conversation metadata (existing `conversations.metadata` JSON)

Tagged by `append_conversation_turn(assistant_metadata=…)` in `m3_support.py`:

| Metadata key | When set | Used by |
|--------------|----------|---------|
| `invalid_id` | `True` on a turn whose reply was a retry message **or** the escalation menu (`invalid_id_pending`) | `invalid_id_node` to count the trailing streak |
| `invalid_id_menu` | `True` on a turn that presented the escalation menu (`invalid_id_menu_shown`) | `input_parser_node` to interpret the next turn's menu choice |

Mirrors the existing `clarification` tag. No new column; the `metadata` JSON
column already exists and is loaded by `load_conversation_history`.

## Entities (from spec)

### Customer identifier
- **Source**: `state["customer_identifier"]` = `{ "type": IdentifierType, "value": str }`.
- **Validity**: *format-valid* if the parser/regex produced a `{type, value}`; *found* if the
  post-fetch `data_completeness > 0.0`. A failure = format-valid-but-not-found, OR an
  unparseable value (handled by Feature 004 clarification, not counted here).

### Conversation session
- **Source**: the `session_id` and its `chat_history`. Holds the invalid-ID streak (via tagged
  turns), alongside Feature 004's clarification asks and Feature 005's memory.

### Failed-attempt count (`invalid_id_attempts`)
- **Lifecycle**: `0` → increments by 1 per invalid/not-found ID → reset to `0` on a successful
  lookup (streak broken) or a new `session_id`.
- **Drives**: message selection — `< max_attempts` (default 3) → retry message; `>= max_attempts`
  → escalation menu.

### Escalation menu
- **Composition**: ordered choices — (1) Re-enter your ID, (2) Talk to a human agent, and
  (3) Search by phone/email **iff** `m3_alt_lookup_enabled`.
- **Routing**: re-enter → normal pipeline; human → `escalation_node`; phone/email → alternate
  lookup (flagged).

### Alternate lookup detail
- **Source**: `state["alt_lookup_choice"]` — a phone or email captured after the customer picks
  choice 3 (only when alternate lookup is enabled). Out of critical-path scope; see research §5.

## State transitions (per conversation)

```text
attempts = trailing count of metadata.invalid_id assistant turns in chat_history

supplied ID, lookup FOUND      → reset streak (turn untagged), normal answer
supplied ID, lookup NOT FOUND:
    attempts + 1 <  max (3)    → retry message      (tag invalid_id)            [end turn]
    attempts + 1 >= max (3)    → escalation menu     (tag invalid_id + menu)     [end turn]

after escalation menu shown, next turn:
    customer sends a new ID    → re-enter pipeline (found→reset | not→menu again)
    customer asks for human    → escalation_needed=True → escalation_node
    customer gives phone/email → if alt_lookup_enabled: alternate lookup; else not offered
```

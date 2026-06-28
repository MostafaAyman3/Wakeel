# Phase 1 Data Model: Conversation Memory & Recall

No database schema changes and no new graph-state fields. Memory is the
existing conversation transcript, now actually used by the reply path.

## Existing data reused

### `conversations` table (no change)
Already stores every turn (`session_id`, `role`, `content`, `metadata`, `created_at`)
via `backend/repositories/conversations.py`:
- `load_conversation_history(session_id)` → ordered `[{role, content, metadata}]`, last ~10 turns.
- `append_conversation_turn(...)` → persists each user+assistant turn.

### Graph state (`M3State`) — already present
- `chat_history: list` — the loaded prior turns (`[{role, content, metadata}]`).
  Populated by the API endpoint when `session_id` is provided. **This is the memory.**
- The conversational reply nodes will now *read* `chat_history` (today only the
  router does).

## Conceptual entities (from spec)

| Entity | Representation | Notes |
|--------|----------------|-------|
| Conversation session | one `session_id` | unit of memory; isolates conversations (FR-003) |
| Conversation turn | one `conversations` row | ordered user/assistant message |
| Recalled fact / context | derived from the transcript at reply time | not stored separately (D1, transcript-based) |

## Behavior rules (validation)

- A reply node MUST only recall facts present in `chat_history` for the current
  `session_id`; never from another session, never invented (FR-003, FR-005).
- When `chat_history` is empty (no `session_id`), behavior is unchanged from today
  (graceful single-turn).
- On a restated fact, the later turn appears later in `chat_history`; the reply
  uses the most recent (FR-004).

## Window

- Bounded to the last ~10 turns provided by `load_conversation_history` (D4). This
  is a single existing constant, not a new field.

## Frontend session identity (FR-010)

- `session_id` is generated once and **persisted in `localStorage`**; reused on
  reload; replaced only by an explicit "New chat". (No backend/state change — the
  same id simply keeps loading the same transcript.)

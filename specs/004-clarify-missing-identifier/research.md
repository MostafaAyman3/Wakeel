# Phase 0 Research: Clarifying Follow-up for Missing Identifiers

All items below were resolvable from the existing M3 codebase and the clarified spec — no open `NEEDS CLARIFICATION` remain.

## D1 — Where to branch in the graph

**Decision**: Insert a conditional edge **after `input_parser`** (before `data_fetcher`). `input_parser` already determines whether a usable identifier exists; branch there into one of: `data_fetcher` (have identifier), `clarification_node` (missing, attempts remain), or `escalation` (attempts exhausted).

**Rationale**: `input_parser` is the single place that already resolves the identifier and today sets `escalation_needed=True, error="no_identifier_found"`. Branching here is minimal and keeps `data_fetcher`/`completeness` unchanged. The `customer_issue` and `hybrid` routes both pass through `input_parser`, so both are covered automatically.

**Alternatives considered**: (a) Branch in `completeness_check` — rejected: by then we've already run useless DB fetches with an empty identifier. (b) A new top-level router before `input_parser` — rejected: duplicates identifier logic the parser already does.

## D2 — Counting clarification attempts without new storage

**Decision**: Derive the attempt count from the already-loaded `chat_history` (present whenever the request carries `session_id`). Count prior assistant turns that were clarification questions (tagged via a stable marker, e.g. a `clarification` route/flag persisted in the conversation turn metadata, or a sentinel the node recognizes). If count ≥ 2 → escalate instead of asking again.

**Rationale**: The graph state is reconstructed per request; only `chat_history` persists across turns. Reusing it avoids a schema change (honors the "no migration" constraint) and is naturally session-scoped (FR-004, SC-005).

**Alternatives considered**: (a) New `clarification_attempts` column on `conversations` — rejected as unnecessary persistence for a count derivable from history. (b) In-memory per-session counter — rejected: not durable across worker restarts and harder to test.

## D3 — How the clarification reply is generated

**Decision**: A new `clarification_node` composes the follow-up using `llm_fast` (`gpt-4o-mini`) with a dedicated prompt, mirroring `greeting_node`'s structure (language-matched, short, friendly, static AR/EN fallback on LLM error). It names the exact reference needed based on the detected/likely issue (order vs invoice vs customer number) and asks for the type when a bare number is ambiguous (FR-011).

**Rationale**: Matches the user's request to use the "greeting agent" conversational style, reuses an established, never-raising node pattern, and keeps latency to a single fast-model call.

**Alternatives considered**: Pure static templates — rejected: less natural and weaker at matching how the customer phrased things; kept only as the fallback.

## D4 — Carrying the original question across turns

**Decision**: Rely on the existing conversation-aware `intent_router_node`, which already feeds the last 3 `chat_history` turns to keep the follow-up message on the original intent. When the customer replies with just a reference, the router keeps `customer_issue`, `input_parser` extracts the now-present reference, and the pipeline answers the original question.

**Rationale**: The deep test (`problem.md`, scenarios S12-t2 / S13-t2) already showed turn-2 answering correctly from session memory — the plumbing works; we only need to stop escalating on turn 1.

**Alternatives considered**: Persisting an explicit "pending question" slot — rejected as redundant given the router already inherits intent from history; may revisit if multi-slot collection is added later.

## D5 — Detecting "needs a reference" vs greeting / general knowledge

**Decision**: Clarification only triggers inside the CRM path (`customer_issue` / `hybrid`) because only that path runs `input_parser`. `greeting` and pure `general_knowledge` never reach the parser, so they can never produce a clarification prompt (SC-004) with no extra guarding.

**Rationale**: The intent router already separates these routes; the branch point in D1 is structurally unreachable for greeting/knowledge-only messages.

## D6 — Ambiguous reference type

**Decision**: When `input_parser` finds a value but cannot classify its type (no recognizable `ORD-/INV-/CUST-` prefix), set a distinct missing-slot reason ("ambiguous_type") so `clarification_node` asks "is this an order, invoice, or customer number?" (FR-011) rather than the generic "what's your number?".

**Rationale**: Distinguishes the two clarification shapes the spec calls out and avoids a dead-end on inputs like "1567".

## D7 — Preserving the review gate (Q3 / FR-013)

**Decision**: No change to `human_review_gate`. Clarification happens strictly *before* classification/response. Once the reference arrives and the request is classified as billing/refund, it flows through the unchanged gate to mandatory human review.

**Rationale**: Clarification only gathers data; it must not bypass safeguards.

## D8 — Privacy posture (Q1)

**Decision**: No ownership verification. Any valid reference returns its record, consistent with the current public `/support` endpoint. Recorded as a known limitation for production.

**Rationale**: Locked in clarification Q1; data is mock for the MVP/demo.

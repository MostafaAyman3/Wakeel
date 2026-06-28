# Phase 0 Research: Conversation Memory & Recall

All items resolvable from the existing code + the clarified spec. No open `NEEDS CLARIFICATION`.

## D1 — Memory mechanism (Q1)

**Decision**: Transcript-based. Include the recent conversation turns (already loaded into `state["chat_history"]` when a `session_id` is present) in the context of the node that writes the customer-facing reply, so the model can recall anything stated. No separate fact-extraction store.

**Rationale**: Locked in clarification Q1. Simplest and most robust; the history is already loaded for the router. Recall of arbitrary facts (name, subject) "for free" without brittle extraction rules.

**Alternatives**: Structured extraction (name→field) — rejected as more complex/brittle for the MVP. Hybrid — deferred; revisit only if transcript recall proves unreliable.

## D2 — Where the gap is

**Decision**: `greeting_node` is the conversational reply path but currently reads only `state["issue_description"]` (the current message). Feed it the recent `chat_history`. Likewise give `response_generator_node` access to `chat_history` (FR-006) so issue-path replies stay coherent.

**Rationale**: Confirmed by reading the nodes — history is loaded but unused in the reply. Minimal change: pass the recent turns into the existing LLM call.

## D3 — Routing personal/recall questions (fix M-2)

**Decision**: Update the intent router (`support_router.py` prompt + `intent_router_node`) so that questions answerable from the conversation itself — "what's my name?", "what did I say?", recalling personal info the customer already gave — route to the **greeting/conversational** path (which now has memory), not `customer_issue`. An actionable record request (order/invoice status) still wins and goes to the CRM path.

**Rationale**: `problem.md` M-2 showed "what is my name?" → `customer_issue` → clarification asks for an order number. These questions need no DB/knowledge — only the transcript. The router already runs first for every message and is conversation-aware, so it is the right place to make the distinction.

**Alternatives**: A dedicated "memory" node/route — rejected as unnecessary; the greeting/conversational node already produces a short LLM reply and just needs the transcript.

## D4 — Memory window size (deferred tuning, now fixed)

**Decision**: Use the recent window already provided — `load_conversation_history` returns the last ~10 turns; the conversational reply will use up to that many. Keep the existing constant; no new tuning surface for the MVP.

**Rationale**: 10 turns comfortably covers the name-recall and short multi-turn cases (SC-001/005) while bounding token cost. The spec flagged the exact window as tuning, not scope.

## D5 — Cross-session isolation (FR-003 / SC-002)

**Decision**: No change needed — history is loaded strictly by `session_id`, so facts never cross conversations. Keep it that way; add a test to guard it.

**Rationale**: Verified live (the baseline test already showed correct isolation). The risk is regression, covered by a test.

## D6 — Reload persistence (Q2 / FR-010)

**Decision**: Persist the `session_id` in the browser (`localStorage`) in `useM3Support.ts`: read it on mount, generate+store one if absent; "New chat" generates a fresh id and overwrites. Today the id lives in a `useRef` created per page load, so a reload starts a new conversation and loses memory.

**Rationale**: Smallest change that makes "the same conversation" survive a refresh (Q2) while staying session-scoped to the browser. No backend change.

**Alternatives**: Server-side per-customer session — rejected as cross-session scope expansion (out of scope).

## D7 — Never fabricate (FR-005)

**Decision**: The conversational reply prompt must instruct: answer recall questions only from the provided history; if the fact was never stated, say so and offer to note it — do not invent.

**Rationale**: Directly satisfies FR-005 / SC-003 and keeps memory trustworthy.

# Phase 0 Research: Invalid Identifier Retry & Guidance

This feature has no novel technology choices — it reuses the existing M3 LangGraph
pipeline, conversation storage, and escalation path. The "research" here is about
fitting the new behavior into the existing graph with minimal, regression-safe
changes. Each decision is recorded as Decision / Rationale / Alternatives.

## 1. Where to detect an "invalid or not found" identifier

**Decision**: Detect it **after `completeness_check`**, as the condition
`data_completeness == 0.0` AND `customer_identifier` has a non-empty `type` + `value`.
Route this branch to a new `invalid_id_node` instead of the current escalate path.

**Rationale**: The existing pipeline already produces exactly this signal.
`data_fetcher_node` returns all-`None` when the supplied identifier matches no record;
`data_completeness_node` then sets `data_completeness = 0.0` and `escalation_needed = True`.
Today `_escalation_router` sends that to `response_generator` → `escalation_node` (immediate
hand-off). Intercepting the branch where an identifier *was* supplied is a one-line
routing predicate and changes nothing for the missing-identifier case (which never reaches
`data_fetcher` — it goes to `clarification_node` from `input_parser`).

**Alternatives considered**:
- *Validate inside `data_fetcher_node`*: rejected — mixes "fetch" with "decide", and the
  found/not-found verdict already lives in `completeness_check`.
- *Format-validate in `input_parser_node`*: rejected as the primary mechanism — a well-formed
  but nonexistent ID (`ORD-999999`) is only knowable after a lookup. Format typos that the
  parser cannot extract already fall to Feature 004's clarification, which is correct.
  (We treat "parser produced an identifier, but lookup found nothing" as the failure here.)

## 2. How to count attempts per conversation

**Decision**: Recompute the count each turn by scanning the already-loaded `chat_history`
for prior assistant turns tagged `metadata.invalid_id == True`. The current failure is
`prior_count + 1`. Persist the tag from the API layer (`m3_support.py`) exactly as Feature
004 persists `metadata.clarification`.

**Rationale**: This is the established pattern (`clarification_node._count_prior_asks` +
`append_conversation_turn(assistant_metadata={"clarification": True})`). It needs **no new
DB column or migration**, is naturally per-session (history is loaded by `session_id`), and
resets for free on "New chat" (a new `session_id` has no history). It also survives page
reloads via Feature 005's persisted `session_id`.

**Alternatives considered**:
- *New `invalid_id_attempts` column on `conversations`*: rejected — extra migration and write
  path for a value derivable from history; inconsistent with the clarification pattern.
- *Counter in volatile graph state only*: rejected — graph state is per-invocation; it cannot
  persist across turns, which is the whole point.

## 3. Reset semantics

**Decision**: The count resets implicitly. Because it is derived from "consecutive invalid-ID
assistant turns", a **successful lookup** turn is not tagged `invalid_id`, so the next failure
counts the tagged turns since the last success. Implementation detail: count **trailing**
`invalid_id` turns (stop counting at the first non-`invalid_id` assistant turn) so a valid
lookup in between zeroes the streak. **Session end / "New chat"** resets by virtue of a fresh
`session_id`.

**Rationale**: Matches FR-009 (reset on valid ID) and FR-010 (reset on session end) without any
explicit reset code. "Trailing streak" counting also satisfies SC-003 (a success mid-way must
restart the next failure at attempt 1).

**Alternatives considered**:
- *Count all `invalid_id` turns ever in the session*: rejected — a success would not reset the
  streak, violating SC-003.

## 4. The escalation menu and how each choice is handled

**Decision**: On the 3rd failure, `invalid_id_node` emits the escalation menu as the turn's
`final_response` and tags the turn `metadata.invalid_id = True` **and** `metadata.invalid_id_menu = True`.
Choices are handled on the **next** turn:
- **Re-enter your ID** — no special handling: the customer simply sends another ID, which
  re-enters `input_parser → data_fetcher → completeness_check`. If found → success + reset; if
  not → `invalid_id_node` re-presents the menu (because the streak is now ≥ 3).
- **Talk to a human agent** — a small detector in `input_parser_node` recognizes a human-handoff
  request **when the prior assistant turn was tagged `invalid_id_menu`** and sets
  `escalation_needed = True`, routing to the existing `escalation_node`.
- **Search using phone/email instead** — gated by `m3_alt_lookup_enabled` (see §5).

**Rationale**: Reuses the existing turn-by-turn conversational model and the existing
`escalation_node`. No new "menu state machine" is needed; the `invalid_id_menu` tag on the prior
turn is enough context to interpret a one-word choice ("2", "human", "اتكلم مع موظف").

**Alternatives considered**:
- *Structured/clickable menu buttons in the frontend*: rejected for this iteration — the spec and
  the rest of M3 are text-conversational; buttons are a future UX enhancement, not required for
  the behavior. Keeping it text-only avoids a frontend change (FR-014).
- *Auto-hand-off on the 3rd failure (no menu)*: rejected — the user explicitly chose "keep asking
  + escalate with options", not silent hand-off.

## 5. "Search by phone/email" availability

**Decision**: Introduce `m3_alt_lookup_enabled` (default **False**). When False, the rendered menu
omits choice 3 (per FR-008) and shows only re-enter + human-agent. When True, choosing it collects
a phone/email and performs a contact-based lookup. Building the contact-lookup tool is scoped as a
**follow-up** task (the customers table carries phone/email, so it is feasible later) and is **not**
on the critical path for this feature.

**Rationale**: Honors FR-008's "omit if unavailable" rule and the spec assumption that alternate
lookup is a follow-up dependency, while leaving the canonical 3-option wording (FR-005) intact for
when the capability is enabled. Keeps this feature bounded and shippable now.

**Alternatives considered**:
- *Build phone/email lookup now*: deferred — it is a separable capability (new tool + parser slot)
  and would expand scope beyond the core retry/escalation behavior the user asked for.
- *Always show choice 3 but reply "not available yet" when picked*: rejected — FR-008 says omit it
  rather than offer a non-functional option.

## 6. Language adaptation of the messages

**Decision**: Store canonical English wording (FR-004/FR-005) plus static Arabic equivalents in the
node. Use the already-detected `state["language"]` to pick the variant. Optionally pass through
`llm_fast` for tone (as `clarification_node` does), with the static templates as the guaranteed
fallback on any LLM error.

**Rationale**: Matches FR-013 and the system's existing bilingual behavior; static fallbacks keep
the node non-raising and deterministic for tests (SC-006).

**Alternatives considered**:
- *LLM-only generation*: rejected — unnecessary latency/nondeterminism for fixed messages and a
  failure risk without a fallback.

## 7. Configuration

**Decision**: Add `m3_invalid_id_max_attempts: int = 3` and `m3_alt_lookup_enabled: bool = False`
to `backend/core/config.py`, alongside the existing `m3_clarification_max_attempts`.

**Rationale**: Makes the "3" threshold and the alternate-lookup gate tunable without code changes,
consistent with how Feature 004's limit is configured.

**Alternatives considered**: hard-coding 3 — rejected for consistency with existing configurable limits.

## Summary of resolved unknowns

| Topic | Resolution |
|-------|------------|
| Detection point | After `completeness_check`: `data_completeness==0.0` + identifier present |
| Attempt counting | Trailing `metadata.invalid_id` streak in `chat_history` (no migration) |
| Reset | Implicit via success-untagged turns + fresh `session_id` |
| Menu handling | Re-enter = natural turn; human = `escalation_node`; phone/email = flagged |
| Alt lookup | `m3_alt_lookup_enabled=False` default; choice omitted when off (FR-008) |
| Language | Static AR/EN templates, optional LLM tone pass with fallback |
| Threshold/flags | `m3_invalid_id_max_attempts=3`, `m3_alt_lookup_enabled=False` |

All NEEDS CLARIFICATION items are resolved. Ready for Phase 1.

# Feature Spec: Knowledge-Path & Router Fixes

**Status**: Decisions finalized (see
[wakeel_agent_instructions.md](../../wakeel_agent_instructions.md)). This spec
records them for traceability; options are NOT to be re-evaluated.

## Summary

Eight agreed fixes against live findings from
[system_analysis_and_solutions.md](../../docs/testing/system_analysis_and_solutions.md).
They restore the knowledge route (currently suppressed), correct bilingual
behaviour, add multi-turn routing, source citations, audit `issue_type`, latency,
and complete tax ingestion. Two are code-free (a test calibration and an ops
re-ingest).

## Actors

- **Customer** — public chat user (greeting / knowledge / issue / hybrid).
- **Support agent** — reviews held drafts (unchanged by these fixes).

## User Stories (work units = the 8 fixes)

### US1 — Knowledge answers reach the customer, in their language (Priority: P1) 🎯 MVP
Fixes 1 + 2 (tightly coupled, ship together). A `general_knowledge` answer is no
longer held by the review gate, and its language matches the customer's message.

**Independent test**: "What is your return policy?" → `review_required=false`, real
KB answer in `final_response`. "كم يستغرق الشحن؟" → Arabic answer.

### US2 — Multi-turn follow-ups keep route context (Priority: P2)
Fix 3 (conversation-aware router, last 3 turns; requires `session_id`).

**Independent test**: session of "where is my order ORD-2024-0001?" then "when will
it arrive?" → both `customer_issue`.

### US3 — Knowledge answers carry source citations (Priority: P3)
Fix 4 (return retrieved chunk doc names from Mini-RAG → `rag_sources`).

**Independent test**: a knowledge answer returns `rag_sources` with ≥1 doc name.

### US4 — Faster knowledge responses (Priority: P4)
Fix 6 (`llm_fast` for `general_knowledge`; only after US1 confirmed).

**Independent test**: knowledge-turn latency drops from the 11–17s range.

### US5 — Audit captures issue_type on escalation (Priority: P5)
Fix 5 (lightweight keyword classification on the no-data escalation branch).

**Independent test**: refund-on-missing-invoice escalation shows
`issue_type=refund_request` in the escalation summary.

### US6 — Calibration & ops (Priority: P5, no app-logic change)
Fix 7 ("ok"/acknowledgements → greeting; update tests + router examples) and
Fix 8 (complete tax ingestion: raise timeout / batch, re-run; `index/info/2 > 0`).

## Out of Scope (rejected options — see instructions §2)

S1-B, S1-C, S3-B, S3-C, S6-B, S6-C.

## Tests Requested

Yes — re-run `scripts/test_system_scenarios.py` and
`scripts/test_conversation_agent.py` after each milestone; compare to the baseline
(HIGH 58/65, MEDIUM 13/23, 10/21 turns green).

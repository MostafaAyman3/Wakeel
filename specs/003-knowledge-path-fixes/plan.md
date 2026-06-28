# Implementation Plan: Knowledge-Path & Router Fixes

**Branch/Feature**: `003-knowledge-path-fixes` | **Date**: 2026-06-24
**Source of truth (decisions)**: [wakeel_agent_instructions.md](../../wakeel_agent_instructions.md)
**Evidence**: [docs/testing/system_analysis_and_solutions.md](../../docs/testing/system_analysis_and_solutions.md),
[docs/testing/scenario_results.json](../../docs/testing/scenario_results.json)

> **Scope note**: This is a PLAN ONLY — no code is written here. Decisions are
> already finalized in `wakeel_agent_instructions.md`; this document turns them
> into a concrete, file-level, sequenced implementation plan with acceptance and
> verification per fix. Implementation happens later (e.g. via `/speckit-tasks`
> → `/speckit-implement`).

---

## Summary

Eight agreed fixes against the live findings. Two are code-free (a test
calibration and an ops re-ingest). The functional core is **Fix 1 + Fix 2**
(un-suppress knowledge answers + correct their language), which together move the
knowledge MVP from "broken for users" to "bilingual-functional". Then Fix 3
(multi-turn routing), Fix 4 (source citations), Fix 6 (latency), Fix 5 (audit),
Fix 7 (calibration), Fix 8 (tax ingestion).

Mapping to findings: Fix1↔P1, Fix2↔P2, Fix3↔P3, Fix4↔P5, Fix5↔P4, Fix6↔P7,
Fix7↔P6, Fix8↔env note.

## Technical Context

- **Backend/agents**: Python 3.10, FastAPI, LangGraph, LangChain (OpenAI
  `llm_fast`=gpt-4o-mini, `llm_primary`=gpt-4o). **Frontend**: Next.js 14 / TS.
- **RAG service**: Mini-RAG-APP-V1 (separate FastAPI on :8001, Supabase client).
- **No new dependencies, no DB migration** (the Supabase + Mini-RAG schema already
  exist and are reachable; support_kb ingested with 20 vectors).
- **Reuse, don't rebuild**: changes are surgical edits to existing nodes/prompts;
  Mini-RAG edits are limited to returning data it already computes.

## Constitution Check

`.specify/memory/constitution.md` is an unfilled template → no governance gates.
**PASS**. No new architectural complexity is introduced; all changes are localized.

---

## Work items (file-level, no code)

### Fix 1 — Bypass review gate for knowledge/greeting answers  (P1, priority 1)

- **File / function**: `agents/m3/nodes/human_review_node.py` → `human_review_gate`.
- **Change (conceptual)**: At the very start of the gate, short-circuit when
  `state["route"]` is `greeting` or `general_knowledge` → return
  `review_required = False` before any confidence/keyword evaluation. (`route` is
  already present in `M3State`, set by the intent router.) Option A from the
  instructions; B and C are out of scope.
- **Why it's safe**: pure-knowledge answers are grounded in the curated KB and make
  no account-specific or financial commitment; `hybrid` and `customer_issue` keep
  the full gate (so refund/billing on a real account is still reviewed).
- **Depends on**: nothing. Ship together with Fix 2.
- **Acceptance**: every `general_knowledge` turn → `review_required=False` and the
  real KB answer appears in `final_response` (not the hold message).
- **Risk / rollback**: low; single-node guard, trivially revertible.

### Fix 2 — Language detection on the RAG/knowledge path  (P2, priority 1)

- **Part A — file / function**: `agents/m3/nodes/intent_router_node.py` →
  `route_intent`. Detect the message language (reuse the Arabic-range check used in
  `greeting_node`) and include `language` in the node's returned state update, so
  every downstream path inherits it (router runs first for every message).
- **Part B (guard) — file / function**:
  `agents/m3/nodes/response_generator_node.py` → `generate_response` /
  `_build_prompt_data`. When `language == "auto"` (or empty), re-detect from the
  customer message before building the prompt, so a future path that bypasses the
  router cannot silently regress to English.
- **Depends on**: pairs with Fix 1 (same failing turns). Do not ship one without
  the other.
- **Acceptance**: Arabic knowledge question → Arabic answer; any legitimately held
  message (e.g. hybrid refund) is Arabic for Arabic input.
- **Risk**: low. Note: the API review-hold message in
  `backend/api/v1/m3_support.py` already reads `result["language"]`; once the
  router sets it, that message is language-correct too — verify, no change expected.

### Fix 3 — Conversation-aware router  (P3, priority 2)

- **Files / functions**:
  - `agents/m3/nodes/intent_router_node.py` → `route_intent`: read
    `state["chat_history"]` and use the **last 3 turns** (hard cap N=3, default 3,
    not left configurable without that default).
  - `agents/prompts/support_router.py`: add a short "recent conversation" block to
    the prompt so follow-ups inherit context.
  - `backend/api/v1/m3_support.py`: confirm `chat_history` (already loaded for
    session memory) is placed in the initial state the router can read (it already
    sets `initial_state["chat_history"]` when `session_id` is present — verify the
    router consumes it).
- **Constraint**: cap at 3 turns. **Known limitation (document, not a bug)**:
  without `session_id` the router stays single-turn.
- **Depends on**: session memory working (now that the DB is reachable).
- **Acceptance**: two-turn session — "where is my order ORD-2024-0001?" then
  "when will it arrive?" → both route `customer_issue`.
- **Risk**: medium — larger router prompt; mitigate by capping at 3 turns and
  trimming each turn's text.

### Fix 4 — Return real sources from Mini-RAG  (P5, priority 3)

- **Primary (Option A) — files / functions**:
  - `MIni-RAG-APP-V1/src/controllers/NLPController.py` → `answer_rag_question`:
    also return the retrieved chunks' document names (already retrieved internally
    for the prompt).
  - `MIni-RAG-APP-V1/src/routes/nlp.py` → `/index/answer/{project_id}`: include
    those source names in the JSON response.
  - `backend/services/rag_client.py` → `rag_answer`: map the returned source names
    into the `sources` field (the `rag_node`/API already surface `rag_sources`).
- **Fallback (Option B)** — if modifying Mini-RAG is too costly: in
  `agents/m3/nodes/rag_node.py`, call Mini-RAG `/index/search/{project_id}` in
  parallel with `/answer` and derive sources from its `results`, leaving Mini-RAG
  untouched (accept one extra HTTP call).
- **Acceptance**: a knowledge answer returns `rag_sources` with ≥1 document name
  (e.g. `["return_policy.txt"]`); UI Sources line appears.
- **Risk**: low (A) / latency (B). Prefer A; document the document-name source
  (asset filename) used for citation.

### Fix 5 — Preserve `issue_type` on the escalation path  (P4, priority 5, parallelizable)

- **File / function**: the no-data escalation branch — `agents/m3/nodes/
  escalation_node.py` (and/or the completeness→escalation hop in
  `agents/m3/graphs/m3_graph.py`). Add a lightweight keyword-based classification
  to set `issue_type` (e.g. refund/billing/shipping/status) before escalating, so
  it lands in the escalation summary + audit.
- **Acceptance**: Khaled's escalation scenario shows `issue_type=refund_request`
  in the escalation summary.
- **Risk**: very low; internal/audit only, zero customer-facing impact.

### Fix 6 — Faster model for pure knowledge responses  (P7, priority 4)

- **File / function**: `agents/m3/nodes/response_generator_node.py` →
  `generate_response`. When `route == general_knowledge`, use `llm_fast`
  (gpt-4o-mini) instead of `llm_primary` (gpt-4o); the answer is already grounded
  by Mini-RAG, so this step only does language/formatting polish.
- **Hard ordering**: implement **only after Fix 1 + Fix 2 are confirmed working**.
  Option B (skip response_generator) and C (caching) are out of scope.
- **Acceptance**: knowledge-turn latency drops meaningfully from the 11–17s range.
- **Risk**: low; minor quality delta on already-grounded text.

### Fix 7 — "ok"/acknowledgement calibration  (P6, no code change in app logic)

- **Files**:
  - `agents/prompts/support_router.py`: list short acknowledgements ("ok",
    "تمام", "👍") explicitly as `greeting` examples to stabilize intent.
  - `scripts/test_system_scenarios.py` (and `scripts/test_conversation_agent.py`):
    change the expected route for "ok" from `customer_issue` to `greeting`.
- **Acceptance**: "ok" → `greeting`; the scenario suite no longer flags it.
- **Bundle**: include in the same commit as Fix 1.

### Fix 8 — Complete tax knowledge ingestion  (env, no code change)

- **Action**: raise the ingest client timeout to 600s **or** push the tax
  collection in batches, then re-run `python scripts/ingest_mini_rag.py --only tax`.
- **Acceptance**: `GET /api/v1/nlp/index/info/2` returns vector count > 0.
- **Risk**: none (operational); independent of all other fixes.

---

## Sequencing & milestones (from instructions §3)

1. **Milestone A (knowledge MVP)** — Fix 1 + Fix 2 together (+ Fix 7 calibration in
   the same commit). Ship only as a pair.
2. **Milestone B (continuity)** — Fix 3.
3. **Milestone C (trust)** — Fix 4.
4. **Milestone D (latency)** — Fix 6 (only after A is confirmed).
5. **Anytime / parallel** — Fix 5 (audit), Fix 8 (ops).

## Verification strategy

- Re-run `python scripts/test_system_scenarios.py` after each milestone; compare
  against `docs/testing/scenario_results.json` (baseline: HIGH 58/65, MEDIUM 13/23,
  10/21 turns green).
- Re-run `python scripts/test_conversation_agent.py` to confirm greeting route is
  unregressed.
- Per-fix acceptance checks listed above.

## Expected outcome (from instructions §4)

| Metric | Before | After all fixes |
|--------|--------|-----------------|
| Knowledge turns passing | 0/6 | 6/6 |
| Arabic knowledge answers in Arabic | 0/3 | 3/3 |
| Multi-turn follow-up routing | broken | correct (with session_id) |
| `rag_sources` populated | never | every knowledge answer |
| Fully green turns | 10/21 | ~19–20/21 |

## Out of scope (rejected — instructions §2)

S1-B (confidence boost), S1-C (graph terminal edge), S3-B (sticky route), S3-C
(persist ID in session), S6-B (skip response_generator), S6-C (answer caching).

## Risks & mitigations

- **Router prompt growth (Fix 3)** → cap at 3 trimmed turns.
- **Mini-RAG edits (Fix 4)** → small, additive (return already-retrieved names);
  fallback B avoids touching Mini-RAG if needed.
- **Latency change masking quality (Fix 6)** → gated behind Fix 1+2 confirmation and
  re-tested via the scenario suite.
- **Hot-reload**: backend and Mini-RAG run without `--reload`; each milestone needs
  a service restart before re-testing (operational reminder).

## Files touched (summary)

```
agents/m3/nodes/human_review_node.py          (Fix 1)
agents/m3/nodes/intent_router_node.py         (Fix 2A, Fix 3)
agents/m3/nodes/response_generator_node.py    (Fix 2B, Fix 6)
agents/prompts/support_router.py              (Fix 3, Fix 7)
agents/m3/nodes/escalation_node.py            (Fix 5)
agents/m3/graphs/m3_graph.py                  (Fix 5, if hop change needed)
backend/api/v1/m3_support.py                  (Fix 3 verify, Fix 2 verify)
backend/services/rag_client.py                (Fix 4)
agents/m3/nodes/rag_node.py                   (Fix 4 fallback B only)
MIni-RAG-APP-V1/src/controllers/NLPController.py  (Fix 4 primary)
MIni-RAG-APP-V1/src/routes/nlp.py             (Fix 4 primary)
scripts/test_system_scenarios.py              (Fix 7)
scripts/test_conversation_agent.py            (Fix 7)
scripts/ingest_mini_rag.py                    (Fix 8 ops, optional timeout bump)
```

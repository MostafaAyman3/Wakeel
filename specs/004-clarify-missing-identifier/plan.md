# Implementation Plan: Clarifying Follow-up for Missing Identifiers

**Branch**: `004-clarify-missing-identifier` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-clarify-missing-identifier/spec.md`

## Summary

When the support assistant (M3) receives a record-dependent question (order / invoice / shipping / account) that lacks a usable reference, it currently sets `escalation_needed=True` in `input_parser` and hands the case to a human. This feature replaces that premature hand-off with a **conversational clarification turn**: the assistant asks for the exact reference it needs, ends the turn without escalating, and — on the customer's next message (tied together by the existing `session_id` conversation memory) — combines the supplied reference with the original question to fetch data and answer.

Technical approach: add a lightweight **ClarificationNode** and a small conditional branch right after `input_parser`. Missing identifier + attempts remaining → clarification reply (reuses the greeting/`llm_fast` conversational style). Identifier present → existing pipeline unchanged. Attempts exhausted (2) or topic clearly un-resolvable → existing escalation path. Clarification attempt count is **derived from `chat_history`** (no new persistence/schema). Sensitive types (billing/refund) keep the existing mandatory human-review gate untouched (FR-013).

## Technical Context

**Language/Version**: Python 3.11 (agents + FastAPI backend); TypeScript / Next.js 14 frontend (no change required for the core; optional chat-state polish only).

**Primary Dependencies**: LangGraph (StateGraph), LangChain + OpenAI `gpt-4o-mini` (`llm_fast`) for the clarification/greeting reply, FastAPI, SQLAlchemy async. RAG path (Mini-RAG service) is unaffected.

**Storage**: Supabase PostgreSQL. Session memory uses the existing `conversations` table via `backend/repositories/conversations.py` (`load_conversation_history` / `append_conversation_turn`). **No migration required** — the clarification-attempt count is computed from the loaded `chat_history`.

**Testing**: Scenario scripts in `scripts/` (pattern: `scripts/test_m3_*.py`) plus a new `scripts/test_clarification.py`; the live deep-test harness used for `problem.md`.

**Target Platform**: Local/dev server (uvicorn :8000) + Next.js (:3000) + Mini-RAG (:8001).

**Project Type**: Web (FastAPI backend agent graph + Next.js frontend). This feature is backend-agent-focused.

**Performance Goals**: A clarifying reply returns in roughly the same time as a greeting (single `llm_fast` call, typically a few seconds); no extra DB round-trips beyond the session-history load already performed.

**Constraints**: Reuse the existing graph, intent router, and `session_id` memory. Do not weaken the human-review gate (FR-013). No ownership verification (Q1 decision; documented privacy limitation). Clarification limited to 2 attempts (Q2).

**Scale/Scope**: Demo/MVP volume; correctness and conversation coherence over throughput.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution (`.specify/memory/constitution.md`) is the **unpopulated template** — it defines no ratified principles or constraints. There are therefore no explicit gates to satisfy.

Applied general engineering gates (self-imposed, consistent with the existing M3 code):
- **Simplicity**: reuse existing nodes/patterns; add one node + one conditional edge; no new storage. ✅
- **Graceful degradation**: clarification path never raises; falls back to escalation. ✅
- **No regression**: identifier-present and greeting/general-knowledge flows are untouched; review gate preserved. ✅

**Result**: PASS (no constitution violations; no entries needed in Complexity Tracking).

## Project Structure

### Documentation (this feature)

```text
specs/004-clarify-missing-identifier/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── support-endpoint.md   # /support request/response delta
└── checklists/
    └── requirements.md  # from /speckit-specify
```

### Source Code (repository root)

```text
agents/m3/
├── graphs/
│   └── m3_graph.py                 # MODIFY: add clarification node + conditional branch after input_parser
├── nodes/
│   ├── input_parser_node.py        # MODIFY: flag missing identifier as clarification (not escalation) + detect ambiguous-type
│   ├── clarification_node.py       # NEW: compose the AR/EN follow-up question; count attempts from chat_history
│   ├── intent_router_node.py       # (unchanged) already conversation-aware via chat_history
│   ├── greeting_node.py            # (reference) conversational reply pattern reused
│   ├── data_fetcher_node.py        # (unchanged)
│   ├── data_completeness_node.py   # MODIFY (optional, ISSUE-2): graceful "not found" wording when a supplied ref matches nothing
│   ├── response_generator_node.py  # (unchanged) review gate stays intact
│   └── human_review_node.py        # (unchanged) FR-013 preserved
├── schemas/
│   └── m3_state.py                 # MODIFY: add clarification fields (see data-model.md)
└── prompts/
    └── clarification_agent.py      # NEW: system prompt for the clarification reply

backend/
├── api/v1/m3_support.py            # MODIFY (small): surface `clarification_pending` in the response so the UI/turn knows it's a question, not a final answer
└── repositories/conversations.py   # (unchanged) reused for attempt counting

scripts/
└── test_clarification.py           # NEW: scenario tests for missing-id / ambiguous / multi-turn / exhausted attempts
```

**Structure Decision**: Single backend agent-graph change. The feature lives inside the existing M3 LangGraph; the only new files are one node, one prompt, and one test. Frontend needs no functional change (the clarifying question renders as a normal assistant chat turn); an optional cosmetic "awaiting your reply" hint is out of scope for the core.

## Complexity Tracking

> No constitution violations — section intentionally empty.

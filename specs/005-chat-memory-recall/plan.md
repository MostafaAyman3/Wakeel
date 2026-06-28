# Implementation Plan: Conversation Memory & Recall

**Branch**: `005-chat-memory-recall` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-chat-memory-recall/spec.md`

## Summary

The assistant forgets facts said earlier in the same chat. Two concrete gaps were observed (see `problem.md`):

1. **No recall** — the conversational reply path (`greeting_node`) uses only the *current* message; it never sees the conversation history, so "my name is Kareem" → "what's my name?" can't be answered.
2. **Mis-route** — "what is my name?" is classified as `customer_issue`, reaches the record-lookup path, and (since Feature 004) asks for an order number instead of recalling.

Approach (per clarifications): **transcript-based** memory — feed the recent conversation turns into the conversational reply path so the model recalls anything said; and teach the **intent router** to send "questions answerable from the conversation itself" (name, what-did-I-say, personal recall) to that path instead of the CRM path. The conversation history is already loaded from the `conversations` table when a `session_id` is present — the missing piece is *using* it in the reply nodes and routing correctly. Frontend persists the `session_id` in browser storage so memory survives a page reload (FR-010).

## Technical Context

**Language/Version**: Python 3.11 (agents + FastAPI backend); TypeScript / Next.js 14 (frontend — small change for reload persistence).

**Primary Dependencies**: LangGraph, LangChain + OpenAI `gpt-4o-mini` (`llm_fast`, used by the greeting/conversational reply), FastAPI. Supabase `conversations` table for turn storage.

**Storage**: Supabase PostgreSQL `conversations` table via `backend/repositories/conversations.py` (`load_conversation_history` loads the last ~10 turns; `append_conversation_turn` persists each turn). **No migration required** — memory is the transcript already stored there.

**Testing**: New `scripts/test_memory.py` (recall, cross-session isolation, update, unknown, cross-path) + the live deep-test from `problem.md`.

**Target Platform**: uvicorn :8000 + Next.js :3000 (+ Mini-RAG :8001 unaffected).

**Project Type**: Web (FastAPI agent graph + Next.js). This feature touches the backend conversational path/router and a small frontend session-id change.

**Performance Goals**: No extra DB round-trips beyond the history load already performed; recall adds only a few hundred tokens of recent transcript to one existing LLM call.

**Constraints**: Transcript-based (Q1) — no separate fact-extraction store. Session-scoped; the conversation id persists across reloads in the same browser (Q2). Must not regress Feature 004 (clarification) or the record-lookup paths.

**Scale/Scope**: Demo/MVP; correctness and conversational coherence over throughput.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution (`.specify/memory/constitution.md`) is the unpopulated template — no ratified principles/gates. Self-imposed engineering gates:
- **Simplicity**: reuse the already-loaded `chat_history`; no new storage, no fact-extraction subsystem. ✅
- **No regression**: record-lookup, clarification (Feature 004), RAG, and review gate behavior unchanged; only the conversational path gains memory and the router gains one route distinction. ✅
- **Graceful degradation**: with no `session_id` (no history) the assistant behaves as today. ✅

**Result**: PASS (no violations; Complexity Tracking empty).

## Project Structure

### Documentation (this feature)

```text
specs/005-chat-memory-recall/
├── plan.md            # This file
├── research.md        # Phase 0
├── data-model.md      # Phase 1
├── quickstart.md      # Phase 1
├── contracts/
│   └── memory-behavior.md
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
agents/m3/
├── nodes/
│   ├── intent_router_node.py     # MODIFY: route conversation/personal-recall questions to the conversational path (fix M-2)
│   ├── greeting_node.py          # MODIFY: include recent chat_history so it can recall earlier facts
│   └── response_generator_node.py # MODIFY (FR-006): give the issue-path reply access to chat_history too
└── prompts/
    ├── support_router.py         # MODIFY: define "answerable from the conversation" → greeting/conversational route
    └── greeting_agent.py         # MODIFY: instruct the reply to use the provided history to recall; never invent

backend/
└── repositories/conversations.py # (reuse) already loads/persists turns; confirm window adequate

frontend/
└── hooks/useM3Support.ts         # MODIFY: persist session_id in localStorage (survive reload); "New chat" issues a new id

scripts/
└── test_memory.py                # NEW: recall / isolation / update / unknown / cross-path scenarios
```

**Structure Decision**: Backend-centric (router + conversational reply nodes use the existing transcript) plus a small frontend change (persist the session id). No new services, no schema changes.

## Complexity Tracking

> No constitution violations — section intentionally empty.

# Implementation Plan: Conversation Agent (Small-Talk Route)

**Branch**: `002-conversation-agent` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-conversation-agent/spec.md`

## Summary

Add a fourth `greeting` route to the existing Unified Support Chatbot intent
router (feature 001). Social/small-talk messages ("Hi", "how are you", "thanks",
and Arabic equivalents) are answered directly by a lightweight, friendly LLM
response — no RAG call, no CRM/DB lookup, no human-review gate. Knowledge
questions still route to RAG; issues/complaints still route to the CRM agent.
The router stays conservative: any actionable request or low confidence falls
back to the existing `customer_issue` path so no real support need is dropped.

Technical approach: extend the router's allowed labels + prompt, add a tiny
`greeting_node` that generates a short friendly reply via the fast LLM, add one
conditional edge in the LangGraph so `greeting → END` (through the existing
finalization), widen the `route` Literal + API/UI enums, and ensure the review
gate is bypassed for greetings.

## Technical Context

**Language/Version**: Python 3.10 (backend/agents), TypeScript / Next.js 14 (frontend)

**Primary Dependencies**: FastAPI, LangGraph, LangChain (OpenAI `llm_fast` =
gpt-4o-mini), Pydantic; React/Next.js for the chat UI. No new dependencies.

**Storage**: Reuses the existing `conversations` table (session memory). No new
tables, no migration.

**Testing**: Standalone Python script under `scripts/` (consistent with feature
001's `test_unified_support.py` / node unit checks); manual UI pass.

**Target Platform**: Local dev — backend `:8000`, frontend `:3000`, Mini-RAG
`:8001` (greeting route does not depend on Mini-RAG).

**Project Type**: Web application (backend + agents + frontend).

**Performance Goals**: Greeting replies return faster than data-backed answers
(single fast-LLM call, no RAG/DB round-trips).

**Constraints**: Bilingual AR/EN only; reply is short (1–2 sentences);
greeting must never expose data, sources, held drafts, or escalations.

**Scale/Scope**: Small extension — ~1 new node, ~1 new prompt, edits to router
prompt/node, graph, state, API, and one frontend badge map.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution (`.specify/memory/constitution.md`) is an unfilled
template with no ratified principles, so there are no governance gates to
violate. **PASS** (no constraints). This feature also introduces no new
architectural complexity — it reuses the existing graph, endpoint, response
mechanism, and memory.

## Project Structure

### Documentation (this feature)

```text
specs/002-conversation-agent/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (router contract, API delta)
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
agents/
├── prompts/
│   ├── support_router.py          # MOD: add `greeting` route + rules
│   └── greeting_agent.py          # NEW: friendly small-talk system prompt
├── m3/
│   ├── nodes/
│   │   ├── intent_router_node.py  # MOD: allow `greeting` label
│   │   ├── greeting_node.py       # NEW: generate friendly reply (llm_fast)
│   │   └── human_review_node.py   # (unchanged; greeting bypasses gate)
│   ├── schemas/
│   │   └── m3_state.py            # MOD: route Literal gains "greeting"
│   └── graphs/
│       └── m3_graph.py            # MOD: route greeting → greeting_node → END

backend/
└── api/v1/
    └── m3_support.py              # MOD: `route` may be "greeting" (doc only)

frontend/
├── types/m3.ts                    # MOD: RouteType gains "greeting"
└── components/chat/MessageBubble.tsx  # MOD: badge label+color for greeting

scripts/
└── test_conversation_agent.py     # NEW: route + reply assertions
```

**Structure Decision**: Web application reusing feature 001's structure. The
greeting route is the shortest path through the graph: `intent_router →
greeting_node → END`. It deliberately skips `rag_node`, the CRM pipeline
(`input_parser → … → context_builder`), and the `human_review_gate`.

## Complexity Tracking

No constitution violations; no new projects, patterns, or dependencies. Table
intentionally omitted.

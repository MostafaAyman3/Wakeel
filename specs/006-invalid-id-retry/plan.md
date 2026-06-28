# Implementation Plan: Invalid Identifier Retry & Guidance

**Branch**: `006-invalid-id-retry` | **Date**: 2026-06-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-invalid-id-retry/spec.md`

## Summary

When a customer supplies a record-lookup identifier (order / invoice / shipment / tracking / customer ID) that is **invalid or not found**, the M3 assistant currently escalates immediately (the no-data branch sets `escalation_needed=True` and hands off). This feature inserts a **bounded, friendly retry loop with an explicit exit**:

1. Count invalid-ID attempts **per conversation** (derived from `chat_history` metadata — the same pattern Feature 004 uses to count clarification asks; no new DB column).
2. On the **1st and 2nd** failure → reply with the friendly retry message and end the turn (no escalation).
3. On the **3rd** failure → present the escalation menu (re-enter ID / talk to a human agent / search by phone-email) and end the turn.
4. **Reset** the count when a valid ID is found or the conversation resets.

**Where it plugs in**: the "supplied identifier but no data" condition is exactly `data_completeness == 0.0` with a non-empty `customer_identifier` after `completeness_check`. A new `invalid_id_node` intercepts that branch *before* the existing escalation, so the immediate-handoff behavior is replaced by the retry loop. The "talk to a human" menu choice reuses the existing `escalation_node`; "re-enter" is the natural next turn (a new ID re-enters the pipeline); "search by phone/email" is gated behind an alternate-lookup capability flag (off by default per spec FR-008).

## Technical Context

**Language/Version**: Python 3.11 (LangGraph agent + FastAPI backend). No frontend change required — the retry/menu messages render as ordinary assistant replies.

**Primary Dependencies**: LangGraph (`StateGraph`), LangChain + OpenAI `gpt-4o-mini` (`llm_fast`, used only to language-adapt the canned messages if desired; static AR/EN fallbacks otherwise), FastAPI. Supabase `conversations` table for per-session turn storage and metadata tagging.

**Storage**: Supabase PostgreSQL `conversations` table via `backend/repositories/conversations.py`. The attempt count is **not** a new column — it is recomputed each turn by counting prior assistant turns tagged `metadata.invalid_id = True` (mirrors `metadata.clarification`). **No migration required.**

**Testing**: New `scripts/test_invalid_id.py` covering: 1st/2nd retry message, 3rd escalation menu, reset on valid ID, cross-conversation isolation, language adaptation, and "no regression" for the missing-identifier (Feature 004) and valid-ID paths.

**Target Platform**: uvicorn :8000 (backend) + existing Next.js :3000 frontend (unchanged) + Mini-RAG :8001 (unaffected).

**Project Type**: Web (FastAPI agent graph + Next.js). This feature is **backend-only** — one new graph node, one routing change, a few new state fields, and one API metadata-tagging line.

**Performance Goals**: No extra DB round-trips beyond the history load already performed. Attempt counting is an in-memory scan of the already-loaded `chat_history`. The retry/menu messages use static templates (optional one `llm_fast` call for tone, consistent with the clarification node).

**Constraints**: Must not regress Feature 004 (missing-identifier clarification), Feature 005 (memory recall), RAG/knowledge answers, valid-ID lookups, or the human-review gate (FR-014). The escalation-menu choice "search by phone/email" must be **omitted** when alternate lookup is unavailable (FR-008).

**Scale/Scope**: Demo/MVP; correctness and conversational coherence over throughput.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution (`.specify/memory/constitution.md`) is the unpopulated template — no ratified principles/gates. Self-imposed engineering gates (consistent with Features 004/005):

- **Simplicity**: reuse the already-loaded `chat_history` for counting (no new column, no new datastore); reuse the existing `escalation_node` for the human-agent choice; one new node + one routing edge. ✅
- **No regression**: routing, clarification (004), memory (005), RAG, valid-ID lookups, and the review gate are untouched; only the *not-found-with-identifier* branch changes from "escalate now" to "retry then menu". ✅
- **Graceful degradation**: any LLM failure falls back to static AR/EN message templates; alternate-lookup-off simply trims the menu to two choices. ✅

**Result**: PASS (no violations; Complexity Tracking empty).

## Project Structure

### Documentation (this feature)

```text
specs/006-invalid-id-retry/
├── plan.md            # This file
├── research.md        # Phase 0 — decisions (insertion point, counting, menu handling, alt-lookup flag)
├── data-model.md      # Phase 1 — state fields, metadata, entities
├── quickstart.md      # Phase 1 — runnable validation scenarios
├── contracts/
│   └── invalid-id-behavior.md   # node I/O contract + message wording + routing table
└── checklists/
    └── requirements.md          # spec quality checklist (from /speckit-specify)
```

### Source Code (repository root)

```text
agents/m3/
├── nodes/
│   ├── invalid_id_node.py        # NEW: count attempts → retry message (1–2) | escalation menu (3+)
│   └── input_parser_node.py      # MODIFY (small): when the prior turn was the escalation menu, detect a
│                                  #         menu choice (human / phone-email) before normal parsing
├── graphs/
│   └── m3_graph.py               # MODIFY: route "not-found + identifier present" → invalid_id_node;
│                                  #         add menu-choice detection → escalation_node (human-agent)
└── schemas/
    └── m3_state.py               # MODIFY: add invalid_id_attempts, invalid_id_pending,
                                   #         invalid_id_menu_shown, alt_lookup_choice; seed defaults

agents/prompts/
└── invalid_id_agent.py           # NEW (optional): tone/language adaptation; static AR/EN fallbacks live in the node

backend/
├── api/v1/m3_support.py          # MODIFY (1 line): tag assistant turn metadata.invalid_id when invalid_id_pending
└── core/config.py                # MODIFY: add m3_invalid_id_max_attempts (=3) and m3_alt_lookup_enabled (=False)

scripts/
└── test_invalid_id.py            # NEW: retry / menu / reset / isolation / language / no-regression scenarios
```

**Structure Decision**: Backend-centric, mirroring Feature 004's clarification design. The new `invalid_id_node` is the symmetric counterpart to `clarification_node`: 004 handles *missing* references (pre-fetch), 006 handles *supplied-but-not-found* references (post-fetch). Both count attempts from `chat_history` metadata and both can terminate the turn with a question/message or route to `escalation_node`. No schema changes, no new services, no frontend change.

## Complexity Tracking

> No constitution violations — section intentionally empty.

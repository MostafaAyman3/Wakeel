# Wakeel Chatbot — Agreed Fixes for Implementation Planning

**Project**: Wakeel Unified Support Chatbot  
**Document purpose**: Decisions finalized after review — hand this to the implementation-planning agent.  
**Scope**: This document lists what to implement, what option to pick where there are alternatives, what NOT to implement, and hard constraints. The agent's job is to build a detailed implementation plan from these decisions — not to re-evaluate them.

---

## Section 1 — What to implement (with chosen options)

### Fix 1 — Bypass human-review gate for knowledge answers (was P1 / S1)

**Option chosen: A**  
In `human_review_gate`, add a short-circuit before the confidence/keyword checks:

```
if route in {"greeting", "general_knowledge"}:
    return {"review_required": False}
```

This is the only change needed for this fix. Options B and C are rejected (see Section 2).

**Verification target**: All `general_knowledge` turns must return `review_required=False` and show the real KB answer in `final_response`, not a hold message.

---

### Fix 2 — Language detection on the RAG / knowledge path (was P2 / S2)

**Two-part fix, both parts required:**

**Part A** — Add language detection inside `intent_router_node`.  
The router already reads the message; it should detect language there (reusing the Arabic-range check already used in `greeting_node`) and write `language` to state. This means every downstream path — including the knowledge path — inherits the detected language automatically.

**Part B (guard)** — In `response_generator`, treat `language == "auto"` as a signal to re-detect language from the customer message before building the prompt.  
This is defensive insurance so any future new path that somehow misses the router cannot silently regress language back to English.

**Verification target**: An Arabic knowledge question must return an Arabic answer. A held message (when it does legitimately occur, e.g. hybrid refund) must also appear in Arabic for Arabic input.

---

### Fix 3 — Conversation-aware router (was P3 / S3)

**Option chosen: A**  
Pass `chat_history` to the router (`route_intent`). Include the last **3 turns** (hard cap — N=3) as a "recent conversation" block in the router prompt so follow-up questions inherit context.

**Hard constraint on N**: Cap at 3 turns. Do not leave N configurable without a default — the default must be 3.

**Note**: This fix requires `session_id` to be present for the router to load history. If `session_id` is absent, the router remains single-turn (current behavior). Document this as a known limitation, not a bug.

Options B and C are rejected (see Section 2).

**Verification target**: A two-turn session — "where is my order ORD-2024-0001?" followed by "when will it arrive?" — must both route as `customer_issue`.

---

### Fix 4 — Return real sources from Mini-RAG (was P5 / S4)

**Option chosen: A as primary, B as fallback**  
Extend Mini-RAG's `answer_rag_question` and the `/answer` route to return the retrieved chunk document names alongside the answer. The backend's `rag_client` then maps them to `rag_sources`.

**Fallback condition**: If Mini-RAG is owned by a separate team and modifying it requires significant coordination overhead, use Option B instead — call Mini-RAG's `/search/{project_id}` in parallel with `/answer` in `rag_node` to get sources without touching Mini-RAG internals. Accept the extra latency cost of one additional HTTP call in that case.

Option C (accept empty sources) is rejected.

**Verification target**: A knowledge answer must return `rag_sources` with at least one document name (e.g. `["return_policy.txt"]`). The UI Sources line must appear.

---

### Fix 5 — Preserve issue_type on escalation path (was P4 / S5)

On the no-data escalation branch (the path that currently skips `IssueClassifier`), add a lightweight keyword-based classification step before escalating so that `issue_type` is captured in the escalation summary and audit trail.

This is a low-effort internal fix. It has zero customer-facing impact.

**Verification target**: Khaled's escalation scenario must show `issue_type=refund_request` in the escalation summary.

---

### Fix 6 — Use faster model for pure knowledge responses (was P7 / S6)

**Option chosen: A only**  
For `route=general_knowledge`, use `llm_fast` (gpt-4o-mini) in `response_generator` instead of `llm_primary` (gpt-4o).  
The answer is already grounded by Mini-RAG; the response_generator step is only adding language mirroring and light formatting polish, which does not require the heavier model.

**This fix must be implemented after Fixes 1 and 2 are confirmed working.**  
Option B (skip response_generator entirely) is rejected. Option C (caching) is rejected (see Section 2).

**Verification target**: Knowledge turn latency should drop meaningfully from the current 11–17s range.

---

### Fix 7 — Test calibration for "ok" classification (was P6 / S7)

**No code change.** Update the test expectation: short acknowledgements like "ok", "تمام", "👍" should be expected as `greeting`, not `customer_issue`. The current system behavior is correct; the test expectation was wrong.

Update the router prompt to explicitly list these short acknowledgements as examples of `greeting` to make the intent stable.

---

### Fix 8 — Complete tax knowledge ingestion (was environment note / S8)

**No code change.** Operational fix only:  
Raise the ingest client timeout to 600s, or split the tax collection push into batches, then re-run `scripts/ingest_mini_rag.py --only tax`. Verify that `index/info/2` returns a vector count greater than 0.

---

## Section 2 — What NOT to implement (and why)

| Rejected option | Reason |
|-----------------|--------|
| S1 Option B — boost confidence when rag_context present | The financial-keyword check in human_review_gate still fires on policy text containing "refund" / "استرداد". Insufficient alone; does not fully solve P1. |
| S1 Option C — new graph terminal edge for general_knowledge | Bigger graph change, higher risk. Option A achieves the same result in 3 lines. |
| S3 Option B — sticky route heuristic | Brittle. Fails on genuine topic switches. Not a real fix. |
| S3 Option C — persist order/invoice ID in session state | Helps data-fetch but does not fix route classification, which is the actual problem in P3. |
| S6 Option B — skip response_generator entirely for knowledge | Couples language output to Mini-RAG's internal PRIMARY_LANG setting (currently `en`). High risk of re-introducing P2 on the knowledge path. Rejected. |
| S6 Option C — cache frequent KB answers | Premature. Correctness and language fixes must be stable before adding a cache layer. |

---

## Section 3 — Implementation priority order

1. **Fix 1 + Fix 2** together — these two are tightly coupled (both affect the same failing knowledge turns) and together move the knowledge MVP from broken to bilingual-functional. Do not ship one without the other.
2. **Fix 3** — restores multi-turn conversation continuity.
3. **Fix 4** — restores source citations and trust.
4. **Fix 6** — latency optimization, after correctness is confirmed.
5. **Fix 5** — low effort, internal audit improvement, can be done in parallel with any of the above.
6. **Fix 7** — test calibration, include in the same commit as Fix 1.
7. **Fix 8** — ops task, independent, can be run at any time.

---

## Section 4 — Expected outcome after all fixes

| Metric | Before | Expected after |
|--------|--------|----------------|
| Knowledge turns fully passing | 0 / 6 (suppressed) | 6 / 6 |
| Arabic knowledge answers in Arabic | 0 / 3 | 3 / 3 |
| Multi-turn follow-up routing | Broken | Correct with session_id |
| rag_sources populated | Never | On every knowledge answer |
| Fully green turns (all checks) | 10 / 21 | ~19–20 / 21 |
| Remaining open items | — | P6 calibration only + tax grounding (S8) |

---

*End of agent instructions.*

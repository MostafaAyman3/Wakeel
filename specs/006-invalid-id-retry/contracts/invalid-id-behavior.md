# Contract: Invalid Identifier Retry & Guidance

This is the behavioral contract for the new `invalid_id_node` and the routing/
metadata changes around it. It is the source of truth for the test suite
(`scripts/test_invalid_id.py`) and the implementation.

## Node: `invalid_id_node` (`agents/m3/nodes/invalid_id_node.py`)

**Invoked when**: after `completeness_check`, `data_completeness == 0.0` AND
`customer_identifier` has a non-empty `type` and `value`.

**Inputs (read from `M3State`)**:
- `customer_identifier: {type, value}`
- `data_completeness: float` (== 0.0 on this branch)
- `language: "ar" | "en"`
- `chat_history: list[{role, content, metadata}]`

**Computation**:
1. `prior = trailing_invalid_id_streak(chat_history)` — count consecutive most-recent assistant
   turns with `metadata.invalid_id == True`; stop at the first non-tagged assistant turn.
2. `attempt = prior + 1`.
3. `max_attempts = settings.m3_invalid_id_max_attempts` (default 3).

**Outputs (partial `M3State` update)**:

| Condition | `final_response` | `invalid_id_attempts` | `invalid_id_pending` | `invalid_id_menu_shown` | `escalation_needed` |
|-----------|------------------|-----------------------|----------------------|-------------------------|---------------------|
| `attempt < max_attempts` | retry message (lang) | `attempt` | `True` | `False` | `False` |
| `attempt >= max_attempts` | escalation menu (lang) | `attempt` | `True` | `True` | `False` |

The node also sets `draft_response = final_response`, `review_required = False`,
`confidence_score = 0.0`, `rag_sources = []` (same hygiene as `clarification_node`).
The turn **ends** after this node (edge → `END`); it does **not** route to `escalation_node`
on its own — escalation only happens if the customer later asks for a human.

**Never raises**: on any LLM tone-adaptation error, fall back to the static templates below.

### Message wording

**Retry message (attempts 1–2)** — canonical EN (FR-004):
> We couldn't find your order/invoice using that ID. Please rewrite your ID carefully and try again.

AR fallback:
> لم نتمكن من العثور على طلبك/فاتورتك بهذا الرقم. من فضلك أعد كتابة الرقم بعناية وحاول مرة أخرى.

**Escalation menu (attempt 3+)** — canonical EN (FR-005), choice 3 included only when
`m3_alt_lookup_enabled`:
> We still cannot find your order after 3 attempts. Please choose one of the following:
> 1) Re-enter your ID
> 2) Talk to a human agent
> 3) Search using phone/email instead

AR fallback:
> ما زلنا غير قادرين على العثور على طلبك بعد 3 محاولات. من فضلك اختر أحد الخيارات التالية:
> ١) إعادة إدخال الرقم
> ٢) التحدث مع موظف خدمة العملاء
> ٣) البحث باستخدام رقم الهاتف أو البريد الإلكتروني

When `m3_alt_lookup_enabled == False`, omit choice 3 (and renumber) in both languages.

## Routing changes (`agents/m3/graphs/m3_graph.py`)

Replace the post-completeness routing so the not-found-with-identifier branch reaches the new node:

```text
completeness_check → _completeness_router:
    data_completeness == 0.0 AND identifier present   → "invalid_id"   (NEW → invalid_id_node)
    escalation_needed (no identifier / other)         → "escalate"     (response_generator, unchanged)
    else                                              → "classify"     (issue_classifier, unchanged)

invalid_id_node → END
```

Menu-choice handling on the **next** turn (`input_parser_node`, small pre-check): when the most
recent assistant turn has `metadata.invalid_id_menu == True` and the new message is a human-agent
request (e.g. matches a small AR/EN intent set: "human", "agent", "موظف", "representative", or the
choice index for option 2), set `escalation_needed = True` so the existing
`_escalation_router`/`escalation_node` handles hand-off with full context (FR-007).

## API metadata tagging (`backend/api/v1/m3_support.py`)

Extend the existing tag line so invalid-ID turns are counted next time:

```python
metadata = {}
if clarification_pending:
    metadata["clarification"] = True
if result.get("invalid_id_pending"):
    metadata["invalid_id"] = True
if result.get("invalid_id_menu_shown"):
    metadata["invalid_id_menu"] = True
assistant_metadata = metadata or None
```

## Acceptance mapping

| Spec item | Verified by |
|-----------|-------------|
| FR-003, FR-004, US1 | `attempt 1/2 → retry message`, count increments |
| FR-005, US2.1 | `attempt 3 → escalation menu` with choices |
| FR-006, US2.5 | new invalid ID after menu → menu re-presented |
| FR-007, US2.3 | "talk to a human" → `escalation_node` with context |
| FR-008, US2.4 | choice 3 omitted when `m3_alt_lookup_enabled=False`; collected when on |
| FR-009, US3 | valid ID → reset streak + normal answer |
| FR-010, US4.2 | new `session_id` → count starts at 0 |
| FR-011, US4.1 | conversation A's count does not affect B |
| FR-012 | never fabricate; only templates + genuine record |
| FR-013, SC-006 | AR/EN message selection |
| FR-014, FR-015, SC-007 | missing-ID (004) path and valid-ID path unchanged |

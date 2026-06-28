# Feature Specification: Clarifying Follow-up for Missing Identifiers

**Feature Branch**: `004-clarify-missing-identifier`

**Created**: 2026-06-26

**Status**: Draft

**Input**: User description: "خليه لما العميل يسال سؤال مش موضح فيه رقم الطلب او رقم العميل او رقم الفاتورة او في معلومات مش وضحه ترجع تساله تاني باستخدام الgreeting agent عن البيانات اللي انت محتاجها عشان ترد علي سؤاله و تقدر تستخدم المعلومات دي في انك تجيب الdata من الdatabase"

## Summary

When a customer asks a support question that needs a record lookup (order status, invoice, shipping, account history) but does **not** include the reference the system needs — an order number, invoice number, or customer number — the assistant should **ask a short, friendly follow-up question** for exactly the missing piece instead of giving up or handing the case to a human. Once the customer supplies the reference (in the same conversation), the assistant uses it to look up the data and answer the original question.

Today the assistant escalates such questions to a human the moment no reference is found. This feature replaces that premature hand-off with a brief conversational clarification, so most of these cases resolve themselves.

## Clarifications

### Session 2026-06-26

- Q: Should the clarifying flow verify the requester owns the record before returning it? → A: No ownership verification for this MVP — any valid reference returns its record (consistent with the current public endpoint); the privacy gap is recorded as a known limitation to close before production.
- Q: How many times should the assistant ask for the missing reference before handing off to a human? → A: Two attempts, then hand off.
- Q: After the missing reference is collected, should sensitive types (billing dispute / refund) still require mandatory human review? → A: Yes — clarification only gathers data; the existing human-review gate for billing/refund is preserved.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask for the missing reference, then answer (Priority: P1)

A customer types a record-dependent question without any reference, e.g. "Where is my order?" or "فين الأوردر بتاعي؟". The assistant recognizes that it needs an order/invoice/customer number to help, replies with a friendly question asking for that specific reference, and — once the customer provides it in the next message — looks up the record and answers the original question.

**Why this priority**: This is the core of the request and the highest-volume case. Without it, every reference-less question is escalated, frustrating customers and loading the support queue. Delivering just this story already turns abandoned questions into self-served answers.

**Independent Test**: Send a record-dependent question with no reference, confirm the reply is a clarifying question naming the exact reference needed (not an escalation), then send the reference and confirm the original question is answered from the looked-up data.

**Acceptance Scenarios**:

1. **Given** a new conversation, **When** the customer asks "Where is my order?" with no number, **Then** the assistant responds with a question asking for the order/invoice/customer number it needs — and does **not** escalate.
2. **Given** the assistant has just asked for an order number, **When** the customer replies "ORD-2024-1567", **Then** the assistant looks up that order and answers the original "where is my order" question with the real status.
3. **Given** a customer writing in Arabic, **When** the assistant asks for the missing reference, **Then** the clarifying question is in Arabic.

---

### User Story 2 - Ambiguous request gets a focused question (Priority: P2)

A customer describes a problem in vague terms, e.g. "I have an issue with a charge" or "عندي مشكلة في فاتورة", without saying which charge/invoice. The assistant asks a focused question to pin down which record they mean (e.g., "Which invoice number is this about?") before attempting a lookup.

**Why this priority**: Reduces wrong-record answers and repeated back-and-forth. Valuable but secondary to the basic missing-reference case.

**Independent Test**: Send a vague record-dependent complaint with no reference; confirm the assistant asks a single focused question for the missing detail rather than guessing or escalating.

**Acceptance Scenarios**:

1. **Given** a new conversation, **When** the customer says "the amount on my bill is wrong" with no invoice number, **Then** the assistant asks which invoice number it concerns.
2. **Given** the customer then supplies an invoice number, **When** the assistant looks it up, **Then** it responds about that specific invoice.

---

### User Story 3 - Carry context across the conversation (Priority: P2)

The original question and the later-supplied reference arrive in **separate messages**. The assistant must remember the original intent so that when the reference finally arrives, it answers the original question — not treat the bare reference as a brand-new, contextless input.

**Why this priority**: The clarification loop is worthless if the system forgets why it asked. Required for Stories 1 and 2 to feel coherent, but called out separately because it is the main failure mode to guard against.

**Independent Test**: Across two turns (question, then reference only), confirm the final answer addresses the original question using the supplied reference.

**Acceptance Scenarios**:

1. **Given** the customer asked about delivery and was asked for an order number, **When** they reply with only the order number, **Then** the assistant answers the delivery question for that order.
2. **Given** a customer changes topic mid-clarification (asks something unrelated), **When** they do so, **Then** the assistant handles the new request and does not silently apply the old pending reference to it.

---

### User Story 4 - Stop asking and hand off when needed (Priority: P3)

If the customer cannot or will not provide a usable reference after a small number of attempts, or keeps giving references that don't match any record, the assistant stops re-asking, explains it couldn't locate the record, and routes the case to a human with the conversation context.

**Why this priority**: Prevents an endless "please provide your number" loop and preserves the existing human safety net. Lower priority because it is the fallback, not the happy path.

**Acceptance Scenarios**:

1. **Given** the assistant has already asked twice for a reference, **When** the customer still provides none, **Then** the assistant stops asking and escalates with a clear message.
2. **Given** the customer provides a reference that matches no record, **When** the lookup fails, **Then** the assistant says it couldn't find that reference and offers to verify or hand off.

### Edge Cases

- **Greeting / general-knowledge questions**: "hello", "what is your return policy?" need no reference — the assistant MUST answer normally and MUST NOT ask for an order/invoice/customer number.
- **Reference present but unrecognized type**: The customer pastes a number with no prefix (e.g. "1567"). The assistant asks whether it is an order, invoice, or customer number.
- **Multiple references in one message**: The customer gives both an order and an invoice number; the assistant uses the one relevant to the question (or asks which to use).
- **Reference supplied up-front**: When the first message already contains a valid reference, the assistant skips clarification entirely and answers directly (no regression).
- **Customer abandons mid-clarification**: A new conversation/session starts clean with no leftover pending question.
- **Non-existent but well-formed reference** (e.g. "DEL-999"): graceful "couldn't find that record" response, then verify-or-escalate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST detect when a customer's request requires a record lookup but no usable order, invoice, or customer reference (or other required detail) is available from the message or the ongoing conversation.
- **FR-002**: When a required reference is missing, the system MUST reply with a short, conversational clarifying question that names the exact reference it needs (order number, invoice number, or customer number) — rather than escalating on that basis alone.
- **FR-003**: The system MUST NOT ask for a reference when the request does not need one (greetings, general product/policy questions).
- **FR-004**: The system MUST retain the original question and pending need across conversation turns, so that a reference supplied in a later message is applied to the original question.
- **FR-005**: Once the missing reference (or detail) is supplied, the system MUST use it to retrieve the relevant records and answer the original question.
- **FR-006**: The clarifying question MUST be written in the same language the customer is using (Arabic or English).
- **FR-007**: The system MUST ask for missing information at most **two** times in a conversation before falling back to a human hand-off, to avoid an endless clarification loop. (The limit is configurable; the agreed value is 2.)
- **FR-008**: When the supplied reference matches no record, the system MUST respond with a clear "not found" message and offer to verify the reference or hand the case to a human — it MUST NOT fabricate data.
- **FR-009**: When the customer changes topic during a pending clarification, the system MUST handle the new request on its own merits and not misapply the earlier pending reference.
- **FR-010**: When a valid reference is already present in the first message, the system MUST proceed directly to the lookup without asking a clarifying question (no regression to current direct-answer behavior).
- **FR-011**: If the customer provides a number whose type is ambiguous (no recognizable prefix), the system MUST ask which kind of reference it is before attempting a lookup.
- **FR-012**: After a hand-off triggered by exhausted clarification, the conversation context (original question, what was asked, what the customer provided) MUST be available to the human handling the case.
- **FR-013**: Collecting a missing reference MUST NOT bypass existing review safeguards — once the reference is supplied and the request is classified, billing-dispute and refund-request replies MUST still go to mandatory human review before reaching the customer.

### Key Entities *(include if feature involves data)*

- **Customer request**: The natural-language message and its detected intent; carries whether it needs a record lookup and which reference type(s) would satisfy it.
- **Conversation session**: The ordered set of turns for one customer interaction; holds the original/pending question and any references collected so far, and the count of clarification attempts.
- **Required-information need ("slot")**: A description of what is still missing (e.g., "order number") that drives the clarifying question and is cleared once filled.
- **Customer reference**: An order number, invoice number, or customer number used to fetch records; has a type and a value.
- **Record set**: The order, invoice, shipping, and history data retrieved once a valid reference is known.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 80% of record-dependent questions that arrive without a reference are answered after a single clarifying exchange, without human escalation.
- **SC-002**: Escalations caused solely by a missing reference drop by at least 70% compared with the current behavior (where every reference-less question escalates).
- **SC-003**: 100% of clarifying questions are presented in the same language the customer used.
- **SC-004**: The assistant never asks for a reference on greeting or general-knowledge questions (0 false clarification prompts in a representative test set).
- **SC-005**: No conversation enters an endless clarification loop — the assistant asks for missing information at most **twice** before handing off.
- **SC-006**: When a customer supplies a reference in a later turn, the assistant answers the original question (not a contextless reply) in at least 95% of multi-turn test cases.

## Assumptions

- The clarification flow applies to the customer-support assistant (M3) and reuses the existing conversation/session memory; a session identifier is available to tie turns together.
- The conversational follow-up is delivered through the existing greeting/conversational path, as the customer requested ("using the greeting agent").
- The clarification limit is **two** attempts before falling back to human escalation (decided in clarification; remains configurable).
- "Required information" for the current scope means a customer reference (order, invoice, or customer number). Collecting other arbitrary details is out of scope for this iteration.
- Reference formats follow existing conventions (e.g., `ORD-…`, `INV-…`, `CUST-…`); type can be inferred from the prefix, and the system asks when it cannot.
- General-knowledge answers continue to come from the existing knowledge base; this feature does not change how those are produced.
- Out of scope: collecting sensitive identity/verification data, authentication of the customer, and proactively asking for information the question does not actually require.
- **Known limitation (privacy)**: because there is no ownership verification, any caller who supplies a valid reference can view that record's data. This is acceptable for the mock-data MVP/demo but MUST be addressed (ownership/identity verification) before a production release with real customer data.

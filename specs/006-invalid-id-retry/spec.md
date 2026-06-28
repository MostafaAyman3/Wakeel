# Feature Specification: Invalid Identifier Retry & Guidance

**Feature Branch**: `006-invalid-id-retry`

**Created**: 2026-06-28

**Status**: Draft

**Input**: User description: "Feature Modification Request — M3 System (Invalid ID Handling): when a customer enters an identifier (order number, invoice number, shipment ID, tracking ID, or any customer-related lookup ID) that is invalid or not found, respond with user-friendly retry guidance. Track an `invalid_id_attempts` counter per conversation; show a standard retry message on the 1st and 2nd failed attempt and a stronger correctness-emphasis message on the 3rd; reset the counter when a valid ID is entered or the session ends. Existing M3 workflow stays unchanged except for this ID-validation enhancement."

## Summary

When a customer supplies a reference the system needs for a record lookup — an order number, invoice number, shipment ID, tracking ID, or other customer-related lookup ID — and that reference is **invalid or not found**, the assistant today gives an unhelpful response. This feature adds a **friendly, escalating retry flow with a clear exit**: each failed attempt is counted per conversation, the customer is gently asked to re-enter the ID after the first and second failure, and after a **third** consecutive failure the assistant **stops the normal retry loop and offers a short menu of recovery choices** — re-enter the ID, talk to a human agent, or look the record up another way (e.g., by phone or email). The counter resets as soon as a valid ID is entered (or the conversation ends), so a corrected ID immediately returns the conversation to its normal flow.

The escalation-after-three design prevents an infinite "wrong ID" loop, keeps the customer from getting stuck, and routes recovery to another tool or a human when self-service has clearly failed.

This refines the existing identifier handling. Feature 004 (`004-clarify-missing-identifier`) covers the case where **no** reference is supplied and the assistant asks for one. This feature covers the complementary case where a reference **is** supplied but is **wrong, malformed, or matches no record**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Friendly retry on a wrong ID (Priority: P1)

A customer supplies an identifier (e.g., an order number) that the system cannot find. Instead of a dead-end or generic error, the assistant replies with a friendly message asking them to rewrite the ID carefully and try again, and waits for a new attempt.

**Why this priority**: This is the core of the request and the highest-volume failure case. A clear, encouraging retry prompt turns most typos into self-served successes without escalation.

**Independent Test**: In a conversation, supply an order/invoice/shipment/tracking ID that matches no record; confirm the reply is the friendly retry message (not a generic error or escalation) and that the assistant is ready to accept a new ID.

**Acceptance Scenarios**:

1. **Given** a conversation where a record lookup is in progress, **When** the customer enters an order number that matches no record, **Then** the assistant replies "We couldn't find your order/invoice using that ID. Please rewrite your ID carefully and try again." and increments the failed-attempt count to 1.
2. **Given** the customer's first attempt already failed, **When** they enter a second ID that is also invalid or not found, **Then** the assistant shows the same friendly retry message and the failed-attempt count becomes 2.
3. **Given** the customer enters a malformed ID (wrong format), **When** the system cannot validate it, **Then** it is treated as a failed attempt with the same friendly retry message.

---

### User Story 2 - Escalation menu after three failures (Priority: P1)

After two failed attempts, a third consecutive failure stops the normal retry loop. The assistant tells the customer it still cannot find the record after three attempts and presents a short menu of recovery choices: **re-enter the ID**, **talk to a human agent**, or **search using phone/email instead**. The customer picks a path rather than being asked to keep guessing.

**Why this priority**: Repeated identical retries are a dead end. Offering an explicit exit prevents an infinite loop, keeps the customer from getting stuck, and hands recovery to a more capable path (human or alternate lookup). It is part of the same core flow as US1.

**Independent Test**: Cause three consecutive invalid-ID failures in one conversation; confirm the first two produce the standard retry message and the third presents the escalation menu with the three choices.

**Acceptance Scenarios**:

1. **Given** the failed-attempt count is 2, **When** the customer enters a third ID that is still invalid or not found, **Then** the assistant replies that it still cannot find the order after 3 attempts and offers the three choices (re-enter the ID / talk to a human agent / search using phone or email), and the failed-attempt count becomes 3.
2. **Given** the escalation menu has been shown, **When** the customer chooses **"re-enter your ID"** and provides a valid one, **Then** the record is returned and the failed-attempt count resets to 0.
3. **Given** the escalation menu has been shown, **When** the customer chooses **"talk to a human agent"**, **Then** the case is handed off to a human with the full conversation context, consistent with the existing human-handoff behavior.
4. **Given** the escalation menu has been shown, **When** the customer chooses **"search using phone/email instead"**, **Then** the assistant collects the alternate detail and attempts the lookup by that method instead of the failed ID.
5. **Given** the escalation menu has been shown, **When** the customer ignores the menu and simply enters another ID, **Then** the assistant attempts that ID; if still invalid it re-presents the escalation menu rather than looping silently.

---

### User Story 3 - A valid ID clears the slate (Priority: P1)

At any point in the retry sequence, the moment the customer enters a valid, found ID, the failed-attempt counter resets to zero and the conversation continues normally with the looked-up record.

**Why this priority**: Without a reset, a later unrelated lookup would inherit a stale failure count and prematurely trigger the escalation menu. Resetting on success keeps the escalation accurate and the experience fair.

**Independent Test**: Fail one or two attempts, then enter a valid ID; confirm the record is returned, the original question is answered, and a subsequent invalid ID starts the count again from 1.

**Acceptance Scenarios**:

1. **Given** the failed-attempt count is 2, **When** the customer enters a valid ID that is found, **Then** the assistant returns the record, answers the original question, and resets the failed-attempt count to 0.
2. **Given** a valid ID was just entered and the count was reset, **When** the customer later enters another invalid ID, **Then** the count starts again at 1 with the standard retry message.

---

### User Story 4 - Each conversation counts independently (Priority: P2)

The failed-attempt counter is scoped to a single conversation/session. A new conversation starts with a zero count, and failures in one conversation never affect another.

**Why this priority**: Correctness and fairness — a fresh chat should never inherit another conversation's failures. Builds on the per-session memory the system already maintains.

**Independent Test**: Reach two failures in conversation A, start conversation B, and enter an invalid ID; confirm B shows the first-attempt message (count 1), not the escalation menu.

**Acceptance Scenarios**:

1. **Given** conversation A reached two failed attempts, **When** a new conversation B begins and the customer enters an invalid ID, **Then** B treats it as attempt 1 with the standard retry message (not the escalation menu).
2. **Given** a conversation ends or is reset ("New chat"), **When** a fresh conversation starts, **Then** the failed-attempt count begins at 0.

### Edge Cases

- **Empty input**: When the customer sends no identifier where one is expected, the existing missing-identifier clarification (Feature 004) asks for the reference; an empty submission is not counted as an invalid-ID attempt by this feature.
- **Valid format but nonexistent record** (e.g., well-formed `ORD-999999` that matches nothing): counts as a failed attempt and shows the friendly retry message.
- **Invalid format / typo** (e.g., `ORDr-12a`): counts as a failed attempt with the same friendly retry message.
- **Mixed identifier types**: The retry flow applies to any supported lookup ID (order, invoice, shipment, tracking, or other customer-related ID); the message wording adapts to the kind of lookup in progress.
- **Switching the looked-up item**: Entering a valid ID for a different but valid record still counts as success and resets the counter.
- **Recovery after the escalation menu**: After the 3rd-attempt escalation menu, a subsequent valid ID (whether chosen via "re-enter" or typed directly) still resets the counter and returns to normal flow.
- **Repeated failure past the menu**: If the customer keeps entering invalid IDs after the menu was shown, the assistant re-presents the escalation menu instead of looping on the plain retry message — it never gets stuck silently.
- **Alternate-lookup unavailable**: If lookup by phone/email is not available in the current environment, the assistant still offers re-enter and human-agent options and does not present a non-functional choice.
- **Language**: The customer may be conversing in Arabic or English; the retry messages and the escalation menu (including its choice labels) are presented in the language the customer is using.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: When a customer supplies an identifier for a record lookup (order number, invoice number, shipment ID, tracking ID, or other supported customer-related ID), the system MUST determine whether the identifier is valid in format and whether it corresponds to an existing record.
- **FR-002**: The system MUST treat each of the following as a failed attempt: a malformed/invalid-format identifier, a well-formed identifier that matches no record, and a typo'd identifier that cannot be located.
- **FR-003**: The system MUST maintain a per-conversation failed-attempt count (`invalid_id_attempts`) that increments by one each time a supplied identifier is invalid or not found.
- **FR-004**: On the **first** and **second** failed attempt in a conversation, the system MUST reply with the friendly retry message: "We couldn't find your order/invoice using that ID. Please rewrite your ID carefully and try again." and prompt the customer to re-enter the identifier.
- **FR-005**: On the **third** failed attempt in a conversation, the system MUST stop the normal retry loop and present an escalation message that states the record still cannot be found after three attempts and offers a short menu of recovery choices. Canonical wording: "We still cannot find your order after 3 attempts. Please choose one of the following: (1) Re-enter your ID, (2) Talk to a human agent, (3) Search using phone/email instead."
- **FR-006**: When the customer chooses **"re-enter your ID"** (or simply supplies another identifier after the menu), the system MUST attempt the lookup; on success it follows FR-007 (reset + normal flow), and on another failure it MUST re-present the escalation menu rather than reverting to the plain retry message.
- **FR-007**: When the customer chooses **"talk to a human agent"**, the system MUST hand the case off to a human with the full conversation context (original question, attempted IDs, attempt count), reusing the existing human-handoff path.
- **FR-008**: When the customer chooses **"search using phone/email instead"**, the system MUST collect the alternate detail (phone or email) and attempt the record lookup by that method instead of the failed identifier. If alternate lookup is not available in the current environment, the system MUST omit this choice from the menu rather than offer a non-functional option.
- **FR-009**: The system MUST reset the failed-attempt count to zero when the customer enters a valid identifier that is successfully found (including via the menu's "re-enter" choice), and then MUST continue the normal flow (return the record / answer the original question).
- **FR-010**: The system MUST reset the failed-attempt count to zero when the conversation/session ends or is explicitly reset (e.g., "New chat").
- **FR-011**: The failed-attempt count MUST be scoped to a single conversation/session — failures in one conversation MUST NOT affect the count in any other conversation.
- **FR-012**: The system MUST NOT fabricate or guess record data for an invalid or not-found identifier; it MUST only present the retry/escalation messages and the genuine looked-up record on success.
- **FR-013**: The retry messages and the escalation menu (including its choice labels) MUST be presented in the language the customer is using (Arabic or English), preserving the meaning of the canonical English wording in FR-004 and FR-005.
- **FR-014**: This feature MUST NOT change any existing M3 behavior other than the invalid-identifier handling described here — routing, the missing-identifier clarification (Feature 004), conversation memory (Feature 005), knowledge answers, and the human-review gate remain unchanged.
- **FR-015**: An empty or absent identifier MUST be handled by the existing missing-identifier clarification flow (Feature 004) and MUST NOT increment this feature's failed-attempt count.

### Key Entities *(include if feature involves data)*

- **Customer identifier**: A reference supplied by the customer for a record lookup — order number, invoice number, shipment ID, tracking ID, or other supported customer-related ID. Has a kind (which lookup it targets), a value, a format-validity status, and a found/not-found status.
- **Conversation session**: The ordered set of turns for one customer interaction; holds the `invalid_id_attempts` count for this feature, alongside the existing per-session memory and pending-question state.
- **Failed-attempt count (`invalid_id_attempts`)**: A per-conversation integer, starting at 0, incremented on each invalid/not-found identifier and reset to 0 on a successful lookup or session end. Drives whether the customer sees the standard retry message (attempts 1–2) or the escalation menu (attempt 3+).
- **Escalation menu**: The set of recovery choices offered on the 3rd failure — re-enter the ID, talk to a human agent, and (when available) search by phone/email. Each choice routes to a recovery path: another lookup attempt, the human-handoff path, or the alternate-lookup method.
- **Alternate lookup detail**: A phone number or email address the customer can provide as an alternative to the failed identifier, used to find the record when ID-based lookup keeps failing.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of invalid or not-found identifier submissions receive a friendly retry message or the escalation menu rather than a generic error or fabricated record.
- **SC-002**: The first and second failed attempts in a conversation show the standard retry message, and the third presents the escalation menu with its recovery choices, in 100% of test cases.
- **SC-003**: After a successful lookup, a subsequent invalid identifier restarts the count at the standard retry message (count = 1) in 100% of test cases — no stale count carries over.
- **SC-004**: Zero cross-conversation interference — in a representative test set, no conversation's failed-attempt count is affected by another conversation (0 leaks).
- **SC-005**: No customer is left in an unbounded retry loop — the escalation menu (and therefore a path to a human or alternate lookup) is reachable within 3 failed attempts in 100% of test cases.
- **SC-006**: 100% of retry messages and escalation menus are presented in the same language the customer is using.
- **SC-007**: No existing M3 scenario (missing-identifier clarification, memory recall, knowledge answers, valid-ID lookups, review gate) regresses when this feature is enabled, verified across the existing test suites.

## Assumptions

- This feature applies to the customer-support assistant (M3) and reuses the existing per-conversation/session state already used for memory (Feature 005) and pending-clarification tracking (Feature 004); a session identifier ties turns together.
- "Invalid or not found" covers both format-invalid identifiers and well-formed identifiers that match no record; both increment the same counter and produce the same standard message.
- The canonical message wording is the English text given in the request; the assistant translates/adapts it to Arabic when the customer is conversing in Arabic (consistent with the system's existing bilingual behavior). The literal phrase "order/invoice" stands in for whichever lookup kind is in progress.
- The reset triggers are limited to (a) a successful valid-ID lookup and (b) end/reset of the conversation, per the request. Switching topics without a successful lookup does not, on its own, reset the count.
- **Behavior after the third attempt (resolved)**: On the 3rd failure the assistant stops the plain retry loop and offers the escalation menu (re-enter / human agent / phone-or-email lookup). This supersedes simply repeating a stronger message: it prevents an infinite loop and provides an explicit exit. Further failures re-present the menu rather than reverting to the plain retry message.
- The **"talk to a human agent"** choice reuses the existing human-handoff path (the same one Feature 004 uses when clarification is exhausted); this feature adds a new entry point to it, not a new escalation mechanism.
- The **"search using phone/email instead"** choice depends on an alternate-lookup capability (find a record by phone or email). Where that capability is not yet available, the menu offers only the re-enter and human-agent choices; standing up alternate lookup may be a follow-up dependency.
- Empty/missing identifiers are routed to the existing missing-identifier clarification (Feature 004), which has its own at-most-two-attempts-then-handoff limit; this feature does not duplicate or override that flow.
- The lookup data source is the existing record store used by the current record-lookup path; no new datastore is introduced.
- Out of scope: ownership/identity verification of the supplied identifier (the existing known privacy limitation from Feature 004 still applies), and any change to how valid records are formatted or answered.

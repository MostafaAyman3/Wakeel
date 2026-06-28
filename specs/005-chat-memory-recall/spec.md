# Feature Specification: Conversation Memory & Recall

**Feature Branch**: `005-chat-memory-recall`

**Created**: 2026-06-26

**Status**: Draft

**Input**: User description: "دلوقتي لما بقوله علي اسمي و ارجع اساله اسمي ايه مبيردش عايز نزود memory للشات بحيث يبقي فاكر اللي بيحصل في المحادثة"

## Summary

The assistant forgets what was said earlier in the same chat. If a customer says "my name is Kareem" and later asks "what's my name?", the assistant doesn't answer. This feature gives the chat **conversation memory**: within a single conversation the assistant remembers facts and context the customer shared earlier (their name, what they're asking about, references already given) and uses them when replying — including answering direct questions about those facts.

Scope is **within one conversation** (the current chat session). A new conversation starts fresh.

## Clarifications

### Session 2026-06-26

- Q: How should the assistant remember and recall conversation facts? → A: Transcript-based — the recent conversation turns are included in the assistant's context so it can recall anything that was said (no separate fact-extraction store for this iteration).
- Q: Should the conversation (and its memory) survive a page reload in the same browser? → A: Yes — the conversation id persists in the browser so memory survives a refresh; an explicit "New chat" resets it. Still session-scoped (no cross-customer/cross-device profile).

### Session 2026-06-28

- Q: How far back must recall reliably work for the acceptance tests? → A: Recent bounded window only (~last 10 turns); facts older than the window may be forgotten — acceptance tests exercise facts stated within this span.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recall a fact the customer stated (Priority: P1)

A customer tells the assistant a fact about themselves (e.g., "my name is Kareem" / "اسمي كريم"). Later in the same conversation they ask for it back ("what's my name?" / "اسمي ايه؟"). The assistant answers correctly from the conversation.

**Why this priority**: This is the exact failure the user reported and the clearest proof of memory. Without it the chat feels broken; with it the conversation feels coherent.

**Independent Test**: In one session, send a fact, then ask for it; confirm the assistant returns the stated value (not a generic "I don't know").

**Acceptance Scenarios**:

1. **Given** a conversation where the customer said "my name is Kareem", **When** they later ask "what's my name?", **Then** the assistant replies with "Kareem".
2. **Given** the customer wrote in Arabic ("اسمي كريم"), **When** they later ask "اسمي ايه؟", **Then** the assistant answers in Arabic with "كريم".
3. **Given** the customer never stated their name, **When** they ask "what's my name?", **Then** the assistant says it doesn't have that yet and offers to note it — it does **not** invent a name.

---

### User Story 2 - Use earlier context to stay coherent (Priority: P2)

The customer refers back to something mentioned earlier without repeating it (e.g., they discussed an order, then say "is it shipped yet?"). The assistant uses the earlier context to understand "it".

**Why this priority**: Makes multi-turn conversations natural and reduces repetition. Builds on US1's memory but applies to context, not just stored facts.

**Independent Test**: Mention a subject in turn 1, refer to it indirectly in a later turn; confirm the reply addresses that subject.

**Acceptance Scenarios**:

1. **Given** the customer mentioned a specific order earlier, **When** they later ask "has it shipped?", **Then** the assistant understands "it" refers to that order.
2. **Given** the customer already gave a reference earlier in the chat, **When** a later question needs it, **Then** the assistant does not ask for it again.

---

### User Story 3 - Memory is private to each conversation (Priority: P2)

Facts shared in one conversation must never surface in a different conversation (another customer or a fresh chat).

**Why this priority**: Correctness and privacy. Memory that leaks across conversations is worse than no memory.

**Independent Test**: State a fact in conversation A; start conversation B and ask for it; confirm B does not know it.

**Acceptance Scenarios**:

1. **Given** the customer said their name in conversation A, **When** a new conversation B asks "what's my name?", **Then** B replies that it doesn't have it.
2. **Given** a customer starts a brand-new chat, **When** they ask about anything from a prior chat, **Then** the assistant treats it as not provided.

---

### User Story 4 - Handle updates and unknowns gracefully (Priority: P3)

The customer changes a fact, or asks about something never said.

**Why this priority**: Edge-case correctness so memory stays trustworthy.

**Acceptance Scenarios**:

1. **Given** the customer said "my name is Kareem" then later "actually, it's Khaled", **When** they ask "what's my name?", **Then** the assistant answers "Khaled" (most recent value).
2. **Given** the customer asks about a detail they never shared, **When** the assistant has no record of it in the conversation, **Then** it says it doesn't have that information rather than guessing.

### Edge Cases

- **No session / single-turn**: When messages aren't tied together as one conversation, recall isn't possible — the assistant behaves as today (known limitation).
- **Very long conversation**: The assistant remembers only the recent window (~last 10 turns); turns older than that window fall outside memory and may not be recalled. Acceptance tests exercise facts stated within the window.
- **Recall on any path**: Whether the follow-up is small talk, a knowledge question, or an issue, the earlier facts are still available.
- **Mixed languages**: A fact stated in Arabic can be recalled when later asked in English and vice-versa; the reply matches the language of the question.
- **Contradictory restatements**: The most recently stated value wins.
- **Page reload**: Refreshing the page keeps the same conversation (memory survives); only an explicit "New chat" clears it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The assistant MUST take the earlier turns of the current conversation into account when forming a reply, so facts and context the customer shared earlier are available. Recall is **transcript-based** — the recent conversation turns are part of the assistant's context; no separate fact-extraction store is introduced in this iteration.
- **FR-002**: When the customer asks for something they stated earlier in the same conversation (e.g., their name), the assistant MUST answer using that conversation's content.
- **FR-003**: Conversation memory MUST be scoped to a single conversation — facts from one conversation MUST NOT appear in any other conversation.
- **FR-004**: When a fact is restated or changed within a conversation, the assistant MUST use the most recent value.
- **FR-005**: If the customer asks about something they never provided in the conversation, the assistant MUST state that it doesn't have it and MUST NOT fabricate a value.
- **FR-006**: Memory MUST apply across every conversational reply path (small talk / greetings, general-knowledge answers, and issue handling) — not only one path.
- **FR-007**: Recall MUST be language-aware: the reply matches the language of the question, regardless of the language the fact was originally stated in.
- **FR-008**: A new conversation MUST begin with no carried-over memory from previous conversations.
- **FR-009**: Memory MUST cover a bounded recent window of the conversation — approximately the last 10 turns. Facts stated within this window MUST be recallable; facts older than the window MAY fall out of memory.
- **FR-010**: The same conversation MUST persist across page reloads within the same browser — the conversation identifier is retained locally so memory survives a refresh. An explicit "New chat" action MUST start a fresh conversation with no carried-over memory.

### Key Entities *(include if feature involves data)*

- **Conversation session**: The ordered set of turns belonging to one chat; the unit of memory. Identified so turns can be tied together and kept separate from other conversations.
- **Conversation turn**: A single customer or assistant message within a session, in order.
- **Recalled fact / context**: Any information the customer shared earlier in the session (e.g., name, the subject they're asking about, a reference already given) that the assistant can use or report back.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When a customer states a fact and later asks for it within the same conversation (and within the recent window of ~10 turns), the assistant returns the correct value in at least 95% of test cases.
- **SC-002**: Zero cross-conversation leaks — in a representative test set, no fact from one conversation appears in another (0 leaks).
- **SC-003**: When asked for something never stated in the conversation, the assistant declines without fabricating in 100% of test cases.
- **SC-004**: Recall succeeds regardless of which reply path handles the follow-up (small talk, knowledge, or issue) — verified across all three paths.
- **SC-005**: After a restated/changed fact, the assistant returns the most recent value in at least 95% of test cases.

## Assumptions

- Memory is **session-scoped (short-term)** — it remembers within one ongoing conversation, and that conversation persists across page reloads in the same browser (its identifier is retained locally). A persistent, cross-customer/cross-device profile is out of scope for this iteration.
- A conversation/session identifier ties turns together (already used by the chat); requests not tied to a session cannot recall (known limitation, consistent with current behavior).
- Memory uses the existing conversation storage; no new long-term datastore is assumed.
- "Recent window" is bounded to approximately the last 10 turns; the exact count is a tuning detail within this bound, not a scope decision.
- Out of scope: remembering across separate chats/devices, building a durable customer profile, and inferring facts the customer did not actually state.

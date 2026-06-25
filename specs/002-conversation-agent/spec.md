# Feature Specification: Conversation Agent (Small-Talk Route)

**Feature Branch**: `002-conversation-agent`

**Created**: 2026-06-24

**Status**: Draft

**Input**: User description: "Add a simple conversation agent whose prompt is a
friendly chatbot response when the customer says things like 'how are you' or
'Hi'; if they ask about anything in our knowledge base, retrieve from RAG; and
when they ask about issues or complaints, go to our CRM agent."

## Summary

Extend the existing Unified Support Chatbot with a fourth conversational
**greeting / small-talk** route. Today the Intent Router classifies every
message as `general_knowledge`, `customer_issue`, or `hybrid`. Social messages
("Hi", "how are you", "thank you", "good morning") currently fall through to the
issue pipeline and produce an awkward "no record found / an agent will follow
up" reply. This feature adds a `greeting` route that answers social messages
directly with a short, friendly, on-brand reply — no database lookup, no RAG
call — while knowledge questions still go to RAG and issues/complaints still go
to the CRM agent.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Friendly small-talk reply (Priority: P1) 🎯 MVP

As a customer, when I open the chat and say something social like "Hi" or "how
are you?", I get a warm, brief, human-sounding reply that invites me to ask my
real question — instead of an error or a "no record found" message.

**Why this priority**: It is the first impression of every conversation. Without
it, greetings produce confusing error-like replies that undermine trust in the
whole chatbot. It is also self-contained and needs no external data.

**Independent Test**: Send "Hi" (and the Arabic "السلام عليكم") with no order
reference → router picks `greeting` → a short friendly reply is returned in the
same language, with no sources, no review hold, and no escalation.

**Acceptance Scenarios**:

1. **Given** an empty chat, **When** the customer sends "Hi", **Then** the system
   replies with a brief friendly greeting that offers help, in English.
2. **Given** an empty chat, **When** the customer sends "كيف حالك؟", **Then** the
   system replies with a brief friendly greeting in Arabic.
3. **Given** a greeting reply, **When** it is returned, **Then** `review_required`
   is false, `escalation_needed` is false, and no knowledge sources are attached.
4. **Given** the customer says "thank you" / "شكراً", **When** sent, **Then** the
   system gives a brief courteous acknowledgement and offers further help.

---

### User Story 2 - Knowledge questions still reach RAG (Priority: P1)

As a customer, when I ask about a policy or general information (e.g. "What is
your return policy?"), the message is NOT mistaken for small-talk and is answered
from the knowledge base.

**Why this priority**: Adding a greeting route must not steal traffic from the
existing knowledge route, which is the product's core value.

**Independent Test**: Send a policy/FAQ question → router picks
`general_knowledge` (not `greeting`) → a grounded knowledge answer is returned.

**Acceptance Scenarios**:

1. **Given** a knowledge question with no greeting, **When** sent, **Then** the
   route is `general_knowledge` and a knowledge-grounded answer is returned.
2. **Given** a message that mixes a greeting and a question ("Hi, what is your
   return policy?"), **When** sent, **Then** the system answers the question
   (knowledge route) rather than only greeting back.

---

### User Story 3 - Issues and complaints still reach the CRM agent (Priority: P1)

As a customer, when I describe an order/invoice problem or a complaint, it is NOT
mistaken for small-talk and is handled by the CRM agent.

**Why this priority**: Misrouting a complaint to the greeting responder would
drop a real support need — unacceptable. The greeting route must be conservative.

**Independent Test**: Send "Where is my order ORD-2024-0001?" → router picks
`customer_issue` (not `greeting`) → the CRM pipeline runs.

**Acceptance Scenarios**:

1. **Given** an order/complaint message, **When** sent, **Then** the route is
   `customer_issue` (or `hybrid`) and the CRM agent pipeline runs.
2. **Given** a frustrated social-sounding complaint ("Hello, I'm really not happy
   with you"), **When** sent, **Then** the system treats it as an issue/complaint,
   not as friendly small-talk.

---

### Edge Cases

- **Greeting + question combined**: The message contains both a greeting and a
  substantive request → the substantive intent wins (knowledge or issue), and the
  reply may open with a brief friendly acknowledgement.
- **Ambiguous one-word messages** ("hello?", "ok", "هاي"): treated as `greeting`
  only when there is no actionable request; otherwise default to `customer_issue`
  (the existing low-confidence fallback) so no real need is dropped.
- **Abusive or off-topic chit-chat**: the greeting responder stays polite, brief,
  and redirects to how it can help; it does not engage with off-topic requests.
- **Follow-up after a greeting**: a greeting turn must not block the next message
  from being routed to knowledge or issue handling.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Intent Router MUST classify each incoming message into one of
  four routes: `greeting`, `general_knowledge`, `customer_issue`, or `hybrid`.
- **FR-002**: When the route is `greeting`, the system MUST produce a short,
  friendly reply directly, WITHOUT querying the knowledge base or the customer
  database.
- **FR-003**: A `greeting` reply MUST be in the same language as the customer's
  message (Arabic or English) and MUST stay brief (roughly one to two sentences).
- **FR-004**: A `greeting` reply MUST offer to help (gently prompt the customer to
  ask their question or describe their issue).
- **FR-005**: A `greeting` reply MUST never set `review_required` or
  `escalation_needed`, and MUST carry no knowledge sources.
- **FR-006**: The router MUST be conservative: if a message contains any
  actionable request (a question answerable from knowledge, or any order/invoice/
  complaint signal), it MUST NOT be routed to `greeting`.
- **FR-007**: On low router confidence, the system MUST fall back to
  `customer_issue` (existing behaviour) rather than `greeting`, so no real support
  need is dropped.
- **FR-008**: The `greeting` route MUST integrate with conversation memory so a
  greeting turn and its reply are persisted like any other turn when a session id
  is supplied.
- **FR-009**: The customer-facing response payload MUST expose `greeting` as a
  possible value of the existing route indicator so the UI can label it.
- **FR-010**: The existing `general_knowledge`, `customer_issue`, and `hybrid`
  behaviours MUST remain unchanged for non-social messages.

### Key Entities *(include if feature involves data)*

- **Route classification**: the routing decision for a message; gains a new
  category `greeting` alongside the existing three. Attributes: chosen route,
  confidence, target knowledge collection (none for greeting).
- **Conversation turn**: an existing entity (user message + assistant reply,
  persisted by session); a greeting exchange is stored the same way.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 95% of common greetings/small-talk ("hi", "hello",
  "how are you", "good morning", "thanks", and their Arabic equivalents) are
  routed to `greeting` and receive a friendly reply rather than an error/no-record
  message.
- **SC-002**: 100% of clear order/complaint messages and clear knowledge
  questions continue to route to `customer_issue`/`hybrid` and `general_knowledge`
  respectively (no regression caused by the new route).
- **SC-003**: A greeting reply is returned noticeably faster than a data-backed
  answer because it performs no knowledge or database lookup.
- **SC-004**: Greeting replies match the customer's language (AR/EN) in at least
  95% of sampled cases.
- **SC-005**: No greeting reply ever exposes internal data, sources, a held draft,
  or an escalation notice.

## Assumptions

- The greeting route is added to the EXISTING intent router and graph from feature
  001 (Unified Support Chatbot); it reuses the same `/support` endpoint, response
  generator, and conversation-memory mechanism.
- "Friendly chatbot response" means a short, polite, on-brand acknowledgement that
  redirects to support — not an open-ended general-purpose assistant; the agent
  does not answer trivia, do math, or hold off-topic conversations.
- Greeting detection is handled by the same LLM-based router used today (no
  separate hard-coded keyword service is required), with a conservative bias
  toward the existing routes when unsure.
- Bilingual scope is Arabic and English only, consistent with feature 001.
- No new data store is required; conversation turns reuse the existing
  conversations persistence.

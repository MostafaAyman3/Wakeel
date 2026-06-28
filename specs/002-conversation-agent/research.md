# Research: Conversation Agent (Small-Talk Route)

No `[NEEDS CLARIFICATION]` markers remained in the spec. The decisions below
record how the feature integrates with the existing feature-001 architecture.

## Decision 1 — Reuse the existing LLM router (no separate keyword matcher)

- **Decision**: Add `greeting` as a fourth label to the existing
  `intent_router_node` / `support_router.py` prompt rather than building a
  hard-coded keyword pre-filter.
- **Rationale**: The router already does AR/EN LLM classification with a
  structured output and a conservative low-confidence fallback. Greetings are
  easy for the model to recognise, and keeping one classifier avoids two sources
  of truth and double latency. Keyword lists miss paraphrases and mix languages
  poorly.
- **Alternatives considered**: (a) Regex/keyword pre-check before the LLM —
  rejected: brittle, bilingual maintenance burden, risks catching "hi" inside
  real questions. (b) A separate small classifier model — rejected: unnecessary
  cost/latency for a 4-way decision the current model handles.

## Decision 2 — Dedicated `greeting_node`, shortest graph path

- **Decision**: Route `greeting` to a new `greeting_node` that calls the fast LLM
  (`llm_fast`, gpt-4o-mini) with a small friendly system prompt and returns
  `final_response`/`draft_response` directly, then goes to `END`.
- **Rationale**: Greetings need no data. Skipping `rag_node`, the CRM pipeline,
  and the review gate makes replies fast and guarantees no data/source leakage.
  A dedicated node keeps the prompt and behaviour isolated and testable.
- **Alternatives considered**: (a) Reuse `response_generator_node` with empty
  context — rejected: that node is built around CRM tiers/escalation and would
  need conditional branches that muddy it. (b) Hard-coded canned strings —
  rejected: less natural, poor coverage of varied greetings; a tiny LLM call is
  cheap and friendlier (still bounded to 1–2 sentences by the prompt).

## Decision 3 — Bypass the human-review gate for greetings

- **Decision**: The greeting path goes straight to `END`; it never enters
  `human_review_gate`, and `greeting_node` sets `review_required=False`,
  `escalation_needed=False`.
- **Rationale**: FR-005 requires greetings to never hold a draft or escalate.
  Routing greeting → END avoids the gate entirely (no risk of a false-positive
  financial/keyword hold on a friendly sentence).
- **Alternatives considered**: Run the gate but force-pass for greetings —
  rejected: extra code path with no benefit.

## Decision 4 — Conservative routing precedence

- **Decision**: Router precedence is: actionable request wins over social
  framing. If a message has any knowledge question or order/invoice/complaint
  signal, choose `general_knowledge` / `customer_issue` / `hybrid`; choose
  `greeting` only for pure social messages. Low confidence still defaults to
  `customer_issue` (existing behaviour), NOT `greeting`.
- **Rationale**: Satisfies FR-006/FR-007 and SC-002 — never drop a real support
  need into small-talk. Mixed "Hi, where is my order?" must run the CRM pipeline.
- **Alternatives considered**: Greeting-first precedence — rejected: would
  mis-handle "Hi, I want a refund".

## Decision 5 — Language handling

- **Decision**: `greeting_node` mirrors the customer's language using the same
  Arabic-range detection already used elsewhere (`language` in state, or detect
  from the message), and the prompt instructs "reply ONLY in {lang}".
- **Rationale**: Consistent with feature 001's language-mirroring fix; satisfies
  FR-003 / SC-004.
- **Alternatives considered**: English-only greeting — rejected: breaks AR users.

## Decision 6 — Testing approach

- **Decision**: Add `scripts/test_conversation_agent.py` (HTTP-level) asserting
  route + reply language + absence of sources/review for greetings, plus
  regression checks that knowledge/issue messages still route correctly. Greeting
  logic is testable without the DB or Mini-RAG.
- **Rationale**: Mirrors feature 001's `test_unified_support.py`; the greeting
  route is the one path that needs neither Postgres nor the RAG service, so it can
  be validated even in the current network-restricted environment.

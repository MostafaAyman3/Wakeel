"""
ResponseGeneratorNode — generates the final customer-facing response via GPT-4o.

Sprint 3 responsibilities:
    1. Repeat-issue detection (>2 same-type issues in 180 days → escalation).
    2. Confidence score refinement (data_completeness + classification + context).
    3. Response generation with three-case logic (full / partial / no data).
    4. Graceful degradation on LLM failure → static template fallback.

Consumes (read-only): issue_type, issue_priority, context, language,
    data_completeness, missing_fields, customer_identifier, fetched_data.
Produces: draft_response, final_response, confidence_score, escalation_needed.

All Sprint 1–2 fields are read-only — never modified.
"""

from __future__ import annotations

from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage

from agents.m3.schemas.m3_state import M3State
from agents.shared.llm_client import llm_primary, llm_fast
from backend.core.logging import get_logger

logger = get_logger(__name__)

# ── Repeat-issue threshold ─────────────────────────────────────────
_REPEAT_ISSUE_THRESHOLD = 2       # more than this → escalate
_REPEAT_ISSUE_DAYS = 180          # lookback window

# ── Static fallback templates (LLM failure) ─────────────────────────
_FALLBACK_AR = (
    "عذراً، حدث خطأ أثناء معالجة طلبك. "
    "سيتواصل معك فريق الدعم قريباً للمتابعة."
)

_FALLBACK_EN = (
    "An error occurred while processing your request. "
    "Our support team will reach out shortly."
)

# ── Standard partial-data message ───────────────────────────────────
_PARTIAL_DATA_AR = (
    "بعض المعلومات غير متوفرة حالياً. "
    "سيتواصل معك فريق الدعم خلال 24 ساعة."
)

_PARTIAL_DATA_EN = (
    "Some information is currently unavailable. "
    "Our support team will follow up within 24 hours."
)

# ── No-data message ─────────────────────────────────────────────────
_NO_DATA_AR = (
    "لم يتم العثور على سجل مطابق. "
    "يرجى التحقق من رقم المرجع الخاص بك أو التواصل مع الدعم الفني."
)

_NO_DATA_EN = (
    "No matching record was found. "
    "Please verify your reference number or contact support."
)

# ── Escalation message (appended when repeat-issue detected) ────────
_ESCALATION_MSG_AR = (
    "تم تحديد أن مشكلتك متكررة. "
    "سيتم تحويل حالتك إلى وكيل دعم أول للمتابعة."
)

_ESCALATION_MSG_EN = (
    "We see that this is a recurring issue. "
    "Your case will be transferred to a senior support agent for follow-up."
)


# ── System prompt for GPT-4o ────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a friendly, professional customer support agent for an e-commerce company.
Your task is to generate a helpful response to the customer based ONLY on the data provided below.

## Rules (strict — follow every rule)

1. **Language**: You MUST respond in EXACTLY the same language as the customer's message.
   - The "IMPORTANT: Respond ONLY in ..." instruction in the data block is mandatory.
   - If the customer wrote in Arabic, your ENTIRE response must be in Arabic.
   - If the customer wrote in English, your ENTIRE response must be in English.
   - NEVER mix languages. NEVER switch mid-response.

2. **Tone**: Simple, warm, non-technical, customer-friendly.
   - Do NOT use internal terminology like "issue_type", "context", "state", "LLM", "confidence".
   - Do NOT mention data sources, field names, or system internals.

3. **Knowledge Base answers** (when a "Knowledge Base Answer" section is present):
   - Lead with the knowledge base answer. Cite it naturally ("According to our policy, ...").
   - Do NOT fabricate policy details not in the knowledge base answer.
   - If CRM data is also present, combine both coherently in one response.

4. **Data completeness tiers** (for CRM data — when present):

   Tier A — Full Data Available: All relevant information is provided below.
       → Generate a complete response including order status, invoice amount,
         shipping tracking, and delivery dates.
       → Be specific and helpful. End with an offer to help further.

   Tier B — Partial Data Available: Some information is marked as "NOT AVAILABLE".
       → Include only the information that IS available.
       → Append (translated to the customer's language):
         "Some information is currently unavailable. Our support team will follow up within 24 hours."
       → Do NOT list which specific fields are missing.

   Tier C — No Data Available: All fields are "NOT AVAILABLE" and no knowledge base answer.
       → Do NOT pretend to have information.
       → State that no matching record was found.
       → Ask the customer to verify their reference number or contact support.

5. **Escalation**: If the customer's problem is marked as a "recurring issue",
   append (translated correctly):
   "We see that this is a recurring issue. Your case will be transferred to a senior support agent."

6. **Truthfulness**: Only use the data provided below. NEVER invent or guess
   order numbers, dates, amounts, statuses, or policy details.

7. **Formatting**: Use plain text only. No markdown, no lists, no JSON.
   Write in full sentences. Use paragraph breaks for readability.
"""


# ── Public node function ────────────────────────────────────────────

async def generate_response(state: M3State) -> dict:
    """Generate the final customer-facing response.

    1. Detect repeat issues from history.
    2. Refine confidence score.
    3. Build prompt and call GPT-4o.
    4. Fall back to static template on LLM failure.
    """
    lang: str = state.get("language", "en") or "en"
    # Fix 2 Part B (guard): if the language was never resolved (e.g. a future path
    # that bypasses the router), re-detect from the customer message so we never
    # silently fall back to English for an Arabic question.
    if lang == "auto":
        _msg = state.get("issue_description", "") or ""
        lang = "ar" if any("؀" <= c <= "ۿ" for c in _msg) else "en"
    ctx: dict = state.get("context") or {}
    history: list[dict] | None = ctx.get("history")
    completeness: float = state.get("data_completeness", 0.0)
    issue_type: str | None = state.get("issue_type")
    issue_priority: str | None = state.get("issue_priority")

    # ── 1. Repeat-issue detection ──────────────────────────────────
    escalation_needed = bool(state.get("escalation_needed", False))
    is_recurring = False

    if history and issue_type:
        try:
            cutoff = datetime.now(tz=timezone.utc)
            match_count = 0
            for entry in history:
                entry_type = entry.get("issue_type")
                raw_date = entry.get("date")
                if entry_type == issue_type and raw_date:
                    try:
                        d = datetime.fromisoformat(raw_date)
                        if d.tzinfo is None:
                            d = d.replace(tzinfo=timezone.utc)
                        if (cutoff - d).days <= _REPEAT_ISSUE_DAYS:
                            match_count += 1
                    except (ValueError, TypeError):
                        logger.warning(
                            "repeat_detection_parse_error",
                            date_raw=raw_date,
                        )
                        continue

            if match_count > _REPEAT_ISSUE_THRESHOLD:
                escalation_needed = True
                is_recurring = True
                logger.info(
                    "repeat_issue_detected",
                    issue_type=issue_type,
                    match_count=match_count,
                )
        except Exception as exc:
            logger.warning("repeat_detection_failed", error=str(exc))

    # ── 2. Refine confidence score ─────────────────────────────────
    # Base: data_completeness (weight 0.5)
    base = completeness * 0.5

    # Classification confidence (weight 0.3)
    if issue_type is None:
        cls_score = 0.0
    elif issue_type == "general_complaint":
        cls_score = 0.15  # half weight — least specific type
    else:
        cls_score = 0.3   # full weight — clearly classified

    # Context richness (weight 0.2)
    subsections = [ctx.get(k) for k in ("invoice", "order", "shipping", "history")]
    rich_count = sum(1 for s in subsections if s is not None)
    ctx_score = (rich_count / 4.0) * 0.2

    confidence_score = round(min(base + cls_score + ctx_score, 1.0), 2)

    # ── 3. Build prompt data ───────────────────────────────────────
    customer_message: str = state.get("issue_description", "") or ""
    rag_context: str = state.get("rag_context", "") or ""
    # Feature 005: the conversation transcript keeps issue-path replies coherent
    # with earlier turns (e.g. the customer's name) without inventing anything.
    conversation_history = _format_conversation_history(state.get("chat_history"))
    prompt_data = _build_prompt_data(
        ctx, lang, completeness, is_recurring, customer_message, rag_context, conversation_history
    )

    # ── 4. Generate response ───────────────────────────────────────
    # Fix 6: pure knowledge answers are already grounded by Mini-RAG — this step
    # only adds language/formatting polish, so use the faster model. Issue/hybrid
    # (CRM reasoning) keep the primary model.
    route = state.get("route", "customer_issue")
    llm = llm_fast if route == "general_knowledge" else llm_primary
    try:
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=prompt_data),
        ]
        result = await llm.ainvoke(messages)
        draft_response = result.content.strip() if result.content else ""
    except Exception as exc:
        logger.error("response_generation_failed", error=str(exc))
        draft_response = ""

    # ── 5. Graceful degradation — fallback if LLM failed or empty ─
    if not draft_response:
        draft_response = _build_fallback_response(lang, completeness, is_recurring)

    # Store the final response (Sprint 3: same as draft; Sprint 4 may differ after review)
    final_response = draft_response

    logger.info(
        "response_generated",
        language=lang,
        data_completeness=completeness,
        confidence_score=confidence_score,
        escalation_needed=escalation_needed,
        is_recurring=is_recurring,
        draft_length=len(draft_response),
    )

    return {
        "draft_response": draft_response,
        "final_response": final_response,
        "confidence_score": confidence_score,
        "escalation_needed": escalation_needed,
    }


# ── Helpers ─────────────────────────────────────────────────────────

def _format_conversation_history(chat_history: list[dict] | None, max_turns: int = 12) -> str:
    """Format the recent transcript as 'role: text' lines (oldest first).

    Returns "" when there is no history so the prompt is unchanged from before
    Feature 005 (graceful, single-turn behavior preserved).
    """
    if not chat_history:
        return ""
    recent = chat_history[-max_turns:]
    lines: list[str] = []
    for turn in recent:
        role = turn.get("role", "user")
        content = (turn.get("content", "") or "").strip().replace("\n", " ")
        if len(content) > 500:
            content = content[:500] + "…"
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def _build_prompt_data(
    ctx: dict,
    lang: str,
    completeness: float,
    is_recurring: bool,
    customer_message: str = "",
    rag_context: str = "",
    conversation_history: str = "",
) -> str:
    """Serialize context into a human-readable prompt block."""
    lines: list[str] = []
    lines.append(f"Customer language: {lang}")
    lines.append(f"IMPORTANT: Respond ONLY in {'Arabic' if lang == 'ar' else 'English'}. Do not switch languages.")
    lines.append(f"Data completeness tier: {_tier_label(completeness)}")
    if is_recurring:
        lines.append("NOTE: This is a RECURRING issue — append the escalation message.")
    lines.append("")

    if conversation_history:
        lines.append("## Recent conversation (for context — recall facts the customer already stated, e.g. their name; never invent)")
        lines.append(conversation_history)
        lines.append("")

    if customer_message:
        lines.append(f"Customer's original message: {customer_message}")
        lines.append("")

    if rag_context:
        lines.append("## Knowledge Base Answer")
        lines.append(rag_context)
        lines.append("")
        lines.append("(Use the knowledge base answer above to inform your response. Cite it naturally.)")
        lines.append("")

    customer_name = ctx.get("customer_name", "Customer")
    lines.append(f"Customer name: {customer_name}")

    invoice = ctx.get("invoice")
    if invoice:
        lines.append(f"Invoice number: {invoice.get('number', 'NOT AVAILABLE')}")
        lines.append(f"Invoice amount: {invoice.get('amount', 'NOT AVAILABLE')}")
        lines.append(f"Invoice status: {invoice.get('status', 'NOT AVAILABLE')}")
        lines.append(f"Invoice date: {invoice.get('date', 'NOT AVAILABLE')}")
    else:
        lines.append("Invoice: NOT AVAILABLE")

    order = ctx.get("order")
    if order:
        lines.append(f"Order ID: {order.get('id', 'NOT AVAILABLE')}")
        lines.append(f"Order status: {order.get('status', 'NOT AVAILABLE')}")
        lines.append(f"Order total: {order.get('total_amount', 'NOT AVAILABLE')}")
        lines.append(f"Estimated delivery: {order.get('estimated_delivery', 'NOT AVAILABLE')}")
    else:
        lines.append("Order: NOT AVAILABLE")

    shipping = ctx.get("shipping")
    if shipping and isinstance(shipping, list) and len(shipping) > 0:
        s = shipping[0]
        lines.append(f"Shipping carrier: {s.get('carrier', 'NOT AVAILABLE')}")
        lines.append(f"Tracking number: {s.get('tracking', 'NOT AVAILABLE')}")
        lines.append(f"Shipping status: {s.get('status', 'NOT AVAILABLE')}")
        lines.append(f"Current location: {s.get('location', 'NOT AVAILABLE')}")
    else:
        lines.append("Shipping: NOT AVAILABLE")

    history = ctx.get("history")
    if history:
        lines.append(f"Previous interactions count: {len(history)}")
        for h in history[:3]:
            lines.append(
                f"  - {h.get('date', '?')}: {h.get('issue_type', '?')} "
                f"({h.get('resolution', 'no details')})"
            )
    else:
        lines.append("History: NOT AVAILABLE")

    lines.append("")
    lines.append("---")
    lines.append(
        "Generate a response following the rules in the system prompt. "
        "Use plain text only. Be warm and helpful."
    )
    return "\n".join(lines)


def _tier_label(completeness: float) -> str:
    if completeness >= 1.0:
        return "FULL DATA (Tier A)"
    if completeness > 0.0:
        return "PARTIAL DATA (Tier B)"
    return "NO DATA (Tier C)"


def _build_fallback_response(lang: str, completeness: float, is_recurring: bool) -> str:
    """Build a static fallback when the LLM call fails."""
    is_ar = lang == "ar"

    if completeness >= 1.0:
        # Full data fallback — generic but acknowledges the query
        msg = _FALLBACK_AR if is_ar else _FALLBACK_EN
    elif completeness > 0.0:
        # Partial data
        parts = [_PARTIAL_DATA_AR if is_ar else _PARTIAL_DATA_EN]
        msg = " ".join(parts)
    else:
        # No data
        msg = _NO_DATA_AR if is_ar else _NO_DATA_EN

    if is_recurring:
        esc = _ESCALATION_MSG_AR if is_ar else _ESCALATION_MSG_EN
        msg = msg + " " + esc

    return msg

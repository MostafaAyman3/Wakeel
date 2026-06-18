"""
InputParserNode — entry point of the M3 graph.

Responsibilities (M3 Sprint 1):
    1. Detect language (AR/EN) from the raw customer message.
    2. Extract { identifier_type, identifier_value } and a clean
       issue_description using GPT-4o-mini (structured output).
    3. Fall back to regex extraction of the reference number if the LLM
       fails or returns an empty/invalid value.
    4. If a pre-supplied identifier was passed by the API, trust it and
       skip extraction of the identifier (still cleans the description).
    5. If no identifier can be determined at all → escalation_needed = True.

Blueprint reference: section 3.4 — Input Parser Node.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from agents.shared.llm_client import llm_fast
from agents.shared.language import detect_language
from agents.m3.schemas.m3_state import M3State
from agents.prompts.input_parser import INPUT_PARSER_SYSTEM_PROMPT
from backend.core.logging import get_logger

logger = get_logger(__name__)

VALID_IDENTIFIER_TYPES: set[str] = {"order_id", "invoice_id", "customer_id"}

# Regex fallback — maps a reference prefix to its identifier type.
# Generic shape: 2-5 leading letters, then hyphen/alnum groups.
_REGEX_PATTERNS: list[tuple[str, str]] = [
    ("order_id", r"\b(?:ORD|DEL|TRK)[-A-Z0-9]+\b"),
    ("invoice_id", r"\bINV[-A-Z0-9]+\b"),
    ("customer_id", r"\b(?:CUST|CUS)[-A-Z0-9]+\b"),
]


class ParsedInput(BaseModel):
    """Structured output returned by the parser LLM."""

    identifier_type: str = Field(
        description="Exactly one of: order_id, invoice_id, customer_id",
    )
    identifier_value: str = Field(
        default="",
        description="The reference string verbatim, or '' if none present",
    )
    issue_description: str = Field(
        default="",
        description="Concise English summary of the customer's problem",
    )


def _regex_fallback(text: str) -> dict | None:
    """Best-effort identifier extraction via prefix regex.

    Returns ``{"type": ..., "value": ...}`` or ``None`` if nothing matches.
    """
    upper = text.upper()
    for id_type, pattern in _REGEX_PATTERNS:
        match = re.search(pattern, upper)
        if match:
            return {"type": id_type, "value": match.group(0)}
    return None


async def parse_input(state: M3State) -> dict:
    """Parse the customer's free-form message into structured fields.

    Always returns a partial state update. Never raises — a parse failure
    flips ``escalation_needed`` so the pipeline degrades gracefully instead
    of crashing.
    """
    raw_text: str = state.get("issue_description") or ""
    preset_identifier: dict = state.get("customer_identifier") or {}
    language: str = state.get("language", "") or ""

    # ── 1. Language detection ─────────────────────────────────────
    if not language or language == "auto":
        language = detect_language(raw_text)

    # ── 2. Trust a pre-supplied identifier from the API, if valid ─
    if (
        preset_identifier.get("type") in VALID_IDENTIFIER_TYPES
        and preset_identifier.get("value")
    ):
        logger.info(
            "input_parser_preset_identifier",
            identifier_type=preset_identifier["type"],
        )
        return {
            "language": language,
            "customer_identifier": {
                "type": preset_identifier["type"],
                "value": str(preset_identifier["value"]).strip(),
            },
            "issue_description": raw_text,
        }

    # ── 3. LLM extraction (primary path) ──────────────────────────
    identifier: dict | None = None
    issue_description = raw_text

    messages = [
        SystemMessage(content=INPUT_PARSER_SYSTEM_PROMPT),
        HumanMessage(content=f"Customer message ({language}): {raw_text}"),
    ]
    parser = llm_fast.with_structured_output(ParsedInput, method="function_calling")

    try:
        result: ParsedInput = await parser.ainvoke(messages)
        if result.issue_description:
            issue_description = result.issue_description
        if (
            result.identifier_type in VALID_IDENTIFIER_TYPES
            and result.identifier_value.strip()
        ):
            identifier = {
                "type": result.identifier_type,
                "value": result.identifier_value.strip(),
            }
    except Exception as exc:  # noqa: BLE001 — graceful degradation by design
        logger.warning("input_parser_llm_failed", error=str(exc))

    # ── 4. Regex fallback when the LLM gave no usable identifier ──
    if identifier is None:
        identifier = _regex_fallback(raw_text)
        if identifier:
            logger.info("input_parser_regex_fallback", identifier=identifier)

    # ── 5. No identifier at all → escalate (graceful degradation) ─
    if identifier is None:
        logger.warning("input_parser_no_identifier", text_preview=raw_text[:80])
        return {
            "language": language,
            "customer_identifier": {},
            "issue_description": issue_description,
            "escalation_needed": True,
            "error": "no_identifier_found",
        }

    logger.info(
        "input_parser_ok",
        identifier_type=identifier["type"],
        language=language,
    )
    return {
        "language": language,
        "customer_identifier": identifier,
        "issue_description": issue_description,
    }

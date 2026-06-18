"""
InputParserNode — extracts identifier and issue description from free-form customer text.

Uses GPT-4o-mini with structured output.
Entry point of the M3 graph.

Blueprint reference: M3_Sprints.md Sprint 1 — InputParserNode
"""

from __future__ import annotations

import structlog
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from agents.m3.schemas.m3_state import M3State
from agents.shared.llm_client import llm_fast

logger = structlog.get_logger(__name__)


class ParsedInput(BaseModel):
    """Structured output schema for the input parser."""
    identifier_type: str = Field(
        description="Exactly one of: order_id, invoice_id, customer_id"
    )
    identifier_value: str = Field(
        description="The identifier value extracted from the query"
    )
    issue_description: str = Field(
        description="The customer's issue description in their own words"
    )
    reasoning: str = Field(
        default="",
        description="One-sentence justification for the extraction"
    )


SYSTEM_PROMPT = """\
You are the Input Parser for a Customer Support Agent.
Extract structured information from the customer's free-form message.

Return a JSON object with:
1. **identifier_type** — exactly one of: "order_id", "invoice_id", "customer_id"
   - If the customer provides an order number (e.g. ORD-2024-1567), use "order_id"
   - If they provide an invoice number (e.g. INV-890), use "invoice_id"
   - If they provide a customer ID (e.g. CUST-001), use "customer_id"
   - If the type is ambiguous, choose the most likely one based on the format
2. **identifier_value** — the actual identifier string
3. **issue_description** — the customer's description of their problem
4. **reasoning** — brief justification

Rules:
- Always extract the identifier even if it's embedded in a sentence
- The issue_description should capture the full customer concern
- If no identifier is found, set identifier_type to "customer_id" and identifier_value to "unknown"
"""


def _detect_language(text: str) -> str:
    """Auto-detect Arabic vs English using Unicode range."""
    return "ar" if any("\u0600" <= c <= "\u06FF" for c in text) else "en"


async def parse_input(state: M3State) -> dict:
    """Extract identifier and issue from customer text.

    Falls back gracefully on any LLM error.
    """
    query: str = state.get("issue_description", "")
    language: str = _detect_language(query)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Customer message: {query}"),
    ]

    parser = llm_fast.with_structured_output(ParsedInput, method="function_calling")

    try:
        result: ParsedInput = await parser.ainvoke(messages)
        identifier_type = result.identifier_type
        if identifier_type not in ("order_id", "invoice_id", "customer_id"):
            identifier_type = "customer_id"

        return {
            "customer_identifier": {
                "type": identifier_type,
                "value": result.identifier_value,
            },
            "issue_description": result.issue_description or query,
            "language": language,
        }

    except Exception as exc:
        logger.error("input_parser_failed", error=str(exc))
        return {
            "customer_identifier": {"type": "customer_id", "value": "unknown"},
            "issue_description": query,
            "language": language,
            "error": f"Input parsing failed: {exc}",
        }

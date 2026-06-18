"""
IssueClassifierNode — classifies customer issue type using GPT-4o-mini.

Issue types:
  status_inquiry / billing_dispute / shipping_issue / refund_request / general_complaint

Also sets priority: High / Medium / Low

Blueprint reference: M3_Sprints.md Sprint 2 — IssueClassifierNode
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from agents.m3.schemas.m3_state import M3State
from agents.shared.llm_client import llm_fast
from backend.core.logging import get_logger

logger = get_logger(__name__)


class IssueClassification(BaseModel):
    """Structured output from the LLM."""
    issue_type: str = Field(
        description="Exactly one of: status_inquiry, billing_dispute, shipping_issue, refund_request, general_complaint"
    )
    priority: str = Field(
        description="Priority level: High, Medium, or Low"
    )
    reasoning: str = Field(
        default="",
        description="One-sentence justification for the classification"
    )


VALID_ISSUE_TYPES = frozenset({
    "status_inquiry",
    "billing_dispute",
    "shipping_issue",
    "refund_request",
    "general_complaint",
})

VALID_PRIORITIES = frozenset({"High", "Medium", "Low"})


SYSTEM_PROMPT = """\
You are an Issue Classifier for a Customer Support Agent.
Analyze the customer's issue description and the context of their interaction.

Classify the issue into exactly ONE of the following types:

1. **status_inquiry** — Customer is asking about the status of their order, invoice,
   or shipment. They want to know "where is my order" or "what is the status".
   Examples: "أين طلبي؟", "What's the status of my order?", "Is my order shipped?"

2. **billing_dispute** — Customer disputes a charge, claims they didn't order
   something, questions an amount, or disagrees with an invoice total.
   Examples: "أنا ما طلبتش المنتج ده", "I was charged twice", "Why is the amount wrong?"

3. **shipping_issue** — Problem with delivery: delayed shipment, wrong address,
   damaged package, lost item, carrier issue.
   Examples: "الطلب متأخر", "My package hasn't arrived", "Item arrived damaged"

4. **refund_request** — Customer explicitly asks for a refund or return.
   Examples: "عايز استرد فلوسي", "I want a refund", "How do I return this?"

5. **general_complaint** — None of the above. General questions, complaints about
   service, product quality issues, or unclear concerns.
   Examples: "المنتج مش كويس", "I'm not satisfied with your service", "Hello?"

Also assign a priority:
- **High**: billing disputes, refund requests, shipping delays past delivery date
- **Medium**: status inquiries for past-due items, general complaints
- **Low**: simple status inquiries, general information requests

Return valid JSON matching the schema.
"""


async def classify_issue(state: M3State) -> dict:
    """Classify the customer's issue type and priority.

    Falls back gracefully to general_complaint / Medium on error.
    """
    query: str = state.get("issue_description", "")
    fetched: dict = state.get("fetched_data", {})

    # Build a compact summary of available data for context
    data_summary_parts = []
    if fetched.get("invoice"):
        inv = fetched["invoice"]
        data_summary_parts.append(f"Invoice: {inv.get('display_id', 'N/A')} ({inv.get('payment_status', 'N/A')})")
    if fetched.get("order"):
        ord_data = fetched["order"]
        data_summary_parts.append(f"Order: {ord_data.get('display_id', 'N/A')} ({ord_data.get('status', 'N/A')})")
    if fetched.get("shipping"):
        ship = fetched["shipping"]
        if isinstance(ship, list):
            for s in ship:
                data_summary_parts.append(f"Shipping: {s.get('tracking_id', 'N/A')} ({s.get('status', 'N/A')})")
        elif isinstance(ship, dict):
            data_summary_parts.append(f"Shipping: {ship.get('tracking_id', 'N/A')} ({ship.get('status', 'N/A')})")
    data_summary = " | ".join(data_summary_parts) if data_summary_parts else "No data available"

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Customer message: {query}\nAvailable data: {data_summary}"),
    ]

    classifier = llm_fast.with_structured_output(IssueClassification, method="function_calling")

    try:
        result: IssueClassification = await classifier.ainvoke(messages)

        issue_type = result.issue_type if result.issue_type in VALID_ISSUE_TYPES else "general_complaint"
        priority = result.priority if result.priority in VALID_PRIORITIES else "Medium"

        return {
            "issue_type": issue_type,
            "issue_priority": priority,
        }

    except Exception as exc:
        logger.error("issue_classifier_failed", error=str(exc))
        return {
            "issue_type": "general_complaint",
            "issue_priority": "Medium",
            "error": f"Issue classification failed: {exc}",
        }

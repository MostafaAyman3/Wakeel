"""
AwaitOffersNode — pauses the graph after the RFQ is sent, waiting for
supplier offers to arrive via POST /api/v1/m2/offers.

Uses LangGraph's interrupt() primitive (explicit, inside the node):
  1. rfq_send_node finishes → graph enters this node.
  2. interrupt() is called — graph pauses, state is checkpointed.
  3. POST /api/v1/m2/offers arrives with offer data:
       await graph.ainvoke(
           Command(resume={"supplier_offers": [...]}),
           config={"configurable": {"thread_id": rfq.thread_id}}
       )
  4. interrupt() returns the resume payload.
  5. Node extracts supplier_offers and returns them to state.
  6. Graph continues → offer_analysis_node.

The interrupt payload (shown to the Dashboard) tells the frontend which
thread is waiting so the offers form can be pre-filled with the rfq_id.
"""

from typing import Any, Dict

from langgraph.types import interrupt

from agents.m2.schemas.m2_state import M2State


async def await_offers_node(state: M2State) -> Dict[str, Any]:
    """
    Pauses graph execution and waits for supplier offers.
    Returns the offers that were submitted via the resume payload.
    """
    rfq_id = state.get("rfq_id", "")
    current_product = state.get("current_product", {})

    # Pause — graph sleeps until POST /api/v1/m2/offers calls
    # graph.ainvoke(Command(resume={"supplier_offers": [...]}), config)
    resume_payload = interrupt({
        "event": "awaiting_supplier_offers",
        "rfq_id": rfq_id,
        "thread_id": state.get("thread_id", ""),
        "product_name": current_product.get("name", ""),
        "product_sku": current_product.get("sku", ""),
        "suggested_quantity": current_product.get("suggested_quantity", 0),
        "instructions": (
            "Submit supplier offers via POST /api/v1/m2/offers "
            f"with rfq_id={rfq_id}"
        ),
    })

    # Graph resumes — resume_payload is whatever was passed to Command(resume=...)
    offers = []
    if isinstance(resume_payload, dict):
        offers = resume_payload.get("supplier_offers", [])

    return {"supplier_offers": offers}

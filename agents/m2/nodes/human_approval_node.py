"""
HumanApprovalNode — reads the manager's approval decision from state.

This node is placed after rfq_builder_node in the graph and the graph is
compiled with interrupt_before=["human_approval_node"].

Flow:
  1. POST /api/v1/m2/analyze runs graph → rfq_builder_node saves RFQ + thread_id
     → graph pauses BEFORE this node (interrupt_before) → ainvoke returns
  2. Manager sees the RFQ draft on the Dashboard and clicks Approve / Reject
  3. POST /api/v1/m2/rfqs/{rfq_id}/approve calls:
       graph.aupdate_state(config, {"approval_status": ..., "approval_notes": ...})
       graph.ainvoke(None, config=config)
  4. Graph resumes — this node reads approval_status from state and returns it
  5. route_after_approval decides: approved → rfq_send_node, rejected → END
"""

from typing import Any, Dict

from agents.m2.schemas.m2_state import M2State


async def human_approval_node(state: M2State) -> Dict[str, Any]:
    """
    Reads approval_status injected by the approve API before graph resumption.
    No LLM call — pure state passthrough.
    """
    approval_status = state.get("approval_status", "rejected")
    approval_notes = state.get("approval_notes", "")

    return {
        "approval_status": approval_status,
        "approval_notes": approval_notes,
    }

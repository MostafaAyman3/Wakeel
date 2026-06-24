"""
FinalApprovalNode — second human approval gate after offer analysis.

Same pattern as HumanApprovalNode (Sprint 6), compiled with
interrupt_before=["final_approval_node"].

Flow:
  1. offer_analysis_node completes → graph pauses BEFORE this node.
     Checkpointed state includes recommended_offer + justification.
  2. Manager reviews the recommendation on the Dashboard.
  3. POST /api/v1/m2/rfqs/{rfq_id}/approve calls:
       graph.aupdate_state(config, {"approval_status": ..., "approval_notes": ...})
       graph.ainvoke(None, config=config)
  4. This node runs — reads the decision from state and returns it.
  5. Graph ends.
"""

from typing import Any, Dict

from agents.m2.schemas.m2_state import M2State


async def final_approval_node(state: M2State) -> Dict[str, Any]:
    """
    Reads the final approval decision injected via aupdate_state() before resume.
    Records which offer was approved/rejected alongside the decision.
    """
    approval_status = state.get("approval_status", "rejected")
    approval_notes = state.get("approval_notes", "")
    recommended = state.get("recommended_offer", {})

    return {
        "approval_status": approval_status,
        "approval_notes": approval_notes,
        "final_response": {
            **state.get("final_response", {}),
            "final_approval": approval_status,
            "approved_vendor": recommended.get("vendor_name") if approval_status == "approved" else None,
            "approved_offer_score": recommended.get("score"),
        },
    }

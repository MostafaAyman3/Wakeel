"""
M2 LangGraph — Procurement & Inventory Agent (Sprint 7 — full async loop).

Complete procurement path:
  START
    └─ route_detection
        ├─ low_stock / predicted_shortage
        │    alert_generator_node
        │      → rfq_builder_node
        │          → [interrupt_before] human_approval_node   ← 1st approval
        │                → route_after_first_approval
        │                      ├─ approved → rfq_send_node
        │                      │               → await_offers_node  [interrupt()]
        │                      │                   → offer_analysis_node  (GPT-4o)
        │                      │                       → [interrupt_before] final_approval_node
        │                      │                             → END
        │                      └─ rejected → END
        └─ slow_moving / near_expiry → END  (pricing path, Sprint 5)

Two interrupt mechanisms are used:
  ┌─ interrupt_before=["human_approval_node", "final_approval_node"]
  │    Graph pauses automatically BEFORE these nodes.
  │    Resume: graph.aupdate_state(config, decision) then graph.ainvoke(None, config)
  └─ interrupt() inside await_offers_node
       Graph pauses INSIDE the node, waiting for offers.
       Resume: graph.ainvoke(Command(resume={"supplier_offers": [...]}), config)

Checkpointer:
  Default   → MemorySaver (in-process, tests + dev)
  Production → AsyncPostgresSaver via build_m2_app_with_checkpointer()
"""

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agents.m2.nodes.alert_generator_node import alert_generator_node
from agents.m2.nodes.await_offers_node import await_offers_node
from agents.m2.nodes.final_approval_node import final_approval_node
from agents.m2.nodes.human_approval_node import human_approval_node
from agents.m2.nodes.offer_analysis_node import offer_analysis_node
from agents.m2.nodes.rfq_builder_node import rfq_builder_node
from agents.m2.nodes.rfq_send_node import rfq_send_node
from agents.m2.nodes.pricing_advisor_node import pricing_advisor_node
from agents.m2.schemas.m2_state import M2State

# ── Routing functions ─────────────────────────────────────────────

def route_detection(state: M2State) -> Literal["alert_generator_node", "pricing_advisor_node", "__end__"]:
    dt = state.get("detection_type")
    if dt in ("low_stock", "predicted_shortage"):
        return "alert_generator_node"
    elif dt in ["slow_moving", "near_expiry"]:
        return "pricing_advisor_node"
    return END


def route_after_first_approval(
    state: M2State,
) -> Literal["rfq_send_node", "__end__"]:
    """After 1st HumanApprovalNode: approved → send RFQ; rejected → stop."""
    if state.get("approval_status") == "approved":
        return "rfq_send_node"
    return END


# ── Graph definition ──────────────────────────────────────────────

def _build_workflow() -> StateGraph:
    wf = StateGraph(M2State)

    # ── Nodes ─────────────────────────────────────────────────────
    wf.add_node("alert_generator_node", alert_generator_node)
    wf.add_node("rfq_builder_node",     rfq_builder_node)
    wf.add_node("human_approval_node",  human_approval_node)   # 1st gate
    wf.add_node("rfq_send_node",        rfq_send_node)
    wf.add_node("await_offers_node",    await_offers_node)     # explicit interrupt()
    wf.add_node("offer_analysis_node",  offer_analysis_node)
    wf.add_node("final_approval_node",  final_approval_node)   # 2nd gate
    wf.add_node("pricing_advisor_node", pricing_advisor_node)  # Sprint 5

    # ── Edges ─────────────────────────────────────────────────────
    wf.add_conditional_edges(
        START,
        route_detection,
        {
            "alert_generator_node": "alert_generator_node",
            "pricing_advisor_node": "pricing_advisor_node",
            END: END,
        },
    )
    wf.add_edge("alert_generator_node", "rfq_builder_node")
    wf.add_edge("rfq_builder_node",     "human_approval_node")
    wf.add_conditional_edges(
        "human_approval_node",
        route_after_first_approval,
        {"rfq_send_node": "rfq_send_node", END: END},
    )
    wf.add_edge("rfq_send_node",        "await_offers_node")
    wf.add_edge("await_offers_node",    "offer_analysis_node")
    wf.add_edge("offer_analysis_node",  "final_approval_node")
    wf.add_edge("final_approval_node",  END)
    wf.add_edge("pricing_advisor_node", END)

    return wf


_workflow = _build_workflow()

# ── Compiled instances ────────────────────────────────────────────

# Default — MemorySaver (dev / tests).
# interrupt_before pauses the graph before the two human-gate nodes.
# await_offers_node handles its own pause via interrupt() internally.
m2_app = _workflow.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["human_approval_node", "final_approval_node"],
)

def build_m2_app_with_checkpointer(checkpointer):
    """
    Production compile backed by AsyncPostgresSaver.
    Call once in FastAPI lifespan; store result in app.state.m2_graph.
    """
    return _workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval_node", "final_approval_node"],
    )

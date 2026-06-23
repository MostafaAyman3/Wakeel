"""
M2 LangGraph — Procurement & Inventory Agent graph.

Node sequence (procurement path):
  START
    └─ route_detection
        ├─ low_stock / predicted_shortage
        │     alert_generator_node
        │       └─ rfq_builder_node
        │             └─ [INTERRUPT] human_approval_node   ← pauses here
        │                   └─ route_after_approval
        │                         ├─ approved → rfq_send_node → END
        │                         └─ rejected → END
        └─ slow_moving / near_expiry → END  (pricing path, Sprint 5)

Checkpointing strategy
─────────────────────
The graph is compiled with interrupt_before=["human_approval_node"]:
  • First ainvoke()  → runs alert_generator + rfq_builder, then PAUSES.
    The checkpointer saves full state (including rfq_draft, rfq_id, thread_id).
    ainvoke returns that state.
  • API POST /rfqs/{id}/approve calls:
      await graph.aupdate_state(config, {"approval_status": ..., "approval_notes": ...})
      await graph.ainvoke(None, config=config)
  • Second ainvoke() → resumes into human_approval_node (reads state), then
    route_after_approval → rfq_send_node → END.

Default compile (m2_app) uses MemorySaver — state is in-process only.
Production compile (build_m2_app_with_checkpointer) uses AsyncPostgresSaver.
"""

from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agents.m2.nodes.alert_generator_node import alert_generator_node
from agents.m2.nodes.human_approval_node import human_approval_node
from agents.m2.nodes.rfq_builder_node import rfq_builder_node
from agents.m2.nodes.rfq_send_node import rfq_send_node
from agents.m2.schemas.m2_state import M2State


# ── Routing ───────────────────────────────────────────────────────

def route_detection(state: M2State) -> Literal["alert_generator_node", "__end__"]:
    dt = state.get("detection_type")
    if dt in ("low_stock", "predicted_shortage"):
        return "alert_generator_node"
    return END


def route_after_approval(
    state: M2State,
) -> Literal["rfq_send_node", "__end__"]:
    if state.get("approval_status") == "approved":
        return "rfq_send_node"
    return END


# ── Graph ─────────────────────────────────────────────────────────

def _build_workflow() -> StateGraph:
    wf = StateGraph(M2State)

    wf.add_node("alert_generator_node", alert_generator_node)
    wf.add_node("rfq_builder_node", rfq_builder_node)
    wf.add_node("human_approval_node", human_approval_node)
    wf.add_node("rfq_send_node", rfq_send_node)

    wf.add_conditional_edges(
        START,
        route_detection,
        {"alert_generator_node": "alert_generator_node", END: END},
    )
    wf.add_edge("alert_generator_node", "rfq_builder_node")
    wf.add_edge("rfq_builder_node", "human_approval_node")
    wf.add_conditional_edges(
        "human_approval_node",
        route_after_approval,
        {"rfq_send_node": "rfq_send_node", END: END},
    )
    wf.add_edge("rfq_send_node", END)

    return wf


_workflow = _build_workflow()

# Default in-memory compile — used by tests and the /analyze endpoint
# when no PostgresSaver is available.  State survives within one process only.
m2_app = _workflow.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["human_approval_node"],
)


def build_m2_app_with_checkpointer(checkpointer):
    """
    Returns a compiled graph backed by the given checkpointer (AsyncPostgresSaver).
    Call once in FastAPI lifespan and store the result in app.state.m2_graph.
    """
    return _workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_approval_node"],
    )

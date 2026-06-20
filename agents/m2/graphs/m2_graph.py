import structlog
from langgraph.graph import StateGraph, END
from agents.m2.schemas.m2_state import M2State
from agents.m2.nodes.inventory_check_node import inventory_check_node
from agents.m2.nodes.alert_generation_node import alert_generation_node
from agents.m2.nodes.rfq_builder_node import rfq_builder_node

logger = structlog.get_logger(__name__)

def build_m2_graph() -> StateGraph:
    builder = StateGraph(M2State)

    builder.add_node("inventory_check", inventory_check_node)
    builder.add_node("alert_generation", alert_generation_node)
    builder.add_node("rfq_builder", rfq_builder_node)

    builder.set_entry_point("inventory_check")
    
    def route_after_check(state: M2State) -> str:
        if not state.get("low_stock_items"):
            return END
        return "alert_generation"

    builder.add_conditional_edges("inventory_check", route_after_check)
    builder.add_edge("alert_generation", "rfq_builder")
    builder.add_edge("rfq_builder", END)

    return builder.compile()

m2_graph = build_m2_graph()

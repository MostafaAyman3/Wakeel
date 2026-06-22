from langgraph.graph import StateGraph, START, END
from typing import Literal

from agents.m2.schemas.m2_state import M2State
from agents.m2.nodes.alert_generator_node import alert_generator_node
from agents.m2.nodes.rfq_builder_node import rfq_builder_node

def route_detection(state: M2State) -> Literal["alert_generator_node", "__end__"]:
    """
    Routes the execution based on the detection type of the current_product.
    - Procurement path (low_stock, predicted_shortage) -> alert_generator_node
    - Pricing path (slow_moving, near_expiry) -> Ends for now (Sprint 5 will add PricingAdvisorNode)
    """
    dt = state.get("detection_type")
    if dt in ["low_stock", "predicted_shortage"]:
        return "alert_generator_node"
    return END

# Initialize the StateGraph
workflow = StateGraph(M2State)

# Add Nodes
workflow.add_node("alert_generator_node", alert_generator_node)
workflow.add_node("rfq_builder_node", rfq_builder_node)

# Add Edges
workflow.add_conditional_edges(
    START, 
    route_detection, 
    {
        "alert_generator_node": "alert_generator_node",
        END: END
    }
)

workflow.add_edge("alert_generator_node", "rfq_builder_node")
workflow.add_edge("rfq_builder_node", END)

# Compile the graph
m2_app = workflow.compile()

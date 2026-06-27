"""M1 graphs: legacy compatibility graph and stratified analyst graph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.m1.nodes.clarification_node import clarify
from agents.m1.nodes.context_loader_node import load_context
from agents.m1.nodes.context_saver_node import save_context
from agents.m1.nodes.followup_resolver_node import resolve_followup, route_followup
from agents.m1.nodes.intent_classifier_node import classify_intent
from agents.m1.nodes.intent_router_node import route_intent, route_to_tier
from agents.m1.nodes.invoice_analysis_tool_node import invoice_analysis_tool
from agents.m1.nodes.narrative_generator_node import generate_narrative
from agents.m1.nodes.output_selector_node import select_output
from agents.m1.nodes.chart_config_node import chart_config_node
from agents.m1.nodes.result_evaluator_node import result_evaluator_node
from agents.m1.nodes.router_node import route_by_intent
from agents.m1.nodes.t0_conversation_node import t0_conversation
from agents.m1.nodes.t3_aggregator_node import aggregate_results
from agents.m1.nodes.t3_executor_node import execute_plan
from agents.m1.nodes.t3_planner_node import plan_analysis
from agents.m1.nodes.t5_oos_node import t5_out_of_scope
from agents.m1.nodes.t6_m3_delegation_node import delegate_to_m3
from agents.m1.nodes.tax_rag_node import tax_rag_node
from agents.m1.nodes.validation_enrichment_node import validate_and_enrich
from agents.m1.schemas.m1_state import M1State
from agents.m1.tools.db_query_tool import db_query_tool
from backend.core.config import get_settings


def build_legacy_m1_graph():
    """The pre-migration graph, retained as an immediate rollback path."""
    graph = StateGraph(M1State)
    graph.add_node("intent_classifier", classify_intent)
    graph.add_node("clarification", clarify)
    graph.add_node("db_query_tool", db_query_tool)
    graph.add_node("invoice_analysis_tool", invoice_analysis_tool)
    graph.add_node("tax_rag_node", tax_rag_node)
    graph.add_node("validation_enrichment", validate_and_enrich)
    graph.add_node("output_selector", select_output)
    graph.add_node("chart_config", chart_config_node)
    graph.add_node("narrative_generator", generate_narrative)

    graph.add_edge(START, "intent_classifier")
    graph.add_conditional_edges(
        "intent_classifier",
        route_by_intent,
        {
            "clarification": "clarification",
            "db_query_tool": "db_query_tool",
            "invoice_analysis_tool": "invoice_analysis_tool",
            "tax_rag_node": "tax_rag_node",
        },
    )
    graph.add_edge("clarification", END)
    for tool in ("db_query_tool", "invoice_analysis_tool", "tax_rag_node"):
        graph.add_edge(tool, "validation_enrichment")
    graph.add_edge("validation_enrichment", "output_selector")
    graph.add_edge("output_selector", "chart_config")
    graph.add_edge("chart_config", "narrative_generator")
    graph.add_edge("narrative_generator", END)
    return graph.compile()


def _route_t1_domain(state: M1State) -> str:
    domain = state.get("domain_intent", "")
    if domain == "invoice":
        return "invoice"
    if domain == "tax":
        return "tax"
    return "db"


async def _t1_dispatcher(state: M1State) -> dict:
    """No-op graph node used only to dispatch T1 by business domain."""
    return {}


def _route_after_evaluation(state: M1State) -> str:
    # V1 always produces a controlled response. T3 performs its own bounded
    # repair before reaching this shared evaluator.
    return "respond"


def build_stratified_m1_graph():
    """Build the Option C stratified Data Analyst Copilot graph."""
    graph = StateGraph(M1State)

    graph.add_node("context_loader", load_context)
    graph.add_node("intent_router", route_intent)

    graph.add_node("t0_conversation", t0_conversation)
    graph.add_node("t1_dispatcher", _t1_dispatcher)
    graph.add_node("t1_db_query", db_query_tool)
    graph.add_node("t1_invoice", invoice_analysis_tool)
    graph.add_node("t1_tax", tax_rag_node)
    graph.add_node("t2_resolver", resolve_followup)
    graph.add_node("t3_planner", plan_analysis)
    graph.add_node("t3_executor", execute_plan)
    graph.add_node("t3_aggregator", aggregate_results)
    graph.add_node("t4_clarification", clarify)
    graph.add_node("t5_oos", t5_out_of_scope)
    graph.add_node("t6_delegate_m3", delegate_to_m3)

    graph.add_node("result_evaluator", result_evaluator_node)
    graph.add_node("validation_enrichment", validate_and_enrich)
    graph.add_node("output_selector", select_output)
    graph.add_node("chart_config", chart_config_node)
    graph.add_node("narrative_generator", generate_narrative)
    graph.add_node("context_saver", save_context)

    graph.add_edge(START, "context_loader")
    graph.add_edge("context_loader", "intent_router")
    graph.add_conditional_edges(
        "intent_router",
        route_to_tier,
        {
            "T0": "t0_conversation",
            "T1": "t1_dispatcher",
            "T2": "t2_resolver",
            "T3": "t3_planner",
            "T4": "t4_clarification",
            "T5": "t5_oos",
            "T6": "t6_delegate_m3",
        },
    )

    graph.add_conditional_edges(
        "t1_dispatcher",
        _route_t1_domain,
        {
            "db": "t1_db_query",
            "invoice": "t1_invoice",
            "tax": "t1_tax",
        },
    )
    graph.add_edge("t1_db_query", "result_evaluator")
    graph.add_edge("t1_invoice", "result_evaluator")
    graph.add_edge("t1_tax", "result_evaluator")

    graph.add_conditional_edges(
        "t2_resolver",
        route_followup,
        {
            "reason": "output_selector",
            "requery": "t3_planner",
        },
    )

    graph.add_edge("t3_planner", "t3_executor")
    graph.add_edge("t3_executor", "t3_aggregator")
    graph.add_edge("t3_aggregator", "result_evaluator")

    graph.add_conditional_edges(
        "result_evaluator",
        _route_after_evaluation,
        {"respond": "validation_enrichment"},
    )
    graph.add_edge("validation_enrichment", "output_selector")
    graph.add_edge("output_selector", "chart_config")
    graph.add_edge("chart_config", "narrative_generator")

    for final_node in (
        "t0_conversation",
        "t4_clarification",
        "t5_oos",
        "t6_delegate_m3",
        "narrative_generator",
    ):
        graph.add_edge(final_node, "context_saver")
    graph.add_edge("context_saver", END)
    return graph.compile()


settings = get_settings()
m1_graph = (
    build_stratified_m1_graph()
    if settings.m1_stratified_router_enabled
    else build_legacy_m1_graph()
)

# Backward-compatible public builder now follows the active feature flag.
def build_m1_graph():
    return (
        build_stratified_m1_graph()
        if get_settings().m1_stratified_router_enabled
        else build_legacy_m1_graph()
    )

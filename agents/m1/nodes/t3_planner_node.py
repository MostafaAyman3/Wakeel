"""Create a bounded, structured analytical plan for T3."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.m1.schemas.analysis_models import AnalyticalPlan, PlanStep
from agents.m1.schemas.m1_state import M1State
from agents.prompts.m1_planner import M1_PLANNER_SYSTEM_PROMPT
from agents.shared.llm_client import llm_primary
from agents.m1.tools.schema_catalog import get_schema_catalog
from agents.m1.tools.db_query_tool import TEMPLATES


async def plan_analysis(state: M1State) -> dict:
    planner = llm_primary.with_structured_output(
        AnalyticalPlan,
        method="function_calling",
    )
    
    schema_str = get_schema_catalog().get_schema_string()
    templates_str = ", ".join(TEMPLATES.keys())

    prompt = (
        f"Question: {state.get('query', '')}\n"
        f"Domain: {state.get('domain_intent', '')}\n"
        "Analysis frame: "
        f"{json.dumps(state.get('analysis_frame', {}), ensure_ascii=False)}\n\n"
        "Available Templates:\n"
        f"{templates_str}\n\n"
        "Database Schema:\n"
        f"{schema_str}\n"
    )
    try:
        plan = await planner.ainvoke(
            [
                SystemMessage(content=M1_PLANNER_SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
    except Exception:
        plan = AnalyticalPlan(
            steps=[
                PlanStep(
                    id="step_1",
                    purpose=state.get("query", ""),
                    preferred_tool="nl2sql",
                    expected_columns=[],
                    expected_grain="unknown",
                )
            ],
            final_synthesis="Answer the original question from the retrieved evidence.",
        )

    # Hard-bound even if a model returns an overlong plan.
    steps = plan.steps[:4]
    return {
        "react_plan": [step.model_dump() for step in steps],
        "react_iteration": 0,
        "db_execution_count": 0,
        "tool_results": [],
        "react_done": False,
        "react_exit_reason": "",
    }


"""Aggregate bounded T3 step results for shared evaluation and rendering."""

from __future__ import annotations

from agents.m1.schemas.m1_state import M1State


async def aggregate_results(state: M1State) -> dict:
    aggregated: list[dict] = []
    failures: list[str] = []
    for result in state.get("tool_results", []):
        step = result.get("step", {})
        step_id = step.get("id", "step")
        if result.get("status") == "complete":
            for row in result.get("rows", []):
                aggregated.append({"_analysis_step": step_id, **row})
        elif result.get("status") not in {"deferred_to_aggregator"}:
            failures.append(
                f"{step_id}: {result.get('error_category', 'failed')}"
            )

    error = ""
    if not aggregated and failures:
        error = "Analytical plan failed: " + "; ".join(failures)

    return {
        "raw_data": aggregated,
        "error": error,
        "extracted_params": {
            **state.get("extracted_params", {}),
            "analysis_failures": failures,
        },
    }


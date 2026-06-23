"""Execute T3 plans with template-first selection and bounded NL2SQL repair."""

from __future__ import annotations

from typing import Any

import structlog

from agents.m1.config.constants import (
    NL2SQL_MAX_ATTEMPTS,
    REACT_MAX_ITERATIONS,
    T3_MAX_DB_EXECUTIONS,
)
from agents.m1.schemas.analysis_models import GeneratedQuery, PlanStep
from agents.m1.schemas.m1_state import M1State
from agents.m1.tools.db_query_tool import db_query_tool
from agents.m1.tools.nl2sql_generator import generate_sql
from agents.m1.tools.nl2sql_repair import repair_sql
from agents.m1.tools.query_gateway import execute_readonly_query
from agents.m1.tools.sql_policy import validate_sql
from backend.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

_NON_REPAIRABLE = {"security_policy_violation"}


def _step_result_is_complete(
    rows: list[dict[str, Any]],
    step: PlanStep,
) -> tuple[bool, str, str]:
    if not rows:
        return False, "empty_result", "The query returned no rows."
    columns = set(rows[0])
    missing = set(step.expected_columns) - columns
    if missing:
        return (
            False,
            "result_shape_mismatch",
            "Missing expected columns: " + ", ".join(sorted(missing)),
        )
    return True, "", ""


async def _execute_nl2sql_step(
    state: M1State,
    step: PlanStep,
    *,
    db_budget: int,
) -> tuple[dict, int]:
    question = state.get("query", "")
    frame = state.get("analysis_frame", {})
    artifacts: list[dict] = []
    seen_fingerprints: set[str] = set()
    generated: GeneratedQuery | None = None
    max_attempts = min(settings.m1_nl2sql_max_attempts, NL2SQL_MAX_ATTEMPTS)

    for attempt in range(1, max_attempts + 1):
        if db_budget <= 0:
            return {
                "step": step.model_dump(),
                "status": "failed",
                "rows": [],
                "artifacts": artifacts,
                "error_category": "execution_budget_exhausted",
            }, db_budget

        if generated is None:
            generated = await generate_sql(
                question=question,
                analysis_frame=frame,
                step=step,
            )

        prevalidation = validate_sql(generated.sql)
        if prevalidation.sql_fingerprint in seen_fingerprints:
            return {
                "step": step.model_dump(),
                "status": "failed",
                "rows": [],
                "artifacts": artifacts,
                "error_category": "repeated_sql",
            }, db_budget

        rows, artifact = await execute_readonly_query(
            sql=generated.sql,
            source="nl2sql",
            purpose=step.purpose,
        )
        artifact["attempt"] = attempt
        artifact["assumptions"] = generated.assumptions
        artifacts.append(artifact)
        fingerprint = artifact.get("sql_fingerprint", "")

        seen_fingerprints.add(fingerprint)

        if artifact.get("execution_status") == "success":
            db_budget -= 1
            complete, category, feedback = _step_result_is_complete(rows, step)
            if complete:
                return {
                    "step": step.model_dump(),
                    "status": "complete",
                    "rows": rows,
                    "artifacts": artifacts,
                }, db_budget
        else:
            category = artifact.get("error_category", "database_error")
            feedback = artifact.get("error_message", "Query failed.")
            # A blocked statement did not reach the DB and does not consume DB budget.
            if artifact.get("execution_status") == "failed":
                db_budget -= 1

        if category in _NON_REPAIRABLE or attempt >= max_attempts:
            return {
                "step": step.model_dump(),
                "status": "failed",
                "rows": rows,
                "artifacts": artifacts,
                "error_category": category,
                "error_message": feedback,
            }, db_budget

        generated = await repair_sql(
            question=question,
            analysis_frame=frame,
            step=step,
            previous=generated,
            error_category=category,
            error_message=feedback,
        )

    return {
        "step": step.model_dump(),
        "status": "failed",
        "rows": [],
        "artifacts": artifacts,
        "error_category": "attempt_budget_exhausted",
    }, db_budget


async def execute_plan(state: M1State) -> dict:
    steps = [PlanStep.model_validate(item) for item in state.get("react_plan", [])]
    max_iterations = min(
        settings.m1_react_max_iterations,
        REACT_MAX_ITERATIONS,
    )
    db_budget = min(settings.m1_max_db_executions, T3_MAX_DB_EXECUTIONS)
    tool_results: list[dict] = []
    all_artifacts = list(state.get("query_artifacts", []))

    for iteration, step in enumerate(steps[:max_iterations], start=1):
        if step.preferred_tool == "python":
            tool_results.append(
                {
                    "step": step.model_dump(),
                    "status": "deferred_to_aggregator",
                    "rows": [],
                    "artifacts": [],
                }
            )
            continue

        if step.preferred_tool == "template" and db_budget > 0:
            template_state = {
                **state,
                "query": step.purpose,
                "query_artifacts": [],
            }
            template_result = await db_query_tool(template_state)
            template_artifacts = template_result.get("query_artifacts", [])
            all_artifacts.extend(template_artifacts)
            consumed = sum(
                artifact.get("execution_status") in {"success", "failed"}
                for artifact in template_artifacts
            )
            db_budget -= consumed
            rows = template_result.get("raw_data", [])
            complete, _, _ = _step_result_is_complete(rows, step)
            if complete:
                tool_results.append(
                    {
                        "step": step.model_dump(),
                        "status": "complete",
                        "rows": rows,
                        "artifacts": template_artifacts,
                    }
                )
                continue

        nl2sql_result, db_budget = await _execute_nl2sql_step(
            state,
            step,
            db_budget=db_budget,
        )
        tool_results.append(nl2sql_result)
        all_artifacts.extend(nl2sql_result.get("artifacts", []))

        if nl2sql_result.get("status") != "complete":
            logger.warning(
                "t3_step_failed",
                step=step.id,
                category=nl2sql_result.get("error_category"),
            )

    completed = [result for result in tool_results if result["status"] == "complete"]
    exit_reason = (
        "sufficient_data"
        if len(completed) == len([s for s in steps if s.preferred_tool != "python"])
        else "partial_plan"
    )
    return {
        "tool_results": tool_results,
        "query_artifacts": all_artifacts,
        "react_iteration": min(len(steps), max_iterations),
        "db_execution_count": (
            min(settings.m1_max_db_executions, T3_MAX_DB_EXECUTIONS) - db_budget
        ),
        "react_done": True,
        "react_exit_reason": exit_reason,
        "query_mode": "nl2sql" if any(
            artifact.get("source") == "nl2sql" for artifact in all_artifacts
        ) else "template",
    }

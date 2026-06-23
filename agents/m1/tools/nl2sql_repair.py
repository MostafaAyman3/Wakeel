"""Bounded, error-aware replacement-query generation."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.m1.schemas.analysis_models import GeneratedQuery, PlanStep
from agents.m1.tools.schema_catalog import get_schema_catalog
from agents.prompts.nl2sql import NL2SQL_REPAIR_SYSTEM_PROMPT
from agents.shared.llm_client import llm_primary


async def repair_sql(
    *,
    question: str,
    analysis_frame: dict,
    step: PlanStep,
    previous: GeneratedQuery,
    error_category: str,
    error_message: str,
) -> GeneratedQuery:
    catalog = get_schema_catalog()
    repairer = llm_primary.with_structured_output(
        GeneratedQuery,
        method="function_calling",
    )
    prompt = (
        f"User question:\n{question}\n\n"
        f"Analysis frame:\n"
        f"{json.dumps(analysis_frame, ensure_ascii=False, default=str)}\n\n"
        f"Subtask:\n{step.model_dump_json()}\n\n"
        f"Previous generated query:\n{previous.model_dump_json()}\n\n"
        f"Error category: {error_category}\n"
        f"Sanitized error: {error_message}\n\n"
        f"Approved schema:\n{catalog.prompt_text()}\n"
    )
    return await repairer.ainvoke(
        [
            SystemMessage(content=NL2SQL_REPAIR_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
    )


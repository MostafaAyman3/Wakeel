"""Structured NL2SQL generation constrained to the approved M1 schema."""

from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

from agents.m1.schemas.analysis_models import GeneratedQuery, PlanStep
from agents.m1.tools.schema_catalog import get_schema_catalog
from agents.prompts.nl2sql import NL2SQL_SYSTEM_PROMPT
from agents.shared.llm_client import llm_primary


async def generate_sql(
    *,
    question: str,
    analysis_frame: dict,
    step: PlanStep,
) -> GeneratedQuery:
    catalog = get_schema_catalog()
    generator = llm_primary.with_structured_output(
        GeneratedQuery,
        method="function_calling",
    )
    prompt = (
        f"User question:\n{question}\n\n"
        f"Resolved analysis frame:\n"
        f"{json.dumps(analysis_frame, ensure_ascii=False, default=str)}\n\n"
        f"Current subtask:\n{step.model_dump_json()}\n\n"
        f"Approved schema:\n{catalog.prompt_text()}\n"
    )
    return await generator.ainvoke(
        [
            SystemMessage(content=NL2SQL_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
    )


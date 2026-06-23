"""Deterministic tests for the M1 architecture migration.

These tests avoid live LLM and database calls. Business E2E coverage continues
to come from ERP_Test_Questions.md and the existing Sprint suites.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.m1.nodes.context_loader_node import load_context
from agents.m1.nodes.context_saver_node import save_context
from agents.m1.nodes.followup_resolver_node import resolve_followup
from agents.m1.nodes.intent_router_node import route_intent
from agents.m1.nodes.result_evaluator_node import evaluate_result
from agents.m1.nodes.t6_m3_delegation_node import delegate_to_m3
from agents.m1.tools.db_query_tool import TEMPLATES
from agents.m1.tools.invoice_templates import INVOICE_TEMPLATES
from agents.m1.tools.sql_policy import validate_sql


def _assert_sql_policy() -> None:
    assert validate_sql(
        "SELECT id, total_amount FROM invoices LIMIT 5"
    ).is_valid
    assert not validate_sql("DELETE FROM invoices").is_valid
    assert (
        validate_sql("DELETE FROM invoices").error_category
        == "security_policy_violation"
    )
    assert not validate_sql(
        "SELECT tracking_number FROM shipments"
    ).is_valid
    assert not validate_sql("SELECT missing FROM invoices").is_valid
    assert not validate_sql("SELECT * FROM invoices").is_valid
    assert validate_sql("SELECT COUNT(*) AS count FROM invoices").is_valid

    queries = {
        **{
            name: sql.text.format(order="DESC")
            for name, sql in TEMPLATES.items()
        },
        **{name: sql.text for name, sql in INVOICE_TEMPLATES.items()},
    }
    failures = {
        name: validate_sql(sql).model_dump()
        for name, sql in queries.items()
        if not validate_sql(sql).is_valid
    }
    assert not failures, failures


async def _assert_heuristic_routes() -> None:
    support = await route_intent(
        {
            "query": "الفاتورة دي غلط وعايز أكلم مدير",
            "language": "auto",
            "chat_history": [],
        }
    )
    assert support["assigned_tier"] == "T6"
    assert support["domain_intent"] == "support"

    greeting = await route_intent(
        {"query": "أهلا، أنت تقدر تعمل إيه؟", "language": "auto"}
    )
    assert greeting["assigned_tier"] == "T0"
    assert greeting["language"] == "ar"

    oos = await route_intent(
        {"query": "What will revenue be next year?", "language": "auto"}
    )
    assert oos["assigned_tier"] == "T5"

    followup = await route_intent(
        {
            "query": "ليه كده؟",
            "language": "auto",
            "prior_analysis_frame": {"metric": "sales_revenue"},
        }
    )
    assert followup["assigned_tier"] == "T2"


async def _assert_context_roundtrip() -> None:
    state = {
        "assigned_tier": "T1",
        "domain_intent": "sales",
        "analysis_frame": {
            "metric": "sales_revenue",
            "date_range": {"start": "2024-01-01", "end": "2024-03-31"},
        },
        "matched_template": "T1",
        "query_mode": "template",
        "raw_data": [{"total_revenue": 3704000.0}],
        "result_status": "complete",
        "result_coverage": 1.0,
        "result_evidence": ["Retrieved one metric."],
        "result_gaps": [],
        "output_format": "metric_card",
    }
    saved = await save_context(state)
    metadata = saved["context_metadata"]
    loaded = await load_context(
        {
            "chat_history": [
                {
                    "role": "assistant",
                    "content": "Q1 revenue was 3.7M.",
                    "metadata": metadata,
                }
            ]
        }
    )
    assert loaded["prior_analysis_frame"]["metric"] == "sales_revenue"
    assert loaded["prior_result_summary"]["key_metrics"]["total_revenue"] == 3704000.0

    followup = await resolve_followup(
        {
            "query": "ليه كده؟",
            "prior_analysis_frame": loaded["prior_analysis_frame"],
            "prior_result_summary": loaded["prior_result_summary"],
        }
    )
    assert followup["followup_mode"] == "reason_only"
    assert followup["raw_data"][0]["total_revenue"] == 3704000.0


def _assert_result_evaluation() -> None:
    empty = evaluate_result({"query": "sales", "raw_data": []})
    assert empty.status == "empty"

    scalar = evaluate_result(
        {"query": "total sales", "raw_data": [{"total_sales": 100.0}]}
    )
    assert scalar.status == "complete"
    assert scalar.format_hint == "metric_card"

    partial = evaluate_result(
        {
            "query": "Compare Q1 vs Q2 sales",
            "analysis_frame": {
                "comparison_range": {
                    "start": "2024-01-01",
                    "end": "2024-03-31",
                }
            },
            "raw_data": [{"total_sales": 100.0}],
        }
    )
    assert partial.status == "partial"
    assert partial.needs_requery

    suspicious = evaluate_result(
        {
            "query": "monthly sales",
            "raw_data": [
                {"period": "2024-01", "sales": 0},
                {"period": "2024-02", "sales": 0},
            ],
        }
    )
    assert suspicious.status == "suspicious"


async def _assert_t6_boundary() -> None:
    result = await delegate_to_m3(
        {
            "query": "فين طلبي ORD-2024-0050؟",
            "language": "ar",
            "session_id": "test-session",
            "route_signals": ["فين طلبي"],
        }
    )
    assert result["m3_delegation_payload"]["identifier_candidates"]
    assert result["final_response"]["metadata"]["delegated_to"] == "M3"
    assert result["final_response"]["metadata"]["delegation_available"] is False


async def main() -> None:
    _assert_sql_policy()
    await _assert_heuristic_routes()
    await _assert_context_roundtrip()
    _assert_result_evaluation()
    await _assert_t6_boundary()
    print("Architecture migration deterministic tests: PASS")


if __name__ == "__main__":
    asyncio.run(main())

"""Comprehensive offline verification for the M1 architecture migration.

The default suite does not call OpenAI or execute database queries. External
boundaries are mocked where needed, while real parsing, routing heuristics,
state contracts, LangGraph compilation, template validation, context handling,
result evaluation, output selection, and T3 control flow are exercised.

Run:
    py scripts/test_m1_architecture_comprehensive.py
    py scripts/test_m1_architecture_comprehensive.py --verbose
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agents.m1.config.constants import (  # noqa: E402
    M1_APPROVED_TABLES,
    M1_BLOCKED_TABLES,
    NL2SQL_MAX_ATTEMPTS,
    REACT_MAX_ITERATIONS,
    T3_MAX_DB_EXECUTIONS,
)
from agents.m1.graphs.m1_graph import (  # noqa: E402
    build_legacy_m1_graph,
    build_stratified_m1_graph,
)
from agents.m1.nodes.context_loader_node import load_context  # noqa: E402
from agents.m1.nodes.context_saver_node import save_context  # noqa: E402
from agents.m1.nodes.followup_resolver_node import (  # noqa: E402
    resolve_followup,
    route_followup,
)
from agents.m1.nodes.intent_router_node import (  # noqa: E402
    normalize_text,
    route_intent,
)
from agents.m1.nodes.output_selector_node import select_output  # noqa: E402
from agents.m1.nodes.result_evaluator_node import evaluate_result  # noqa: E402
from agents.m1.nodes.t3_aggregator_node import aggregate_results  # noqa: E402
from agents.m1.nodes.t6_m3_delegation_node import delegate_to_m3  # noqa: E402
from agents.m1.schemas.analysis_models import (  # noqa: E402
    GeneratedQuery,
    PlanStep,
)
from agents.m1.schemas.m1_state import M1State  # noqa: E402
from agents.m1.tools.db_query_tool import TEMPLATES  # noqa: E402
from agents.m1.tools.invoice_templates import INVOICE_TEMPLATES  # noqa: E402
from agents.m1.tools.query_gateway import execute_readonly_query  # noqa: E402
from agents.m1.tools.schema_catalog import get_schema_catalog  # noqa: E402
from agents.m1.tools.sql_policy import (  # noqa: E402
    classify_database_error,
    validate_sql,
)
import agents.m1.nodes.t3_executor_node as t3_executor  # noqa: E402


@dataclass
class TestResult:
    group: str
    name: str
    passed: bool
    detail: str = ""


class Suite:
    def __init__(self, *, verbose: bool = False) -> None:
        self.verbose = verbose
        self.results: list[TestResult] = []

    def check(
        self,
        group: str,
        name: str,
        condition: bool,
        detail: str = "",
    ) -> None:
        passed = bool(condition)
        self.results.append(TestResult(group, name, passed, detail))
        if self.verbose or not passed:
            status = "PASS" if passed else "FAIL"
            suffix = f" — {detail}" if detail else ""
            print(f"[{status}] {group}: {name}{suffix}")

    async def run_case(
        self,
        group: str,
        name: str,
        callback: Callable[[], Awaitable[None]],
    ) -> None:
        try:
            await callback()
            self.check(group, name, True)
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
            if self.verbose:
                traceback.print_exc()
            self.check(group, name, False, detail)

    def summary(self) -> bool:
        total = len(self.results)
        passed = sum(result.passed for result in self.results)
        failed = total - passed
        groups = sorted({result.group for result in self.results})
        print("\n" + "=" * 72)
        print("M1 ARCHITECTURE MIGRATION — COMPREHENSIVE OFFLINE TEST")
        print("=" * 72)
        for group in groups:
            group_results = [result for result in self.results if result.group == group]
            group_passed = sum(result.passed for result in group_results)
            print(f"{group:<24} {group_passed:>3}/{len(group_results):<3} passed")
        print("-" * 72)
        print(f"TOTAL                    {passed:>3}/{total:<3} passed")
        if failed:
            print("\nFailures:")
            for result in self.results:
                if not result.passed:
                    print(f"- {result.group} / {result.name}: {result.detail}")
        print("=" * 72)
        return failed == 0


def _base_state(**overrides: Any) -> M1State:
    state: M1State = {
        "query": "test",
        "language": "auto",
        "chat_history": [],
        "prior_analysis_frame": {},
        "prior_result_summary": {},
        "query_artifacts": [],
        "raw_data": [],
        "user_context": {},
    }
    state.update(overrides)
    return state


async def test_contracts(suite: Suite) -> None:
    annotations = M1State.__annotations__
    required_fields = {
        "assigned_tier",
        "domain_intent",
        "analysis_frame",
        "query_mode",
        "query_artifacts",
        "result_status",
        "followup_mode",
        "react_plan",
        "clarification_pending",
        "m3_delegation_payload",
    }
    suite.check(
        "Contracts",
        "M1State migration fields",
        required_fields.issubset(annotations),
        str(sorted(required_fields - set(annotations))),
    )
    suite.check(
        "Contracts",
        "approved table boundary",
        M1_APPROVED_TABLES.isdisjoint(M1_BLOCKED_TABLES)
        and {"shipments", "customer_interactions"}.issubset(M1_BLOCKED_TABLES),
    )
    suite.check(
        "Contracts",
        "bounded execution constants",
        NL2SQL_MAX_ATTEMPTS == 3
        and REACT_MAX_ITERATIONS == 5
        and T3_MAX_DB_EXECUTIONS == 4,
    )

    catalog = get_schema_catalog()
    suite.check(
        "Contracts",
        "schema catalog contains approved tables",
        M1_APPROVED_TABLES.issubset(catalog.table_names),
    )
    suite.check(
        "Contracts",
        "schema slice excludes M3 tables",
        set(catalog.relevant_schema()).isdisjoint(
            {"shipments", "customer_interactions"}
        ),
    )


async def test_router(suite: Suite) -> None:
    scenarios = [
        ("T0 Arabic greeting", "أهلاً يا وكيل", {}, "T0", "conversation"),
        ("T0 English greeting", "Hi Wakeel", {}, "T0", "conversation"),
        (
            "T0 capabilities",
            "What can you do?",
            {},
            "T0",
            "conversation",
        ),
        (
            "T1 sales metric",
            "كام إجمالي المبيعات الشهر ده؟",
            {},
            "T1",
            "sales",
        ),
        (
            "T1 order count not greeting",
            "How many orders were delivered this month?",
            {},
            "T1",
            "orders",
        ),
        (
            "T1 inventory",
            "Show current inventory stock",
            {},
            "T1",
            "inventory",
        ),
        (
            "T1 tax",
            "ما هي ضريبة القيمة المضافة؟",
            {},
            "T1",
            "tax",
        ),
        (
            "T1 invoice",
            "Show vendor invoices for Q1",
            {},
            "T1",
            "invoice",
        ),
        (
            "T2 Arabic reason follow-up",
            "ليه كده؟",
            {"prior_analysis_frame": {"metric": "sales_revenue"}},
            "T2",
            "ambiguous",
        ),
        (
            "T2 English short follow-up",
            "Show more",
            {"prior_analysis_frame": {"metric": "sales_revenue"}},
            "T2",
            "ambiguous",
        ),
        (
            "T3 comparison",
            "Compare Q1 vs Q2 sales",
            {},
            "T3",
            "sales",
        ),
        (
            "T3 driver analysis",
            "ليه المبيعات زادت وإيه أهم الأسباب؟",
            {},
            "T3",
            "sales",
        ),
        (
            "T3 invoice analysis",
            "Analyze vendor invoices for Q1 2025",
            {},
            "T3",
            "invoice",
        ),
        ("T4 Arabic ambiguity", "عايز تقرير", {}, "T4", "ambiguous"),
        (
            "T4 English ambiguity",
            "Show me something",
            {},
            "T4",
            "ambiguous",
        ),
        (
            "T5 forecast",
            "What will my revenue be next year?",
            {},
            "T5",
            "out_of_scope",
        ),
        ("T5 weather", "What is the weather?", {}, "T5", "out_of_scope"),
        (
            "T6 complaint",
            "الفاتورة دي غلط وعايز أكلم مدير",
            {},
            "T6",
            "support",
        ),
        (
            "T6 refund",
            "I need a refund for invoice INV-0042",
            {},
            "T6",
            "support",
        ),
        (
            "T6 shipment",
            "فين طلبي؟ الشحن اتأخر",
            {},
            "T6",
            "support",
        ),
        (
            "clarification continuation",
            "المبيعات",
            {
                "clarification_pending": True,
                "clarification_original_query": "عايز تقرير",
            },
            "T2",
            "ambiguous",
        ),
    ]
    for name, query, extra, expected_tier, expected_domain in scenarios:
        result = await route_intent(_base_state(query=query, **extra))
        suite.check(
            "Router",
            name,
            result["assigned_tier"] == expected_tier
            and result["domain_intent"] == expected_domain,
            f"got {result['assigned_tier']}/{result['domain_intent']}",
        )

    suite.check(
        "Router",
        "Arabic normalization",
        normalize_text("إيرادات القِيمة المُضافة")
        == normalize_text("ايرادات القيمه المضافه"),
    )


async def test_context(suite: Suite) -> None:
    state = _base_state(
        assigned_tier="T1",
        domain_intent="sales",
        analysis_frame={
            "metric": "sales_revenue",
            "date_range": {"start": "2024-01-01", "end": "2024-03-31"},
        },
        matched_template="T1",
        query_mode="template",
        raw_data=[{"total_revenue": 3_704_000.0, "label": "Q1"}],
        result_status="complete",
        result_coverage=1.0,
        result_evidence=["Retrieved one metric."],
        result_gaps=[],
        output_format="metric_card",
    )
    saved = await save_context(state)
    metadata = saved["context_metadata"]
    suite.check(
        "Context",
        "metadata schema version",
        metadata["schema_version"] == 1,
    )
    suite.check(
        "Context",
        "raw rows are not persisted",
        "raw_data" not in metadata
        and metadata["result_summary"]["key_metrics"]["total_revenue"]
        == 3_704_000.0,
    )

    history = [
        {
            "role": "assistant",
            "content": "Q1 revenue",
            "metadata": metadata,
        }
    ]
    loaded = await load_context(_base_state(chat_history=history))
    suite.check(
        "Context",
        "analysis frame roundtrip",
        loaded["prior_analysis_frame"]["metric"] == "sales_revenue",
    )
    suite.check(
        "Context",
        "result summary roundtrip",
        loaded["prior_result_summary"]["row_count"] == 1,
    )

    pending = {
        **metadata,
        "clarification": {
            "pending": True,
            "original_query": "عايز تقرير",
            "missing_slots": ["metric"],
        },
    }
    cleared = {**metadata, "clarification": None}
    loaded_cleared = await load_context(
        _base_state(
            chat_history=[
                {"role": "assistant", "content": "question", "metadata": pending},
                {"role": "assistant", "content": "answer", "metadata": cleared},
            ]
        )
    )
    suite.check(
        "Context",
        "newer turn clears old clarification",
        loaded_cleared["clarification_pending"] is False,
    )


async def test_followups(suite: Suite) -> None:
    summary = {"key_metrics": {"total_revenue": 100.0}}
    scenarios = [
        ("reason_only", "ليه كده؟", "reason_only", "reason"),
        ("drill_down", "وريني التفاصيل", "drill_down", "requery"),
        ("compare", "قارنها بالربع الأول", "compare", "requery"),
        ("summarize", "اعمل ملخص", "summarize", "reason"),
        ("refine", "خليها للعملاء الكبار", "refine", "requery"),
    ]
    for name, query, expected_mode, expected_route in scenarios:
        result = await resolve_followup(
            _base_state(
                query=query,
                prior_analysis_frame={"metric": "sales_revenue"},
                prior_result_summary=summary,
            )
        )
        suite.check(
            "Follow-up",
            name,
            result["followup_mode"] == expected_mode
            and route_followup(result) == expected_route,
            str(result),
        )

    clarification = await resolve_followup(
        _base_state(
            query="المبيعات",
            clarification_pending=True,
            clarification_original_query="عايز تقرير",
            prior_analysis_frame={},
        )
    )
    suite.check(
        "Follow-up",
        "clarification merge",
        clarification["query"].startswith("عايز تقرير")
        and clarification["clarification_pending"] is False,
    )


async def test_sql_policy(suite: Suite) -> None:
    safe_queries = {
        "simple select": "SELECT id, total_amount FROM invoices LIMIT 5",
        "qualified join": (
            "SELECT c.name, SUM(i.total_amount) AS revenue "
            "FROM invoices i JOIN customers c ON c.id = i.customer_id "
            "GROUP BY c.name ORDER BY revenue DESC LIMIT 10"
        ),
        "cte": (
            "WITH totals AS ("
            " SELECT customer_id, SUM(total_amount) AS revenue"
            " FROM invoices GROUP BY customer_id"
            ") SELECT c.name, t.revenue FROM totals t"
            " JOIN customers c ON c.id = t.customer_id"
        ),
        "count star": "SELECT COUNT(*) AS invoice_count FROM invoices",
        "union": (
            "SELECT display_id FROM invoices "
            "UNION SELECT display_id FROM orders"
        ),
        "public schema": "SELECT id FROM public.invoices LIMIT 1",
    }
    for name, sql in safe_queries.items():
        result = validate_sql(sql)
        suite.check(
            "SQL Policy",
            f"allow {name}",
            result.is_valid,
            result.message or "",
        )

    unsafe_queries = {
        "delete": "DELETE FROM invoices",
        "update": "UPDATE invoices SET total_amount = 0",
        "insert": "INSERT INTO invoices (id) VALUES (gen_random_uuid())",
        "drop": "DROP TABLE invoices",
        "multiple statements": "SELECT id FROM invoices; SELECT id FROM orders",
        "M3 shipments": "SELECT tracking_number FROM shipments",
        "M3 interactions": "SELECT issue_type FROM customer_interactions",
        "conversation metadata": "SELECT metadata FROM conversations",
        "tax chunks": "SELECT chunk_text FROM tax_chunks",
        "unknown table": "SELECT id FROM imaginary_table",
        "unknown column": "SELECT imaginary_column FROM invoices",
        "wildcard": "SELECT * FROM invoices",
        "qualified wildcard": "SELECT i.* FROM invoices i",
        "system schema": "SELECT tablename FROM pg_catalog.pg_tables",
        "information schema": (
            "SELECT table_name FROM information_schema.tables"
        ),
        "cross database": "SELECT id FROM other.public.invoices",
        "sleep function": "SELECT pg_sleep(10) FROM invoices",
        "terminate function": (
            "SELECT pg_terminate_backend(1) FROM invoices"
        ),
    }
    for name, sql in unsafe_queries.items():
        result = validate_sql(sql)
        suite.check(
            "SQL Policy",
            f"block {name}",
            not result.is_valid,
            result.model_dump_json(),
        )

    rendered_templates = {
        **{
            name: query.text.format(order="DESC")
            for name, query in TEMPLATES.items()
        },
        **{
            name: query.text
            for name, query in INVOICE_TEMPLATES.items()
        },
    }
    for name, sql in rendered_templates.items():
        result = validate_sql(sql)
        suite.check(
            "Templates",
            name,
            result.is_valid,
            result.message or "",
        )

    blocked_rows, blocked_artifact = await execute_readonly_query(
        sql="DELETE FROM invoices",
        source="nl2sql",
        purpose="offline safety test",
    )
    suite.check(
        "SQL Policy",
        "gateway blocks before DB",
        not blocked_rows
        and blocked_artifact["execution_status"] == "blocked"
        and blocked_artifact["error_category"] == "security_policy_violation",
    )

    error_cases = [
        (Exception('column "x" does not exist'), "unknown_column"),
        (Exception('relation "x" does not exist'), "unknown_table"),
        (Exception("column reference is ambiguous"), "ambiguous_column"),
        (Exception("must appear in the GROUP BY clause"), "invalid_grouping"),
        (Exception("operator does not exist"), "type_mismatch"),
        (Exception("canceling statement due to statement timeout"), "execution_timeout"),
        (Exception("syntax error near FROM"), "syntax_error"),
    ]
    for error, expected in error_cases:
        category, _ = classify_database_error(error)
        suite.check(
            "SQL Errors",
            expected,
            category == expected,
            f"got {category}",
        )


async def test_result_evaluator(suite: Suite) -> None:
    cases = [
        (
            "empty",
            {"query": "sales", "raw_data": []},
            "empty",
            False,
        ),
        (
            "failed",
            {"query": "sales", "raw_data": [], "error": "DB failed"},
            "failed",
            False,
        ),
        (
            "scalar metric",
            {"query": "sales", "raw_data": [{"total_sales": 10}]},
            "complete",
            False,
        ),
        (
            "two-period comparison",
            {
                "query": "Compare sales",
                "analysis_frame": {
                    "comparison_range": {
                        "start": "2024-01-01",
                        "end": "2024-03-31",
                    }
                },
                "raw_data": [
                    {"period": "Q1", "sales": 10},
                    {"period": "Q2", "sales": 12},
                ],
            },
            "complete",
            False,
        ),
        (
            "missing comparison group",
            {
                "query": "Compare sales",
                "analysis_frame": {
                    "comparison_range": {
                        "start": "2024-01-01",
                        "end": "2024-03-31",
                    }
                },
                "raw_data": [{"period": "Q1", "sales": 10}],
            },
            "partial",
            True,
        ),
        (
            "missing dimension",
            {
                "query": "sales by product",
                "analysis_frame": {"dimensions": ["product"]},
                "raw_data": [{"sales": 10}],
            },
            "partial",
            True,
        ),
        (
            "all zero suspicious",
            {
                "query": "sales",
                "raw_data": [
                    {"period": "Q1", "sales": 0},
                    {"period": "Q2", "sales": 0},
                ],
            },
            "suspicious",
            False,
        ),
    ]
    for name, state, expected_status, expected_requery in cases:
        result = evaluate_result(state)
        suite.check(
            "Result Evaluator",
            name,
            result.status == expected_status
            and result.needs_requery == expected_requery,
            result.model_dump_json(),
        )


async def test_output_selector(suite: Suite) -> None:
    cases = [
        (
            "evaluator metric hint",
            {
                "raw_data": [{"total": 10}],
                "result_format_hint": "metric_card",
            },
            "metric_card",
        ),
        (
            "anomaly wins",
            {
                "raw_data": [{"amount": 10}],
                "result_format_hint": "metric_card",
                "anomaly_detected": True,
            },
            "alert",
        ),
        (
            "time series",
            {
                "raw_data": [
                    {"period": "2024-01", "sales": 10},
                    {"period": "2024-02", "sales": 20},
                ]
            },
            "line_chart",
        ),
        (
            "categorical",
            {
                "raw_data": [
                    {"category": "A", "sales": 10},
                    {"category": "B", "sales": 20},
                ]
            },
            "bar_chart",
        ),
    ]
    for name, state, expected in cases:
        result = await select_output(_base_state(**state))
        suite.check(
            "Output Selector",
            name,
            result["output_format"] == expected,
            str(result),
        )


async def _with_t3_mocks(
    *,
    generated_queries: list[GeneratedQuery],
    gateway_results: list[tuple[list[dict], dict]],
    callback: Callable[[], Awaitable[Any]],
    repair_queries: list[GeneratedQuery] | None = None,
) -> tuple[Any, dict[str, int]]:
    originals = {
        "generate_sql": t3_executor.generate_sql,
        "repair_sql": t3_executor.repair_sql,
        "execute_readonly_query": t3_executor.execute_readonly_query,
    }
    counters = {"generate": 0, "repair": 0, "gateway": 0}
    generated_iter = iter(generated_queries)
    repair_iter = iter(repair_queries or [])
    gateway_iter = iter(gateway_results)

    async def fake_generate_sql(**_: Any) -> GeneratedQuery:
        counters["generate"] += 1
        return next(generated_iter)

    async def fake_repair_sql(**_: Any) -> GeneratedQuery:
        counters["repair"] += 1
        return next(repair_iter)

    async def fake_gateway(**_: Any) -> tuple[list[dict], dict]:
        counters["gateway"] += 1
        return next(gateway_iter)

    t3_executor.generate_sql = fake_generate_sql
    t3_executor.repair_sql = fake_repair_sql
    t3_executor.execute_readonly_query = fake_gateway
    try:
        return await callback(), counters
    finally:
        t3_executor.generate_sql = originals["generate_sql"]
        t3_executor.repair_sql = originals["repair_sql"]
        t3_executor.execute_readonly_query = originals["execute_readonly_query"]


def _generated(sql: str, expected: list[str]) -> GeneratedQuery:
    return GeneratedQuery(
        sql=sql,
        purpose="test",
        expected_columns=expected,
        expected_grain="row",
        referenced_tables=["invoices"],
        confidence=0.9,
    )


def _artifact(
    sql: str,
    *,
    status: str,
    category: str | None = None,
) -> dict:
    validation = validate_sql(sql)
    return {
        "source": "nl2sql",
        "purpose": "test",
        "sql_fingerprint": validation.sql_fingerprint,
        "parameters": {},
        "referenced_tables": validation.tables,
        "referenced_columns": validation.columns,
        "validation": validation.model_dump(),
        "execution_status": status,
        "row_count": 0,
        "duration_ms": 0,
        "result_sample": [],
        "error_category": category,
        "error_message": category,
    }


async def test_t3(suite: Suite) -> None:
    step = PlanStep(
        id="step_1",
        purpose="Get invoice totals",
        preferred_tool="nl2sql",
        expected_columns=["total"],
        expected_grain="metric",
    )
    valid_sql = "SELECT SUM(total_amount) AS total FROM invoices"

    async def first_try() -> Any:
        return await t3_executor._execute_nl2sql_step(
            _base_state(query="total invoices"),
            step,
            db_budget=4,
        )

    (result, budget), counters = await _with_t3_mocks(
        generated_queries=[_generated(valid_sql, ["total"])],
        gateway_results=[
            (
                [{"total": 100}],
                _artifact(valid_sql, status="success"),
            )
        ],
        callback=first_try,
    )
    suite.check(
        "T3 Executor",
        "first-attempt success",
        result["status"] == "complete"
        and budget == 3
        and counters == {"generate": 1, "repair": 0, "gateway": 1},
        f"{result} {counters}",
    )

    bad_sql = "SELECT missing_column AS total FROM invoices"
    repaired_sql = "SELECT SUM(total_amount) AS total FROM invoices"

    async def repair_success() -> Any:
        return await t3_executor._execute_nl2sql_step(
            _base_state(query="total invoices"),
            step,
            db_budget=4,
        )

    (result, budget), counters = await _with_t3_mocks(
        generated_queries=[_generated(bad_sql, ["total"])],
        repair_queries=[_generated(repaired_sql, ["total"])],
        gateway_results=[
            (
                [],
                _artifact(
                    bad_sql,
                    status="blocked",
                    category="unknown_column",
                ),
            ),
            (
                [{"total": 100}],
                _artifact(repaired_sql, status="success"),
            ),
        ],
        callback=repair_success,
    )
    suite.check(
        "T3 Executor",
        "repair unknown column",
        result["status"] == "complete"
        and budget == 3
        and counters["repair"] == 1
        and counters["gateway"] == 2,
        f"{result} {counters}",
    )

    destructive_sql = "DELETE FROM invoices"

    async def security_stop() -> Any:
        return await t3_executor._execute_nl2sql_step(
            _base_state(query="delete"),
            step,
            db_budget=4,
        )

    (result, budget), counters = await _with_t3_mocks(
        generated_queries=[_generated(destructive_sql, ["total"])],
        gateway_results=[
            (
                [],
                _artifact(
                    destructive_sql,
                    status="blocked",
                    category="security_policy_violation",
                ),
            )
        ],
        callback=security_stop,
    )
    suite.check(
        "T3 Executor",
        "security violation is not repaired",
        result["status"] == "failed"
        and result["error_category"] == "security_policy_violation"
        and counters["repair"] == 0
        and budget == 4,
        f"{result} {counters}",
    )

    shape_sql = "SELECT total_amount AS amount FROM invoices LIMIT 1"
    shape_repair = "SELECT SUM(total_amount) AS total FROM invoices"

    async def shape_repair_case() -> Any:
        return await t3_executor._execute_nl2sql_step(
            _base_state(query="total"),
            step,
            db_budget=4,
        )

    (result, budget), counters = await _with_t3_mocks(
        generated_queries=[_generated(shape_sql, ["total"])],
        repair_queries=[_generated(shape_repair, ["total"])],
        gateway_results=[
            (
                [{"amount": 100}],
                _artifact(shape_sql, status="success"),
            ),
            (
                [{"total": 100}],
                _artifact(shape_repair, status="success"),
            ),
        ],
        callback=shape_repair_case,
    )
    suite.check(
        "T3 Executor",
        "result-shape feedback triggers repair",
        result["status"] == "complete"
        and counters["repair"] == 1
        and budget == 2,
        f"{result} {counters}",
    )

    async def repeated_case() -> Any:
        return await t3_executor._execute_nl2sql_step(
            _base_state(query="total"),
            step,
            db_budget=4,
        )

    (result, budget), counters = await _with_t3_mocks(
        generated_queries=[_generated(shape_sql, ["total"])],
        repair_queries=[_generated(shape_sql, ["total"])],
        gateway_results=[
            (
                [{"amount": 100}],
                _artifact(shape_sql, status="success"),
            )
        ],
        callback=repeated_case,
    )
    suite.check(
        "T3 Executor",
        "identical repaired SQL is not re-executed",
        result["status"] == "failed"
        and result["error_category"] == "repeated_sql"
        and counters["gateway"] == 1
        and budget == 3,
        f"{result} {counters}",
    )

    zero_budget_result, zero_budget = await t3_executor._execute_nl2sql_step(
        _base_state(query="total"),
        step,
        db_budget=0,
    )
    suite.check(
        "T3 Executor",
        "zero DB budget stops execution",
        zero_budget_result["error_category"] == "execution_budget_exhausted"
        and zero_budget == 0,
    )

    aggregated = await aggregate_results(
        _base_state(
            tool_results=[
                {
                    "step": {"id": "sales"},
                    "status": "complete",
                    "rows": [{"period": "Q1", "sales": 10}],
                },
                {
                    "step": {"id": "cost"},
                    "status": "complete",
                    "rows": [{"period": "Q1", "cost": 6}],
                },
                {
                    "step": {"id": "failed"},
                    "status": "failed",
                    "error_category": "empty_result",
                },
            ]
        )
    )
    suite.check(
        "T3 Aggregator",
        "combines evidence and records failures",
        len(aggregated["raw_data"]) == 2
        and aggregated["raw_data"][0]["_analysis_step"] == "sales"
        and aggregated["extracted_params"]["analysis_failures"],
        str(aggregated),
    )


async def test_t6(suite: Suite) -> None:
    result = await delegate_to_m3(
        _base_state(
            query="فين طلبي ORD-2024-0050؟",
            language="ar",
            session_id="session-1",
            route_signals=["فين طلبي"],
        )
    )
    payload = result["m3_delegation_payload"]
    suite.check(
        "T6 Delegation",
        "identifier extraction",
        payload["identifier_candidates"] == ["ORD-2024-0050"],
        str(payload),
    )
    suite.check(
        "T6 Delegation",
        "stable unavailable response",
        result["final_response"]["metadata"]["delegated_to"] == "M3"
        and result["final_response"]["metadata"]["delegation_available"] is False,
    )
    suite.check(
        "T6 Delegation",
        "no support data access fields",
        "raw_data" not in result and result["query_mode"] == "none",
    )


async def test_graphs(suite: Suite) -> None:
    try:
        legacy = build_legacy_m1_graph()
        suite.check(
            "Graphs",
            "legacy rollback graph compiles",
            legacy is not None,
        )
    except Exception as exc:
        suite.check(
            "Graphs",
            "legacy rollback graph compiles",
            False,
            str(exc),
        )

    try:
        stratified = build_stratified_m1_graph()
        suite.check(
            "Graphs",
            "stratified graph compiles",
            stratified is not None,
        )
    except Exception as exc:
        suite.check(
            "Graphs",
            "stratified graph compiles",
            False,
            str(exc),
        )


async def main(verbose: bool) -> bool:
    suite = Suite(verbose=verbose)
    await test_contracts(suite)
    await test_router(suite)
    await test_context(suite)
    await test_followups(suite)
    await test_sql_policy(suite)
    await test_result_evaluator(suite)
    await test_output_selector(suite)
    await test_t3(suite)
    await test_t6(suite)
    await test_graphs(suite)
    return suite.summary()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    success = asyncio.run(main(args.verbose))
    raise SystemExit(0 if success else 1)

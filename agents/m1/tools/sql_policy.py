"""Schema-aware SQL safety policy for all M1 database queries."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

import sqlglot
from sqlglot import exp

from agents.m1.config.constants import (
    M1_APPROVED_TABLES,
    M1_BLOCKED_TABLES,
    QUERY_MAX_DEPTH,
    QUERY_MAX_JOINS,
)
from agents.m1.schemas.analysis_models import QueryValidation
from agents.m1.tools.schema_catalog import SchemaCatalog, get_schema_catalog

_BLOCKED_EXPRESSION_TYPES: tuple[type[exp.Expression], ...] = tuple(
    expression_type
    for expression_type in (
        getattr(exp, "Insert", None),
        getattr(exp, "Update", None),
        getattr(exp, "Delete", None),
        getattr(exp, "Create", None),
        getattr(exp, "Drop", None),
        getattr(exp, "Alter", None),
        getattr(exp, "TruncateTable", None),
        getattr(exp, "Merge", None),
        getattr(exp, "Command", None),
        getattr(exp, "Transaction", None),
        getattr(exp, "Grant", None),
        getattr(exp, "Revoke", None),
    )
    if expression_type is not None
)

_BLOCKED_FUNCTIONS = {
    "pg_sleep",
    "pg_terminate_backend",
    "pg_cancel_backend",
    "set_config",
    "dblink",
    "lo_import",
    "lo_export",
}


@dataclass(frozen=True)
class SQLPolicyOptions:
    allow_star: bool = False
    max_joins: int = QUERY_MAX_JOINS
    max_depth: int = QUERY_MAX_DEPTH


def _failure(
    category: str,
    message: str,
    *,
    fingerprint: str = "",
    tables: Iterable[str] = (),
    columns: Iterable[str] = (),
) -> QueryValidation:
    return QueryValidation(
        is_valid=False,
        error_category=category,
        message=message,
        tables=sorted(set(tables)),
        columns=sorted(set(columns)),
        sql_fingerprint=fingerprint,
    )


def _fingerprint(sql: str) -> str:
    normalized = re.sub(r"\s+", " ", sql).strip().rstrip(";")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _expression_depth(expression: exp.Expression) -> int:
    def visit(node: exp.Expression, depth: int) -> int:
        children = list(node.iter_expressions())
        if not children:
            return depth
        return max(visit(child, depth + 1) for child in children)

    return visit(expression, 1)


def _cte_names(expression: exp.Expression) -> set[str]:
    return {
        cte.alias_or_name.lower()
        for cte in expression.find_all(exp.CTE)
        if cte.alias_or_name
    }


def validate_sql(
    sql: str,
    *,
    catalog: SchemaCatalog | None = None,
    options: SQLPolicyOptions | None = None,
) -> QueryValidation:
    """Validate one PostgreSQL read query against the M1 schema policy."""
    catalog = catalog or get_schema_catalog()
    options = options or SQLPolicyOptions()
    fingerprint = _fingerprint(sql)

    if not sql or not sql.strip():
        return _failure("syntax_error", "SQL is empty.", fingerprint=fingerprint)

    try:
        statements = sqlglot.parse(sql, read="postgres")
    except Exception as exc:
        return _failure(
            "syntax_error",
            f"SQL could not be parsed: {exc}",
            fingerprint=fingerprint,
        )

    if len(statements) != 1:
        return _failure(
            "security_policy_violation",
            "Exactly one SQL statement is allowed.",
            fingerprint=fingerprint,
        )

    expression = statements[0]
    if expression is None:
        return _failure("syntax_error", "SQL is empty.", fingerprint=fingerprint)

    if isinstance(expression, _BLOCKED_EXPRESSION_TYPES):
        return _failure(
            "security_policy_violation",
            f"Statement type {expression.key} is not allowed.",
            fingerprint=fingerprint,
        )

    if not isinstance(expression, (exp.Select, exp.SetOperation)):
        return _failure(
            "security_policy_violation",
            "Only SELECT, WITH, and read-only set operations are allowed.",
            fingerprint=fingerprint,
        )

    for blocked_type in _BLOCKED_EXPRESSION_TYPES:
        if expression.find(blocked_type):
            return _failure(
                "security_policy_violation",
                f"Blocked SQL expression detected: {blocked_type.__name__}.",
                fingerprint=fingerprint,
            )

    for function in expression.find_all(exp.Func):
        function_name = function.sql_name().lower()
        if function_name in _BLOCKED_FUNCTIONS:
            return _failure(
                "security_policy_violation",
                f"Function is not allowed: {function_name}.",
                fingerprint=fingerprint,
            )

    if expression.args.get("into") is not None:
        return _failure(
            "security_policy_violation",
            "SELECT INTO is not allowed.",
            fingerprint=fingerprint,
        )

    cte_names = _cte_names(expression)
    physical_tables: list[str] = []
    alias_to_table: dict[str, str] = {}

    for table_expression in expression.find_all(exp.Table):
        table_name = table_expression.name.lower()
        if table_name in cte_names:
            continue

        database_name = (table_expression.db or "").lower()
        catalog_name = (table_expression.catalog or "").lower()
        if database_name and database_name != "public":
            return _failure(
                "security_policy_violation",
                f"Schema access is not allowed: {database_name}.",
                fingerprint=fingerprint,
            )
        if catalog_name:
            return _failure(
                "security_policy_violation",
                "Cross-database access is not allowed.",
                fingerprint=fingerprint,
            )

        if table_name in M1_BLOCKED_TABLES or table_name not in M1_APPROVED_TABLES:
            return _failure(
                "security_policy_violation",
                f"Table is not approved for M1 analytics: {table_name}.",
                fingerprint=fingerprint,
                tables=[table_name],
            )
        if not catalog.has_table(table_name):
            return _failure(
                "unknown_table",
                f"Table does not exist in the schema catalog: {table_name}.",
                fingerprint=fingerprint,
                tables=[table_name],
            )

        physical_tables.append(table_name)
        alias_to_table[table_expression.alias_or_name.lower()] = table_name
        alias_to_table[table_name] = table_name

    if not physical_tables:
        return _failure(
            "unknown_table",
            "The query does not reference an approved ERP table.",
            fingerprint=fingerprint,
        )

    joins = list(expression.find_all(exp.Join))
    if len(joins) > options.max_joins:
        return _failure(
            "security_policy_violation",
            f"Query exceeds the maximum join count ({options.max_joins}).",
            fingerprint=fingerprint,
            tables=physical_tables,
        )

    if _expression_depth(expression) > options.max_depth * 8:
        return _failure(
            "security_policy_violation",
            "Query nesting is too deep.",
            fingerprint=fingerprint,
            tables=physical_tables,
        )

    stars = [
        star
        for star in expression.find_all(exp.Star)
        if not isinstance(star.parent, exp.Count)
    ]
    if stars and not options.allow_star:
        return _failure(
            "security_policy_violation",
            "Wildcard column selection is not allowed.",
            fingerprint=fingerprint,
            tables=physical_tables,
        )

    referenced_columns: list[str] = []
    table_set = set(physical_tables)
    for column_expression in expression.find_all(exp.Column):
        column_name = column_expression.name.lower()
        if column_name == "*":
            continue
        qualifier = (column_expression.table or "").lower()
        referenced_columns.append(
            f"{qualifier}.{column_name}" if qualifier else column_name
        )

        if qualifier:
            physical_table = alias_to_table.get(qualifier)
            if physical_table and not catalog.has_column(physical_table, column_name):
                return _failure(
                    "unknown_column",
                    f"Column {qualifier}.{column_name} does not exist.",
                    fingerprint=fingerprint,
                    tables=physical_tables,
                    columns=referenced_columns,
                )
        elif not any(catalog.has_column(table, column_name) for table in table_set):
            # Projection aliases are valid in ORDER BY/HAVING. Accept aliases that
            # are declared anywhere in this statement.
            aliases = {
                alias.alias.lower()
                for alias in expression.find_all(exp.Alias)
                if alias.alias
            }
            if column_name not in aliases:
                return _failure(
                    "unknown_column",
                    f"Column {column_name} does not exist in referenced tables.",
                    fingerprint=fingerprint,
                    tables=physical_tables,
                    columns=referenced_columns,
                )

    normalized_sql = expression.sql(dialect="postgres", pretty=False)
    return QueryValidation(
        is_valid=True,
        tables=sorted(set(physical_tables)),
        columns=sorted(set(referenced_columns)),
        sql_fingerprint=fingerprint,
        normalized_sql=normalized_sql,
    )


def classify_database_error(error: Exception) -> tuple[str, str]:
    """Map a database exception to a stable, sanitized repair category."""
    message = str(error)
    lowered = message.lower()
    if "does not exist" in lowered and "column" in lowered:
        category = "unknown_column"
    elif "does not exist" in lowered and (
        "relation" in lowered or "table" in lowered
    ):
        category = "unknown_table"
    elif "ambiguous" in lowered:
        category = "ambiguous_column"
    elif "group by" in lowered or "aggregate" in lowered:
        category = "invalid_grouping"
    elif "operator does not exist" in lowered or "invalid input syntax" in lowered:
        category = "type_mismatch"
    elif "timeout" in lowered or "canceling statement" in lowered:
        category = "execution_timeout"
    elif "syntax" in lowered:
        category = "syntax_error"
    else:
        category = "database_error"

    sanitized = re.sub(r"\s+", " ", message).strip()
    return category, sanitized[:500]

"""Central policy and execution limits for the M1 intelligence agent."""

from __future__ import annotations

M1_APPROVED_TABLES: frozenset[str] = frozenset(
    {
        "customers",
        "inventory",
        "invoice_items",
        "invoices",
        "order_items",
        "orders",
        "payments",
        "products",
        "transactions",
        "vendors",
    }
)

M1_BLOCKED_TABLES: frozenset[str] = frozenset(
    {
        "audit_log",
        "conversations",
        "customer_interactions",
        "shipments",
        "tax_chunks",
    }
)

AMBIGUITY_THRESHOLD = 0.55
TEMPLATE_MIN_CONFIDENCE = 0.75

REACT_MAX_ITERATIONS = 5
NL2SQL_MAX_ATTEMPTS = 3
T3_MAX_DB_EXECUTIONS = 4

QUERY_MAX_JOINS = 6
QUERY_MAX_DEPTH = 4
QUERY_DEFAULT_LIMIT = 200
QUERY_HARD_LIMIT = 500
QUERY_TIMEOUT_MS = 30_000

CONTEXT_HISTORY_LIMIT = 8
CONTEXT_RESULT_SAMPLE_ROWS = 5
CONTEXT_MAX_KEY_METRICS = 12
CONTEXT_SCHEMA_VERSION = 1

SQL_ALLOWED_ROOT_KEYS: frozenset[str] = frozenset(
    {"select", "union", "intersect", "except"}
)


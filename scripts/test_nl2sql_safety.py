"""Adversarial SQL policy tests for M1 NL2SQL."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.m1.tools.sql_policy import validate_sql


SAFE = [
    "SELECT display_id, total_amount FROM invoices ORDER BY total_amount DESC LIMIT 10",
    (
        "WITH totals AS ("
        " SELECT customer_id, SUM(total_amount) AS revenue"
        " FROM invoices GROUP BY customer_id"
        ") SELECT c.name, t.revenue FROM totals t"
        " JOIN customers c ON c.id = t.customer_id"
        " ORDER BY t.revenue DESC LIMIT 10"
    ),
    "SELECT COUNT(*) AS invoice_count FROM invoices",
]

UNSAFE = [
    "DELETE FROM invoices",
    "DROP TABLE customers",
    "SELECT * FROM invoices",
    "SELECT tracking_number FROM shipments",
    "SELECT metadata FROM conversations",
    "SELECT missing_column FROM orders",
    "SELECT id FROM pg_catalog.pg_tables",
    "SELECT id FROM invoices; SELECT id FROM customers",
]


def main() -> None:
    safe_failures = [sql for sql in SAFE if not validate_sql(sql).is_valid]
    unsafe_failures = [sql for sql in UNSAFE if validate_sql(sql).is_valid]
    assert not safe_failures, safe_failures
    assert not unsafe_failures, unsafe_failures
    print("NL2SQL safety tests: PASS")


if __name__ == "__main__":
    main()

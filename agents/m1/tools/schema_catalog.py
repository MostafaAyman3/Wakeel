"""Read-only catalog of the live ERP schema used by SQL validation and NL2SQL."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from agents.m1.config.constants import M1_APPROVED_TABLES

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_PATH = _PROJECT_ROOT / "docs" / "architecture" / "db_schema_reference.json"


class SchemaCatalog:
    """Small in-memory view over the generated database schema reference."""

    def __init__(self, schema_path: Path = _SCHEMA_PATH) -> None:
        payload = json.loads(schema_path.read_text(encoding="utf-8"))
        tables = payload.get("tables", {})
        self.generated_at: str = payload.get("generated_at", "")
        self.schema_name: str = payload.get("schema", "public")
        self._tables: dict[str, dict[str, Any]] = {
            name.lower(): definition for name, definition in tables.items()
        }

    @property
    def table_names(self) -> set[str]:
        return set(self._tables)

    def has_table(self, table: str) -> bool:
        return table.lower() in self._tables

    def columns_for(self, table: str) -> set[str]:
        definition = self._tables.get(table.lower(), {})
        return {
            column["name"].lower()
            for column in definition.get("columns", [])
            if column.get("name")
        }

    def has_column(self, table: str, column: str) -> bool:
        return column.lower() in self.columns_for(table)

    def relevant_schema(
        self,
        tables: Iterable[str] | None = None,
        *,
        include_relationships: bool = True,
    ) -> dict[str, Any]:
        selected = {
            table.lower()
            for table in (tables or M1_APPROVED_TABLES)
            if table.lower() in M1_APPROVED_TABLES
        }
        result: dict[str, Any] = {}
        for table in sorted(selected):
            definition = self._tables.get(table)
            if not definition:
                continue
            item: dict[str, Any] = {
                "columns": [
                    {
                        "name": column.get("name"),
                        "type": column.get("udt_name") or column.get("data_type"),
                        "nullable": column.get("nullable", True),
                    }
                    for column in definition.get("columns", [])
                ]
            }
            if include_relationships:
                item["foreign_keys"] = definition.get("foreign_keys", [])
            result[table] = item
        return result

    def prompt_text(self, tables: Iterable[str] | None = None) -> str:
        lines: list[str] = []
        for table, definition in self.relevant_schema(tables).items():
            columns = ", ".join(
                f"{column['name']}:{column['type']}"
                for column in definition["columns"]
            )
            lines.append(f"- {table} ({columns})")
            for foreign_key in definition.get("foreign_keys", []):
                lines.append(
                    "  FK "
                    f"{table}.{foreign_key['column']} -> "
                    f"{foreign_key['references_table']}."
                    f"{foreign_key['references_column']}"
                )
        return "\n".join(lines)


@lru_cache(maxsize=1)
def get_schema_catalog() -> SchemaCatalog:
    return SchemaCatalog()


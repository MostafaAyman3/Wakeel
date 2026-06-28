"""
Apply the Mini-RAG Supabase migration (creates projects/assets/chunks +
match_vectors function, vector(1536)) using asyncpg over the configured DB.

Idempotent: uses CREATE ... IF NOT EXISTS. Safe to re-run.

Usage:
    python scripts/apply_mini_rag_migration.py
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import asyncpg

from backend.core.config import get_settings

_MIGRATION = os.path.join(
    os.path.dirname(__file__), "..", "MIni-RAG-APP-V1", "supabase_migration.sql"
)


def _to_asyncpg_dsn(url: str) -> str:
    # SQLAlchemy style -> plain libpq DSN
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def main() -> None:
    settings = get_settings()
    dsn = _to_asyncpg_dsn(settings.database_url)

    with open(_MIGRATION, "r", encoding="utf-8") as fh:
        sql = fh.read()

    print(f"Connecting to DB (pgbouncer-safe, statement_cache_size=0)...")
    conn = await asyncpg.connect(dsn, statement_cache_size=0)
    try:
        await conn.execute(sql)
        print("[OK] Migration executed.")

        # Verify chunks.vector dimension
        row = await conn.fetchrow(
            """
            SELECT a.atttypmod AS typmod
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            WHERE c.relname = 'chunks' AND a.attname = 'vector'
            """
        )
        if row is not None:
            # for pgvector, typmod is the dimension
            print(f"[OK] chunks.vector dimension = {row['typmod']}")
        else:
            print("[WARN] could not read chunks.vector dimension")

        # Confirm match_vectors function exists
        fn = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_proc WHERE proname = 'match_vectors'"
        )
        print(f"[OK] match_vectors function present: {fn}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

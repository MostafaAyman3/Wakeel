"""
AERIE — Connection Verifier + Schema Extractor
يتحقق من الـ DB connections والـ OpenAI API
ولو كل حاجة شغالة يسحب الـ schema من Supabase ويحفظها في ملف
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# تحميل الـ .env من مجلد المشروع
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(env_path)

print("=" * 60)
print("AERIE — Connection Verifier + Schema Extractor")
print("=" * 60)

results = {}

# ─────────────────────────────────────────
# 1. فحص متغيرات البيئة الأساسية
# ─────────────────────────────────────────
print("\n[1] Checking environment variables...")

required_vars = {
    "DATABASE_URL": "Main DB (async)",
    "DATABASE_URL_DIRECT": "Direct DB (sync)",
    "READONLY_DB_URL": "Read-Only DB (M1 agent)",
    "OPENAI_API_KEY": "OpenAI API Key",
}

missing = []
for var, label in required_vars.items():
    val = os.getenv(var, "")
    if not val or "YOUR-PASSWORD" in val or "<<" in val:
        print(f"  ❌ {label} ({var}) — NOT SET or still placeholder")
        missing.append(var)
    else:
        # إظهار جزء من القيمة بس مش كلها للأمان
        safe_preview = val[:30] + "..." if len(val) > 30 else val
        print(f"  ✅ {label} — {safe_preview}")

if missing:
    print(f"\n⚠️  {len(missing)} variable(s) missing. Fix .env then re-run.")
    sys.exit(1)

results["env_check"] = "PASS"


# ─────────────────────────────────────────
# 2. فحص Main DB Connection (psycopg2 sync)
# ─────────────────────────────────────────
print("\n[2] Testing Main DB connection (read-write via Pooler)...")
try:
    import psycopg2
    # نستخدم الـ Pooler (port 6543) مش الـ Direct (port 5432 — محجوب في free tier)
    conn_str = os.getenv("DATABASE_URL")
    conn_str = conn_str.replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg2.connect(conn_str, connect_timeout=15)
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"  ✅ Connected! PostgreSQL: {version[:50]}...")
    cursor.close()
    conn.close()
    results["main_db"] = "PASS"
except ImportError:
    print("  ⚠️  psycopg2 not installed — trying psycopg2-binary")
    results["main_db"] = "SKIP (no psycopg2)"
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    results["main_db"] = f"FAIL: {e}"


# ─────────────────────────────────────────
# 3. فحص Read-Only DB Connection
# ─────────────────────────────────────────
print("\n[3] Testing Read-Only DB connection (erp_readonly)...")
try:
    import psycopg2
    readonly_url = os.getenv("READONLY_DB_URL")
    readonly_url = readonly_url.replace("postgresql+asyncpg://", "postgresql://")
    conn_ro = psycopg2.connect(readonly_url, connect_timeout=10)
    cursor_ro = conn_ro.cursor()
    # اختبار بسيط — SELECT فقط
    cursor_ro.execute("SELECT current_user, current_database();")
    user, db = cursor_ro.fetchone()
    print(f"  ✅ Connected as: {user} on database: {db}")
    # تأكد إنه read-only فعلاً
    try:
        cursor_ro.execute("CREATE TABLE _test_rw (id int);")
        print("  ⚠️  WARNING: Read-Only user can CREATE tables — check permissions!")
        cursor_ro.execute("DROP TABLE _test_rw;")
        results["readonly_db"] = "WARN: user has write access!"
    except psycopg2.Error:
        print("  ✅ Confirmed: User is READ-ONLY (write attempt rejected)")
        results["readonly_db"] = "PASS (read-only confirmed)"
    finally:
        conn_ro.rollback()
    cursor_ro.close()
    conn_ro.close()
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    results["readonly_db"] = f"FAIL: {e}"


# ─────────────────────────────────────────
# 4. فحص pgvector Extension
# ─────────────────────────────────────────
print("\n[4] Checking pgvector extension...")
try:
    import psycopg2
    # Pooler كمان هنا
    conn_str = os.getenv("DATABASE_URL")
    conn_str = conn_str.replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg2.connect(conn_str, connect_timeout=15)
    cursor = conn.cursor()
    cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';")
    row = cursor.fetchone()
    if row:
        print(f"  ✅ pgvector installed — version: {row[1]}")
        results["pgvector"] = f"PASS (v{row[1]})"
    else:
        print("  ❌ pgvector NOT installed — run: CREATE EXTENSION vector;")
        results["pgvector"] = "FAIL: not installed"
    cursor.close()
    conn.close()
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    results["pgvector"] = f"FAIL: {e}"


# ─────────────────────────────────────────
# 5. فحص OpenAI API Key
# ─────────────────────────────────────────
print("\n[5] Testing OpenAI API key...")
try:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # استدعاء بسيط جداً — بدون تكلفة تقريباً
    models = client.models.list()
    has_gpt4o = any("gpt-4o" in m.id for m in models.data)
    has_mini = any("gpt-4o-mini" in m.id for m in models.data)
    print(f"  ✅ API Key valid!")
    print(f"  {'✅' if has_gpt4o else '❌'} gpt-4o available: {has_gpt4o}")
    print(f"  {'✅' if has_mini else '❌'} gpt-4o-mini available: {has_mini}")
    results["openai"] = "PASS"
except ImportError:
    print("  ⚠️  openai package not installed — run: pip install openai")
    results["openai"] = "SKIP (no openai)"
except Exception as e:
    print(f"  ❌ FAILED: {e}")
    results["openai"] = f"FAIL: {e}"


# ─────────────────────────────────────────
# 6. سحب الـ Schema من Supabase
# ─────────────────────────────────────────
print("\n[6] Extracting database schema from Supabase...")

schema_data = {}

try:
    import psycopg2
    # Schema extraction عبر الـ Pooler
    conn_str = os.getenv("DATABASE_URL")
    conn_str = conn_str.replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg2.connect(conn_str, connect_timeout=15)
    cursor = conn.cursor()

    # ── الجداول في الـ public schema ──
    cursor.execute("""
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type IN ('BASE TABLE', 'VIEW')
        ORDER BY table_type, table_name;
    """)
    tables = cursor.fetchall()
    print(f"  Found {len(tables)} tables/views in public schema")

    for table_name, table_type in tables:
        table_info = {
            "type": table_type,
            "columns": [],
            "primary_keys": [],
            "foreign_keys": [],
            "indexes": [],
            "row_count": None,
        }

        # ── الأعمدة ──
        cursor.execute("""
            SELECT
                c.column_name,
                c.data_type,
                c.udt_name,
                c.character_maximum_length,
                c.is_nullable,
                c.column_default,
                c.ordinal_position
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
              AND c.table_name = %s
            ORDER BY c.ordinal_position;
        """, (table_name,))
        cols = cursor.fetchall()
        for col in cols:
            col_info = {
                "name": col[0],
                "data_type": col[1],
                "udt_name": col[2],
                "max_length": col[3],
                "nullable": col[4] == "YES",
                "default": col[5],
                "position": col[6],
            }
            table_info["columns"].append(col_info)

        # ── Primary Keys ──
        cursor.execute("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = %s
            ORDER BY kcu.ordinal_position;
        """, (table_name,))
        pks = cursor.fetchall()
        table_info["primary_keys"] = [pk[0] for pk in pks]

        # ── Foreign Keys ──
        cursor.execute("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table,
                ccu.column_name AS foreign_column,
                tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
              ON ccu.constraint_name = tc.constraint_name
             AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = %s;
        """, (table_name,))
        fks = cursor.fetchall()
        for fk in fks:
            table_info["foreign_keys"].append({
                "column": fk[0],
                "references_table": fk[1],
                "references_column": fk[2],
                "constraint_name": fk[3],
            })

        # ── Indexes ──
        cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = %s;
        """, (table_name,))
        indexes = cursor.fetchall()
        for idx in indexes:
            table_info["indexes"].append({
                "name": idx[0],
                "definition": idx[1],
            })

        # ── Row Count (تقريبي — سريع) ──
        try:
            cursor.execute(f'SELECT COUNT(*) FROM public."{table_name}";')
            table_info["row_count"] = cursor.fetchone()[0]
        except Exception:
            table_info["row_count"] = "unknown"

        schema_data[table_name] = table_info
        print(f"  ✅ {table_name} ({len(table_info['columns'])} cols, {table_info['row_count']} rows)")

    cursor.close()
    conn.close()
    results["schema_extraction"] = f"PASS ({len(schema_data)} tables)"

except Exception as e:
    print(f"  ❌ Schema extraction FAILED: {e}")
    results["schema_extraction"] = f"FAIL: {e}"
    schema_data = {}


# ─────────────────────────────────────────
# 7. حفظ الـ Schema في ملف Markdown
# ─────────────────────────────────────────
if schema_data:
    print("\n[7] Generating schema reference file...")

    output_path = project_root / "docs" / "architecture" / "db_schema_reference.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Database Schema Reference — AERIE",
        "",
        "> **Auto-generated** — لا تعدّل يدوياً. شغّل `scripts/verify_connections.py` لتحديث.",
        f"> **Generated at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"> **Source:** Supabase (public schema)",
        f"> **Total tables:** {len(schema_data)}",
        "",
        "---",
        "",
    ]

    # جدول المحتوى
    lines.append("## Table of Contents")
    lines.append("")
    for tname in sorted(schema_data.keys()):
        lines.append(f"- [{tname}](#{tname.replace('_', '-')})")
    lines.append("")
    lines.append("---")
    lines.append("")

    # تفاصيل كل جدول
    for tname, tinfo in sorted(schema_data.items()):
        lines.append(f"## `{tname}`")
        lines.append("")

        meta_parts = [f"**Type:** {tinfo['type']}"]
        if tinfo["row_count"] is not None:
            meta_parts.append(f"**Rows:** {tinfo['row_count']:,}")
        if tinfo["primary_keys"]:
            meta_parts.append(f"**PK:** `{'`, `'.join(tinfo['primary_keys'])}`")
        lines.append(" | ".join(meta_parts))
        lines.append("")

        # جدول الأعمدة
        lines.append("| Column | Type | Nullable | Default | Notes |")
        lines.append("|--------|------|----------|---------|-------|")
        for col in tinfo["columns"]:
            dtype = col["data_type"]
            if col["udt_name"] and col["udt_name"] not in ("text", "int4", "int8", "bool", "float8"):
                dtype = col["udt_name"]
            if col["max_length"]:
                dtype += f"({col['max_length']})"
            is_pk = "🔑 PK" if col["name"] in tinfo["primary_keys"] else ""
            nullable = "YES" if col["nullable"] else "NO"
            default = col["default"] or ""
            # اختصر الـ default لو طويل
            if len(default) > 40:
                default = default[:37] + "..."
            lines.append(f"| `{col['name']}` | `{dtype}` | {nullable} | `{default}` | {is_pk} |")
        lines.append("")

        # Foreign Keys
        if tinfo["foreign_keys"]:
            lines.append("**Foreign Keys:**")
            lines.append("")
            for fk in tinfo["foreign_keys"]:
                lines.append(f"- `{fk['column']}` → `{fk['references_table']}.{fk['references_column']}`")
            lines.append("")

        # Indexes (غير الـ PK)
        non_pk_indexes = [i for i in tinfo["indexes"] if "pkey" not in i["name"]]
        if non_pk_indexes:
            lines.append("**Indexes:**")
            lines.append("")
            for idx in non_pk_indexes:
                lines.append(f"- `{idx['name']}`: `{idx['definition']}`")
            lines.append("")

        lines.append("---")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✅ Schema saved to: {output_path}")
    results["schema_file"] = str(output_path)

    # حفظ JSON أيضاً للاستخدام البرمجي
    json_path = project_root / "docs" / "architecture" / "db_schema_reference.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "source": "supabase",
            "schema": "public",
            "tables": schema_data,
        }, f, indent=2, ensure_ascii=False, default=str)
    print(f"  ✅ JSON schema saved to: {json_path}")


# ─────────────────────────────────────────
# ملخص النتائج
# ─────────────────────────────────────────
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
for check, status in results.items():
    icon = "✅" if "PASS" in status else ("⚠️ " if "WARN" in status or "SKIP" in status else "❌")
    print(f"  {icon} {check:25} {status}")
print()

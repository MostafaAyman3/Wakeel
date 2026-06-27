"""
M2 Phase 0 — Demo Runner
========================
شغّله مباشرة بدون pytest:
    python tests/integration/run_m2_demo.py

بيعمل إيه:
  1. بيعمل GET /api/v1/m2/inventory  → يعرض حالة المخزون
  2. بيعمل POST /api/v1/m2/analyze   → يشغّل الـ agent ويعرض التنبيهات
"""

import asyncio
import json
import sys
from pathlib import Path

# ── Project root on sys.path ──────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from httpx import AsyncClient, ASGITransport
from backend.core.database import AsyncSessionFactory, ReadonlyAsyncSessionFactory
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.core.config import get_settings

# ── Use NullPool so each request gets a fresh connection ──────────
settings = get_settings()
_CONNECT_ARGS = {"statement_cache_size": 0, "command_timeout": 60}

_engine = create_async_engine(
    settings.database_url, poolclass=NullPool, echo=False, connect_args=_CONNECT_ARGS
)
_session_factory = async_sessionmaker(
    bind=_engine, class_=AsyncSession,
    expire_on_commit=False, autoflush=False, autocommit=False,
)

# Patch the engines before importing app
import backend.core.database as _db_mod
_db_mod.engine = _engine
_db_mod.AsyncSessionFactory = _session_factory
_db_mod.ReadonlyAsyncSessionFactory = _session_factory

from backend.main import app   # noqa: E402  (must be after patch)

# ── Helpers ───────────────────────────────────────────────────────

SEP  = "=" * 60
SEP2 = "-" * 60

STATUS_EMOJI = {
    "low_stock":          "[!] LOW STOCK",
    "predicted_shortage": "[~] PREDICTED SHORTAGE",
    "slow_moving":        "[s] SLOW MOVING",
    "near_expiry":        "[e] NEAR EXPIRY",
    "safe":               "[ok] SAFE",
}


def _fmt_status(status: str) -> str:
    return STATUS_EMOJI.get(status, f"[?] {status}")


def _print_inventory(data: dict) -> None:
    summary = data.get("summary", {})
    products = data.get("products", [])

    print(f"\n{SEP}")
    print("  GET /api/v1/m2/inventory")
    print(SEP)

    print(f"\nSummary ({summary.get('total', 0)} products total):")
    print(f"  Low stock          : {summary.get('low_stock', 0)}")
    print(f"  Predicted shortage : {summary.get('predicted_shortage', 0)}")
    print(f"  Slow moving        : {summary.get('slow_moving', 0)}")
    print(f"  Near expiry        : {summary.get('near_expiry', 0)}")
    print(f"  Safe               : {summary.get('safe', 0)}")

    print(f"\n{SEP2}")
    print(f"  {'SKU':<12} {'Name':<30} {'Qty':>5} {'Reorder':>7} {'DaysLeft':>9}  Status")
    print(SEP2)

    for p in products:
        days = p.get("days_until_stockout", 0)
        days_str = f"{days:.1f}d" if days < 9999 else "   --"
        status_label = _fmt_status(p.get("status", ""))
        print(
            f"  {p.get('sku',''):<12} "
            f"{p.get('name','')[:29]:<30} "
            f"{p.get('quantity', 0):>5} "
            f"{p.get('reorder_point', 0):>7} "
            f"{days_str:>9}  "
            f"{status_label}"
        )


def _print_analyze(data: dict) -> None:
    summary   = data.get("scan_summary", {})
    alerts    = data.get("alerts", [])
    rfq_drafts = data.get("rfq_drafts", [])
    pricing   = data.get("pricing_recs", [])
    language  = data.get("language", "?")

    print(f"\n{SEP}")
    print("  POST /api/v1/m2/analyze")
    print(SEP)
    print(f"\nLanguage : {language}")
    print(f"Trigger  : {summary.get('trigger_source', '?')}")
    print(f"Scanned  : {summary.get('total_products_checked', '?')} products")
    print(f"Flagged  : {summary.get('low_stock_count',0)} low | "
          f"{summary.get('predicted_shortage_count',0)} shortage | "
          f"{summary.get('slow_moving_count',0)} slow | "
          f"{summary.get('near_expiry_count',0)} expiry")

    # ── Alerts ────────────────────────────────────────────────────
    if alerts:
        print(f"\n{SEP2}")
        print(f"  Alerts generated: {len(alerts)}")
        print(SEP2)
        for i, a in enumerate(alerts, 1):
            meta = a.get("metadata", {})
            print(f"\n  [{i}] {a.get('alert_type','').upper()}")
            print(f"       Product ID : {str(a.get('product_id',''))[:8]}...")
            print(f"       Quantity   : {meta.get('current_quantity','?')} "
                  f"(reorder: {meta.get('reorder_point','?')})")
            if meta.get("days_until_stockout"):
                print(f"       Days left  : {meta['days_until_stockout']:.1f} days")
            if meta.get("expiry_date"):
                print(f"       Expiry     : {meta['expiry_date']}")
    else:
        print("\n  No alerts generated.")

    # ── RFQ Drafts ────────────────────────────────────────────────
    if rfq_drafts:
        print(f"\n{SEP2}")
        print(f"  RFQ Drafts generated: {len(rfq_drafts)}")
        print(SEP2)
        for i, r in enumerate(rfq_drafts, 1):
            draft = r.get("draft_text", "")
            preview = draft[:200].replace("\n", " ") if draft else "(empty)"
            print(f"\n  [{i}] RFQ ID: {str(r.get('rfq_id',''))[:8]}...")
            print(f"       Product : {str(r.get('product_id',''))[:8]}...")
            print(f"       Draft preview: {preview}...")
    else:
        print("\n  No RFQ drafts generated.")

    # ── Pricing Recs ──────────────────────────────────────────────
    if pricing:
        print(f"\n{SEP2}")
        print(f"  Pricing recommendations: {len(pricing)}")
        print(SEP2)
        for i, p in enumerate(pricing, 1):
            rec = p.get("recommendation", "")[:150].replace("\n", " ")
            print(f"\n  [{i}] Product: {str(p.get('product_id',''))[:8]}...")
            print(f"       Recommendation: {rec}")


# ── Main runner ───────────────────────────────────────────────────

async def main() -> None:
    print(SEP)
    print("  M2 Phase 0 — Integration Demo")
    print("  Connecting to Supabase DB...")
    print(SEP)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:

        # ── Step 1: Inventory status ──────────────────────────────
        print("\n[1/2] Calling GET /api/v1/m2/inventory ...")
        resp = await client.get("/api/v1/m2/inventory")

        if resp.status_code == 200:
            _print_inventory(resp.json())
        else:
            print(f"  ERROR {resp.status_code}: {resp.text[:400]}")
            return

        # ── Step 2: Analyze ───────────────────────────────────────
        print(f"\n\n[2/2] Calling POST /api/v1/m2/analyze ...")
        resp2 = await client.post(
            "/api/v1/m2/analyze",
            json={"trigger_source": "manual", "language": "en"},
        )

        if resp2.status_code == 200:
            _print_analyze(resp2.json())
        else:
            print(f"  ERROR {resp2.status_code}: {resp2.text[:400]}")
            return

    print(f"\n{SEP}")
    print("  Demo complete.")
    print(SEP)


if __name__ == "__main__":
    asyncio.run(main())

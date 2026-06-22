"""
M2 Seed Script — Inventory Demo Data
=====================================
Sprint 0 deliverable.

PURPOSE
-------
Sets up realistic inventory scenarios in the `inventory` table so that
InventoryCheckNode has interesting data to detect during development
and demos.  Without this seed, all products would have identical
default values and no alert would ever fire.

SCENARIOS COVERED (one for each M2 DetectionType)
--------------------------------------------------
Scenario A — low_stock (2 products)
    quantity <= reorder_point
    The simplest case: stock already hit the minimum threshold.

Scenario B — predicted_shortage (2 products)
    quantity > reorder_point  BUT  quantity / avg_daily_sales < lead_time_days
    The system is "above red line" but will run out before the next
    shipment can arrive.  This is the proactive / intelligent detection.

Scenario C — slow_moving (2 products)
    high quantity, very low avg_daily_sales → high days_until_stockout
    turnover_rate < 0.5 per month.  Capital locked in stagnant stock.

Scenario D — near_expiry (2 products)
    expiry_date within 15 days, significant quantity still in stock.
    Risk of write-off if not sold/discounted quickly.

Scenario E — safe (remaining products)
    Normal levels: quantity comfortably above reorder_point, good
    turnover, no expiry concern.  These should NOT trigger any alert.

HOW IT WORKS
------------
1. Fetches all rows from `inventory JOIN products` ordered by category.
2. Assigns scenarios to the first 8 rows (2 per scenario).
3. Updates them with the seed values.
4. Remaining rows get "safe" defaults.

USAGE
-----
    # From the project root:
    python -m database.seeds.m2_seed_inventory

    # Or directly:
    python database/seeds/m2_seed_inventory.py

REQUIREMENTS
------------
    pip install asyncpg python-dotenv
    DATABASE_URL must be set in .env (postgresql://... or postgresql+asyncpg://...)
"""

import asyncio
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# ── Project root on sys.path so we can import backend.core.config ──
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env", override=False)

try:
    import asyncpg
except ImportError:
    print("ERROR: asyncpg not installed.  Run: pip install asyncpg")
    sys.exit(1)


# ── Scenario definitions ──────────────────────────────────────────

TODAY = date.today()

# Each dict maps to columns in the `inventory` table.
# Keys match column names exactly.
SCENARIOS: list[dict] = [
    # ── A: low_stock (2 products) ─────────────────────────────────
    {
        "_label": "low_stock #1",
        # quantity = reorder_point - 3  (set below in the loop using actual reorder_point)
        "_quantity_offset": -3,
        "lead_time_days": 7,
        "avg_daily_sales": 1.5,
        "expiry_date": None,
    },
    {
        "_label": "low_stock #2",
        "_quantity_offset": -5,
        "lead_time_days": 5,
        "avg_daily_sales": 2.0,
        "expiry_date": None,
    },

    # ── B: predicted_shortage (2 products) ────────────────────────
    # quantity is 10 above reorder_point, but avg_daily_sales is high
    # so days_until_stockout = quantity / avg_daily_sales < lead_time_days
    {
        "_label": "predicted_shortage #1",
        "_quantity_offset": +10,       # above reorder_point
        "lead_time_days": 14,          # 2 weeks to receive stock
        "avg_daily_sales": 4.0,        # days_until_stockout ≈ (rp+10)/4 < 14
        "expiry_date": None,
    },
    {
        "_label": "predicted_shortage #2",
        "_quantity_offset": +8,
        "lead_time_days": 10,
        "avg_daily_sales": 3.5,        # days_until_stockout ≈ (rp+8)/3.5 < 10
        "expiry_date": None,
    },

    # ── C: slow_moving (2 products) ───────────────────────────────
    # High quantity, very low daily sales → turnover rate < 0.5/month
    {
        "_label": "slow_moving #1",
        "_quantity_abs": 120,          # override: fixed quantity regardless of reorder_point
        "lead_time_days": 7,
        "avg_daily_sales": 0.15,       # ~4.5 units/month → very slow
        "expiry_date": None,
    },
    {
        "_label": "slow_moving #2",
        "_quantity_abs": 95,
        "lead_time_days": 7,
        "avg_daily_sales": 0.20,
        "expiry_date": None,
    },

    # ── D: near_expiry (2 products) ───────────────────────────────
    # Expiry date within 15 days, still have significant stock
    {
        "_label": "near_expiry #1",
        "_quantity_abs": 60,
        "lead_time_days": 7,
        "avg_daily_sales": 1.0,
        "expiry_date": TODAY + timedelta(days=12),
    },
    {
        "_label": "near_expiry #2",
        "_quantity_abs": 45,
        "lead_time_days": 7,
        "avg_daily_sales": 0.8,
        "expiry_date": TODAY + timedelta(days=8),
    },
]

SAFE_DEFAULTS = {
    "lead_time_days": 7,
    "avg_daily_sales": 1.8,
    "expiry_date": None,
    # quantity for safe rows = reorder_point * 3  (set in loop)
}


# ── DB connection helper ──────────────────────────────────────────

def _clean_db_url(url: str) -> str:
    """asyncpg doesn't accept the SQLAlchemy '+asyncpg' driver prefix."""
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def get_connection() -> asyncpg.Connection:
    raw_url = os.environ.get("DATABASE_URL") or os.environ.get("database_url")
    if not raw_url:
        raise RuntimeError(
            "DATABASE_URL not found in environment. "
            "Check your .env file."
        )
    return await asyncpg.connect(_clean_db_url(raw_url))


# ── Seed logic ────────────────────────────────────────────────────

async def seed() -> None:
    print("M2 Inventory Seed — connecting to database…")
    conn = await get_connection()

    try:
        # 1. Fetch all inventory rows with product info, ordered consistently.
        rows = await conn.fetch("""
            SELECT
                i.id            AS inv_id,
                i.product_id,
                i.quantity,
                i.reorder_point,
                p.name,
                p.name_ar,
                p.category,
                p.sku
            FROM inventory i
            JOIN products p ON p.id = i.product_id
            ORDER BY p.category, p.name
        """)

        total = len(rows)
        print(f"Found {total} inventory records.")

        if total < 8:
            print(
                f"WARNING: Only {total} inventory records found. "
                "Need at least 8 to cover all 4 demo scenarios. "
                "Seeding what we can."
            )

        # 2. Apply scenarios to first 8 rows; safe defaults to the rest.
        async with conn.transaction():
            for idx, row in enumerate(rows):
                inv_id      = row["inv_id"]
                rp          = row["reorder_point"] or 10
                product_name = row["name"]

                if idx < len(SCENARIOS):
                    sc = SCENARIOS[idx]

                    # Resolve quantity
                    if "_quantity_abs" in sc:
                        new_qty = sc["_quantity_abs"]
                    elif "_quantity_offset" in sc:
                        new_qty = max(0, rp + sc["_quantity_offset"])
                    else:
                        new_qty = rp * 2  # fallback

                    await conn.execute("""
                        UPDATE inventory
                        SET
                            quantity        = $1,
                            lead_time_days  = $2,
                            avg_daily_sales = $3,
                            expiry_date     = $4,
                            updated_at      = now()
                        WHERE id = $5
                    """,
                        new_qty,
                        sc["lead_time_days"],
                        sc["avg_daily_sales"],
                        sc["expiry_date"],
                        inv_id,
                    )

                    label = sc["_label"]
                    print(
                        f"  [{idx+1:02d}] {product_name[:35]:<35} "
                        f"→ {label}  "
                        f"(qty={new_qty}, rp={rp}, "
                        f"avg_daily={sc['avg_daily_sales']}, "
                        f"lead={sc['lead_time_days']}d, "
                        f"expiry={sc['expiry_date']})"
                    )

                else:
                    # Safe row: quantity = 3× reorder_point
                    safe_qty = rp * 3

                    await conn.execute("""
                        UPDATE inventory
                        SET
                            quantity        = $1,
                            lead_time_days  = $2,
                            avg_daily_sales = $3,
                            expiry_date     = $4,
                            updated_at      = now()
                        WHERE id = $5
                    """,
                        safe_qty,
                        SAFE_DEFAULTS["lead_time_days"],
                        SAFE_DEFAULTS["avg_daily_sales"],
                        SAFE_DEFAULTS["expiry_date"],
                        inv_id,
                    )

                    print(
                        f"  [{idx+1:02d}] {product_name[:35]:<35} "
                        f"→ safe  (qty={safe_qty}, rp={rp})"
                    )

        print("\nSeed complete. Summary:")
        print("  Scenario A (low_stock):          2 products")
        print("  Scenario B (predicted_shortage): 2 products")
        print("  Scenario C (slow_moving):        2 products")
        print("  Scenario D (near_expiry):        2 products")
        print(f"  Scenario E (safe):               {max(0, total - 8)} products")
        print("\nAll 4 M2 detection scenarios are now present in the DB.")

    finally:
        await conn.close()


# ── Entry point ───────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(seed())

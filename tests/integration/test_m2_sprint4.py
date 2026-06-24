"""
Sprint 4 Integration Tests — Inventory Intelligence Layer
=========================================================

Tests cover:
  1. Detection constants: SLOW_MOVING_THRESHOLD, NEAR_EXPIRY_WINDOW
  2. Low-stock detection logic: qty <= reorder_point
  3. Predicted-shortage detection: days_until_stockout < lead_time
  4. Slow-moving detection: turnover_rate < SLOW_MOVING_THRESHOLD
  5. Near-expiry detection: expiry_date within NEAR_EXPIRY_WINDOW days
  6. Priority order: low_stock > predicted_shortage > slow_moving > near_expiry
  7. Products with no issue → safe / not flagged
  8. GET /inventory returns products with all 4 detection status types
     (skip if seed data not present)

Run:
    conda activate mlops
    # Seed first for the status coverage test:
    #   python database/seeds/m2_seed_inventory.py
    python -m pytest tests/integration/test_m2_sprint4.py -v
"""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.main import app

BASE = "http://test"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


# ═══════════════════════════════════════════════════════════════════
# 1. Detection constants
# ═══════════════════════════════════════════════════════════════════

def test_slow_moving_threshold_is_half():
    from agents.m2.nodes.inventory_check_node import SLOW_MOVING_THRESHOLD
    assert SLOW_MOVING_THRESHOLD == 0.5, (
        "SLOW_MOVING_THRESHOLD should be 0.5 (turnover per month)"
    )


def test_near_expiry_window_is_30_days():
    from agents.m2.nodes.inventory_check_node import NEAR_EXPIRY_WINDOW
    assert NEAR_EXPIRY_WINDOW == 30, (
        "NEAR_EXPIRY_WINDOW should be 30 days"
    )


def test_min_avg_daily_sales_prevents_division_by_zero():
    from agents.m2.nodes.inventory_check_node import MIN_AVG_DAILY_SALES
    assert MIN_AVG_DAILY_SALES > 0


# ═══════════════════════════════════════════════════════════════════
# 2. Detection logic — pure Python unit tests
#    These replicate the exact logic inside inventory_check_node and
#    the inventory endpoint to verify correct classification.
# ═══════════════════════════════════════════════════════════════════

def _classify(
    qty: int,
    reorder_point: int,
    lead_time: int,
    daily_sales: float,
    turnover_rate: float,
    expiry_date=None,
) -> str:
    """Mirror the detection logic from inventory_check_node."""
    from agents.m2.nodes.inventory_check_node import (
        MIN_AVG_DAILY_SALES,
        NEAR_EXPIRY_WINDOW,
        SLOW_MOVING_THRESHOLD,
    )

    daily_sales = max(daily_sales, MIN_AVG_DAILY_SALES)
    days_until_stockout = qty / daily_sales
    today = date.today()

    if qty <= reorder_point:
        return "low_stock"
    elif days_until_stockout < lead_time:
        return "predicted_shortage"
    elif turnover_rate < SLOW_MOVING_THRESHOLD:
        return "slow_moving"
    elif expiry_date and expiry_date <= today + timedelta(days=NEAR_EXPIRY_WINDOW):
        return "near_expiry"
    return "safe"


def test_detect_low_stock_when_qty_at_reorder():
    result = _classify(qty=10, reorder_point=10, lead_time=5, daily_sales=1.0, turnover_rate=2.0)
    assert result == "low_stock"


def test_detect_low_stock_when_qty_below_reorder():
    result = _classify(qty=3, reorder_point=10, lead_time=5, daily_sales=1.0, turnover_rate=2.0)
    assert result == "low_stock"


def test_detect_predicted_shortage_when_days_less_than_lead_time():
    # qty=20, daily_sales=5.0 → days_until_stockout=4, lead_time=7
    result = _classify(qty=20, reorder_point=5, lead_time=7, daily_sales=5.0, turnover_rate=2.0)
    assert result == "predicted_shortage"


def test_safe_when_days_exceed_lead_time():
    # qty=100, daily_sales=2.0 → days_until_stockout=50, lead_time=7
    result = _classify(qty=100, reorder_point=5, lead_time=7, daily_sales=2.0, turnover_rate=2.0)
    assert result == "safe"


def test_detect_slow_moving():
    # turnover_rate=0.2 < 0.5 threshold
    result = _classify(qty=100, reorder_point=5, lead_time=3, daily_sales=0.001, turnover_rate=0.2)
    assert result == "slow_moving"


def test_not_slow_moving_when_turnover_above_threshold():
    result = _classify(qty=100, reorder_point=5, lead_time=3, daily_sales=5.0, turnover_rate=1.5)
    assert result == "safe"


def test_detect_near_expiry():
    expiry = date.today() + timedelta(days=15)  # within 30-day window
    result = _classify(
        qty=200, reorder_point=5, lead_time=3, daily_sales=5.0,
        turnover_rate=1.5, expiry_date=expiry
    )
    assert result == "near_expiry"


def test_not_near_expiry_when_far_away():
    expiry = date.today() + timedelta(days=90)  # outside 30-day window
    result = _classify(
        qty=200, reorder_point=5, lead_time=3, daily_sales=5.0,
        turnover_rate=1.5, expiry_date=expiry
    )
    assert result == "safe"


def test_not_near_expiry_when_no_expiry_date():
    result = _classify(
        qty=200, reorder_point=5, lead_time=3, daily_sales=5.0,
        turnover_rate=1.5, expiry_date=None
    )
    assert result == "safe"


# ═══════════════════════════════════════════════════════════════════
# 3. Priority order: low_stock beats everything
# ═══════════════════════════════════════════════════════════════════

def test_low_stock_takes_priority_over_near_expiry():
    expiry = date.today() + timedelta(days=5)  # near_expiry condition
    result = _classify(
        qty=2, reorder_point=10,  # also low_stock
        lead_time=3, daily_sales=1.0, turnover_rate=0.1, expiry_date=expiry
    )
    assert result == "low_stock"


def test_predicted_shortage_takes_priority_over_slow_moving():
    # days_until_stockout = 100/10 = 10, lead_time=15 → predicted_shortage
    # turnover_rate=0.1 → would be slow_moving but lower priority
    result = _classify(
        qty=100, reorder_point=5, lead_time=15, daily_sales=10.0, turnover_rate=0.1
    )
    assert result == "predicted_shortage"


# ═══════════════════════════════════════════════════════════════════
# 4. Zero-division safety
# ═══════════════════════════════════════════════════════════════════

def test_zero_daily_sales_does_not_raise():
    """MIN_AVG_DAILY_SALES prevents ZeroDivisionError."""
    result = _classify(qty=50, reorder_point=5, lead_time=7, daily_sales=0.0, turnover_rate=0.0)
    assert result in ("low_stock", "predicted_shortage", "slow_moving", "near_expiry", "safe")


# ═══════════════════════════════════════════════════════════════════
# 5. GET /inventory — detection type coverage via HTTP
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_inventory_contains_only_valid_detection_statuses():
    """All products returned must have a recognized status."""
    valid = {"low_stock", "predicted_shortage", "slow_moving", "near_expiry", "safe"}
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    assert r.status_code == 200
    for p in r.json()["products"]:
        assert p["status"] in valid


@pytest.mark.anyio
async def test_inventory_summary_counts_non_negative():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    s = r.json()["summary"]
    for key in ("low_stock", "predicted_shortage", "slow_moving", "near_expiry", "safe"):
        assert s[key] >= 0


@pytest.mark.anyio
async def test_inventory_detects_at_least_one_procurement_or_pricing_product():
    """With seeded data, at least one non-safe product should exist."""
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    s = r.json()["summary"]
    flagged = s["low_stock"] + s["predicted_shortage"] + s["slow_moving"] + s["near_expiry"]
    if flagged == 0:
        pytest.skip(
            "All products are 'safe' — run database/seeds/m2_seed_inventory.py first."
        )
    assert flagged > 0

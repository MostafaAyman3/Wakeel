"""
Sprint 1 Integration Tests — Backend & Inventory Check
=======================================================

Tests cover:
  1. GET /api/v1/m2/inventory → 200
  2. Response schema: products list + summary dict
  3. Each product has all required fields
  4. Product status is a valid enum value
  5. Summary counts are internally consistent
  6. Detection constants have the correct values
  7. inventory_check_node returns the correct dict structure

Run:
    conda activate mlops
    python -m pytest tests/integration/test_m2_sprint1.py -v
"""

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.main import app

BASE = "http://test"
VALID_STATUSES = {"low_stock", "predicted_shortage", "slow_moving", "near_expiry", "safe"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


# ═══════════════════════════════════════════════════════════════════
# 1. GET /api/v1/m2/inventory — HTTP layer
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_inventory_endpoint_returns_200():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    assert r.status_code == 200, r.text[:300]


@pytest.mark.anyio
async def test_inventory_response_has_products_and_summary():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    data = r.json()
    assert "products" in data, "Response missing 'products'"
    assert "summary" in data, "Response missing 'summary'"
    assert isinstance(data["products"], list)
    assert isinstance(data["summary"], dict)


@pytest.mark.anyio
async def test_inventory_summary_has_required_keys():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    summary = r.json()["summary"]
    for key in ("total", "low_stock", "predicted_shortage", "slow_moving", "near_expiry", "safe"):
        assert key in summary, f"summary missing key: {key}"


@pytest.mark.anyio
async def test_inventory_summary_total_matches_products_count():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    data = r.json()
    assert data["summary"]["total"] == len(data["products"])


@pytest.mark.anyio
async def test_inventory_summary_counts_add_up():
    """low_stock + predicted_shortage + slow_moving + near_expiry + safe == total."""
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    s = r.json()["summary"]
    computed = s["low_stock"] + s["predicted_shortage"] + s["slow_moving"] + s["near_expiry"] + s["safe"]
    assert computed == s["total"], (
        f"Category counts ({computed}) don't match total ({s['total']})"
    )


@pytest.mark.anyio
async def test_inventory_each_product_has_required_fields():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    products = r.json()["products"]

    required = (
        "product_id", "sku", "name", "name_ar", "category",
        "quantity", "reorder_point", "lead_time_days",
        "avg_daily_sales", "days_until_stockout", "status",
    )
    for p in products:
        for field in required:
            assert field in p, f"Product missing field: {field}"


@pytest.mark.anyio
async def test_inventory_product_status_is_valid():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    for p in r.json()["products"]:
        assert p["status"] in VALID_STATUSES, (
            f"Invalid status '{p['status']}' for product {p.get('sku')}"
        )


@pytest.mark.anyio
async def test_inventory_product_numeric_fields_are_non_negative():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    for p in r.json()["products"]:
        assert p["quantity"] >= 0
        assert p["reorder_point"] >= 0
        assert p["avg_daily_sales"] >= 0
        assert p["days_until_stockout"] >= 0


# ═══════════════════════════════════════════════════════════════════
# 2. Detection constants
# ═══════════════════════════════════════════════════════════════════

def test_slow_moving_threshold_constant():
    from agents.m2.nodes.inventory_check_node import SLOW_MOVING_THRESHOLD
    assert SLOW_MOVING_THRESHOLD == 0.5


def test_near_expiry_window_constant():
    from agents.m2.nodes.inventory_check_node import NEAR_EXPIRY_WINDOW
    assert NEAR_EXPIRY_WINDOW == 30


def test_min_avg_daily_sales_constant():
    from agents.m2.nodes.inventory_check_node import MIN_AVG_DAILY_SALES
    assert MIN_AVG_DAILY_SALES > 0, "MIN_AVG_DAILY_SALES must be positive to prevent ZeroDivisionError"


# ═══════════════════════════════════════════════════════════════════
# 3. inventory_check_node — direct function call
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_inventory_check_node_returns_required_keys():
    from agents.m2.nodes.inventory_check_node import inventory_check_node

    result = await inventory_check_node({"trigger_source": "manual"})

    assert "flagged_products" in result
    assert "scan_summary" in result
    assert "alerts_generated" in result
    assert isinstance(result["flagged_products"], list)
    assert isinstance(result["scan_summary"], dict)
    assert isinstance(result["alerts_generated"], list)


@pytest.mark.anyio
async def test_inventory_check_node_scan_summary_has_counts():
    from agents.m2.nodes.inventory_check_node import inventory_check_node

    result = await inventory_check_node({"trigger_source": "manual"})
    summary = result["scan_summary"]

    for key in (
        "total_products_checked",
        "low_stock_count",
        "predicted_shortage_count",
        "slow_moving_count",
        "near_expiry_count",
        "scanned_at",
    ):
        assert key in summary, f"scan_summary missing: {key}"


@pytest.mark.anyio
async def test_inventory_check_node_flagged_products_have_detection_type():
    from agents.m2.nodes.inventory_check_node import inventory_check_node

    result = await inventory_check_node({"trigger_source": "manual"})
    for p in result["flagged_products"]:
        assert "detection_type" in p
        assert p["detection_type"] in (
            "low_stock", "predicted_shortage", "slow_moving", "near_expiry"
        )


@pytest.mark.anyio
async def test_inventory_check_node_alerts_match_flagged_count():
    from agents.m2.nodes.inventory_check_node import inventory_check_node

    result = await inventory_check_node({"trigger_source": "manual"})
    assert len(result["alerts_generated"]) == len(result["flagged_products"])

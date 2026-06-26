"""
Sprint 3 Integration Tests — Frontend Dashboard API Contracts
=============================================================

Sprint 3 built the M2 dashboard UI (InventoryTable, AlertsPanel,
RFQDraftView, PricingRecommendationsPanel). These tests verify the
API contracts the frontend depends on — correct field shapes, correct
content-types, and correct HTTP codes.

Tests cover:
  1. GET  /api/v1/m2/inventory   — InventoryTable data shape
  2. POST /api/v1/m2/analyze     — all four arrays + scan_summary
  3. GET  /api/v1/m2/rfqs        — RFQ list for the approval button
  4. GET  /api/v1/m2/pricing     — PricingRecommendationsPanel data
  5. CORS / content-type basics

Run:
    conda activate mlops
    python -m pytest tests/integration/test_m2_sprint3.py -v
"""

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.main import app

BASE = "http://test"

INVENTORY_PRODUCT_FIELDS = {
    "product_id", "sku", "name", "name_ar", "category",
    "quantity", "reorder_point", "lead_time_days",
    "avg_daily_sales", "days_until_stockout", "status",
}
INVENTORY_SUMMARY_FIELDS = {
    "total", "low_stock", "predicted_shortage",
    "slow_moving", "near_expiry", "safe",
}
VALID_STATUSES = {"safe", "low_stock", "predicted_shortage", "slow_moving", "near_expiry"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


# ═══════════════════════════════════════════════════════════════════
# 1. GET /api/v1/m2/inventory — InventoryTable
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_dashboard_inventory_returns_200():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    assert r.status_code == 200, r.text[:300]


@pytest.mark.anyio
async def test_dashboard_inventory_returns_json():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    assert "application/json" in r.headers["content-type"]


@pytest.mark.anyio
async def test_dashboard_inventory_has_products_and_summary():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    data = r.json()
    assert "products" in data
    assert "summary" in data
    assert isinstance(data["products"], list)
    assert isinstance(data["summary"], dict)


@pytest.mark.anyio
async def test_dashboard_inventory_summary_has_all_fields():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    summary = r.json()["summary"]
    for field in INVENTORY_SUMMARY_FIELDS:
        assert field in summary, f"summary missing: {field}"


@pytest.mark.anyio
async def test_dashboard_inventory_summary_counts_are_non_negative():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    summary = r.json()["summary"]
    for key in INVENTORY_SUMMARY_FIELDS:
        assert summary[key] >= 0, f"{key} must be >= 0, got {summary[key]}"


@pytest.mark.anyio
async def test_dashboard_inventory_products_have_required_fields():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    for prod in r.json()["products"]:
        for field in INVENTORY_PRODUCT_FIELDS:
            assert field in prod, f"Product missing field: {field}"


@pytest.mark.anyio
async def test_dashboard_inventory_product_status_valid():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    for prod in r.json()["products"]:
        assert prod["status"] in VALID_STATUSES, (
            f"Invalid status: {prod['status']}"
        )


@pytest.mark.anyio
async def test_dashboard_inventory_summary_total_equals_product_count():
    async with _client() as c:
        r = await c.get("/api/v1/m2/inventory")
    data = r.json()
    assert data["summary"]["total"] == len(data["products"])


# ═══════════════════════════════════════════════════════════════════
# 2. POST /api/v1/m2/analyze — AlertsPanel + RFQDraftView data
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_dashboard_analyze_returns_200():
    async with _client() as c:
        r = await c.post(
            "/api/v1/m2/analyze",
            json={"trigger_source": "manual", "language": "ar-EG"},
        )
    assert r.status_code == 200, r.text[:300]


@pytest.mark.anyio
async def test_dashboard_analyze_has_all_frontend_arrays():
    """Frontend reads: alerts, rfq_drafts, pricing_recs, scan_summary."""
    async with _client() as c:
        r = await c.post(
            "/api/v1/m2/analyze",
            json={"trigger_source": "manual", "language": "ar-EG"},
        )
    data = r.json()
    for key in ("scan_summary", "alerts", "rfq_drafts", "pricing_recs", "language"):
        assert key in data, f"analyze response missing: {key}"
    assert isinstance(data["alerts"], list)
    assert isinstance(data["rfq_drafts"], list)
    assert isinstance(data["pricing_recs"], list)


@pytest.mark.anyio
async def test_dashboard_analyze_alerts_have_frontend_fields():
    """AlertsPanel renders alert_id, alert_type, metadata."""
    async with _client() as c:
        r = await c.post(
            "/api/v1/m2/analyze",
            json={"trigger_source": "manual", "language": "en"},
        )
    for alert in r.json()["alerts"]:
        assert "alert_id" in alert
        assert "alert_type" in alert
        assert "product_id" in alert
        assert "metadata" in alert
        assert isinstance(alert["metadata"], dict)


@pytest.mark.anyio
async def test_dashboard_analyze_rfq_drafts_have_frontend_fields():
    """RFQDraftView renders rfq_id, product_id, draft_text."""
    async with _client() as c:
        r = await c.post(
            "/api/v1/m2/analyze",
            json={"trigger_source": "manual", "language": "en"},
        )
    for draft in r.json()["rfq_drafts"]:
        assert "rfq_id" in draft
        assert "product_id" in draft
        assert "draft_text" in draft


@pytest.mark.anyio
async def test_dashboard_analyze_pricing_recs_have_frontend_fields():
    """PricingRecommendationsPanel renders product_id, recommendation."""
    async with _client() as c:
        r = await c.post(
            "/api/v1/m2/analyze",
            json={"trigger_source": "manual", "language": "en"},
        )
    for rec in r.json()["pricing_recs"]:
        assert "product_id" in rec
        assert "recommendation" in rec


# ═══════════════════════════════════════════════════════════════════
# 3. GET /api/v1/m2/rfqs — Approve & Send button data
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_dashboard_rfqs_returns_200():
    async with _client() as c:
        r = await c.get("/api/v1/m2/rfqs")
    assert r.status_code == 200, r.text[:300]


@pytest.mark.anyio
async def test_dashboard_rfqs_has_list_and_total():
    async with _client() as c:
        r = await c.get("/api/v1/m2/rfqs")
    data = r.json()
    assert "rfqs" in data
    assert "total" in data
    assert isinstance(data["rfqs"], list)
    assert data["total"] == len(data["rfqs"])


@pytest.mark.anyio
async def test_dashboard_rfq_items_have_approve_button_fields():
    """
    The Approve & Send button needs: id, status, thread_id.
    """
    async with _client() as c:
        r = await c.get("/api/v1/m2/rfqs")
    for item in r.json()["rfqs"]:
        assert "id" in item
        assert "status" in item
        assert item["status"] in ("draft", "pending", "sent", "rejected", "cancelled")


# ═══════════════════════════════════════════════════════════════════
# 4. GET /api/v1/m2/pricing — PricingRecommendationsPanel
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_dashboard_pricing_returns_200():
    async with _client() as c:
        r = await c.get("/api/v1/m2/pricing")
    assert r.status_code == 200, r.text[:300]


@pytest.mark.anyio
async def test_dashboard_pricing_returns_list():
    async with _client() as c:
        r = await c.get("/api/v1/m2/pricing")
    data = r.json()
    assert isinstance(data, list), f"Expected list, got {type(data)}"


@pytest.mark.anyio
async def test_dashboard_pricing_items_have_required_fields():
    async with _client() as c:
        r = await c.get("/api/v1/m2/pricing")
    for item in r.json():
        assert "product_id" in item
        assert "recommendation" in item


# ═══════════════════════════════════════════════════════════════════
# 5. Frontend component files exist
# ═══════════════════════════════════════════════════════════════════

def test_frontend_inventory_table_component_exists():
    p = Path(__file__).resolve().parents[2] / "frontend/components/m2/InventoryTable.tsx"
    assert p.exists(), "InventoryTable.tsx not found"
    assert p.stat().st_size > 0, "InventoryTable.tsx is empty"


def test_frontend_alerts_panel_component_exists():
    p = Path(__file__).resolve().parents[2] / "frontend/components/m2/AlertsPanel.tsx"
    assert p.exists(), "AlertsPanel.tsx not found"
    assert p.stat().st_size > 0, "AlertsPanel.tsx is empty"


def test_frontend_rfq_draft_view_component_exists():
    p = Path(__file__).resolve().parents[2] / "frontend/components/m2/RFQDraftView.tsx"
    assert p.exists(), "RFQDraftView.tsx not found"
    assert p.stat().st_size > 0, "RFQDraftView.tsx is empty"


def test_frontend_pricing_panel_component_exists():
    p = Path(__file__).resolve().parents[2] / "frontend/components/m2/PricingRecommendationsPanel.tsx"
    assert p.exists(), "PricingRecommendationsPanel.tsx not found"
    assert p.stat().st_size > 0, "PricingRecommendationsPanel.tsx is empty"


def test_frontend_m2_page_exists():
    p = Path(__file__).resolve().parents[2] / "frontend/app/m2/page.tsx"
    assert p.exists(), "frontend/app/m2/page.tsx not found"
    assert p.stat().st_size > 0, "page.tsx is empty"

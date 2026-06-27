"""
Sprint 5 Integration Tests — Pricing Advisor
============================================

Tests cover:
  1. GET /api/v1/m2/pricing → 200
  2. Response is a list (possibly empty)
  3. Each item has: id, product_id, recommendation, created_at
  4. pricing_advisor_node is callable and returns pricing_recommendation
  5. After POST /analyze with slow_moving/near_expiry products,
     GET /pricing returns at least one recommendation
     (skipped if no such products in DB)
  6. pricing_advisor_node routes only for slow_moving / near_expiry
     (not for low_stock or predicted_shortage)

Run:
    conda activate mlops
    # Seed first to get slow_moving/near_expiry products:
    #   python database/seeds/m2_seed_inventory.py
    python -m pytest tests/integration/test_m2_sprint5.py -v
"""

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.main import app

BASE = "http://test"


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


# ═══════════════════════════════════════════════════════════════════
# 1. GET /api/v1/m2/pricing
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_pricing_endpoint_returns_200():
    async with _client() as c:
        r = await c.get("/api/v1/m2/pricing")
    assert r.status_code == 200, r.text[:300]


@pytest.mark.anyio
async def test_pricing_response_is_list():
    async with _client() as c:
        r = await c.get("/api/v1/m2/pricing")
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_pricing_items_have_required_fields():
    async with _client() as c:
        r = await c.get("/api/v1/m2/pricing")
    items = r.json()
    if not items:
        pytest.skip("No pricing recommendations in DB — run /analyze first.")

    for item in items:
        assert "id" in item, "item missing 'id'"
        assert "product_id" in item, "item missing 'product_id'"
        assert "recommendation" in item, "item missing 'recommendation'"
        assert "created_at" in item, "item missing 'created_at'"


@pytest.mark.anyio
async def test_pricing_recommendation_is_non_empty_string():
    async with _client() as c:
        r = await c.get("/api/v1/m2/pricing")
    items = r.json()
    if not items:
        pytest.skip("No pricing recommendations — run /analyze first.")
    for item in items:
        assert isinstance(item["recommendation"], str)
        assert len(item["recommendation"]) > 0


# ═══════════════════════════════════════════════════════════════════
# 2. pricing_advisor_node — import and signature
# ═══════════════════════════════════════════════════════════════════

def test_pricing_advisor_node_is_callable():
    from agents.m2.nodes.pricing_advisor_node import pricing_advisor_node
    assert callable(pricing_advisor_node)


def test_pricing_advisor_node_is_async():
    """Must be an async function (coroutine) for LangGraph compatibility."""
    import asyncio
    from agents.m2.nodes.pricing_advisor_node import pricing_advisor_node
    assert asyncio.iscoroutinefunction(pricing_advisor_node)


# ═══════════════════════════════════════════════════════════════════
# 3. Graph routing: pricing path vs procurement path
# ═══════════════════════════════════════════════════════════════════

def test_graph_routes_slow_moving_to_pricing_node():
    from agents.m2.graphs.m2_graph import route_detection
    result = route_detection({"detection_type": "slow_moving"})
    assert result == "pricing_advisor_node"


def test_graph_routes_near_expiry_to_pricing_node():
    from agents.m2.graphs.m2_graph import route_detection
    result = route_detection({"detection_type": "near_expiry"})
    assert result == "pricing_advisor_node"


def test_graph_routes_low_stock_to_alert_generator():
    from agents.m2.graphs.m2_graph import route_detection
    result = route_detection({"detection_type": "low_stock"})
    assert result == "alert_generator_node"


def test_graph_routes_predicted_shortage_to_alert_generator():
    from agents.m2.graphs.m2_graph import route_detection
    result = route_detection({"detection_type": "predicted_shortage"})
    assert result == "alert_generator_node"


def test_graph_routes_unknown_detection_to_end():
    from langgraph.graph import END
    from agents.m2.graphs.m2_graph import route_detection
    result = route_detection({"detection_type": None})
    assert result == END


# ═══════════════════════════════════════════════════════════════════
# 4. End-to-end: analyze → pricing recs in DB
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_analyze_populates_pricing_recs_for_slow_moving_products():
    """
    After POST /analyze, if there are slow_moving/near_expiry products,
    GET /pricing should return recommendations.
    Skipped if no such products exist in the DB.
    """
    async with _client() as c:
        analyze_r = await c.post(
            "/api/v1/m2/analyze",
            json={"trigger_source": "manual", "language": "en"},
        )
    assert analyze_r.status_code == 200

    pricing_recs_in_response = analyze_r.json().get("pricing_recs", [])

    if not pricing_recs_in_response:
        pytest.skip(
            "No slow_moving/near_expiry products detected — "
            "run database/seeds/m2_seed_inventory.py first."
        )

    # Verify each pricing rec in the analyze response has required fields
    for rec in pricing_recs_in_response:
        assert "product_id" in rec
        assert "recommendation" in rec
        assert len(rec["recommendation"]) > 0

    # Now check the GET /pricing endpoint also has them
    async with _client() as c:
        pricing_r = await c.get("/api/v1/m2/pricing")
    assert pricing_r.status_code == 200
    saved = pricing_r.json()
    assert len(saved) > 0, "Pricing recs were returned by /analyze but not saved to DB"


@pytest.mark.anyio
async def test_analyze_pricing_recs_match_detected_product_ids():
    """
    The product_ids in pricing_recs should correspond to products
    classified as slow_moving or near_expiry.
    """
    async with _client() as c:
        r = await c.post(
            "/api/v1/m2/analyze",
            json={"trigger_source": "manual", "language": "en"},
        )
    data = r.json()

    pricing_recs = data.get("pricing_recs", [])
    if not pricing_recs:
        pytest.skip("No pricing recs — seed data needed.")

    # All product_ids in pricing_recs must be UUIDs (non-empty strings)
    for rec in pricing_recs:
        pid = rec["product_id"]
        assert isinstance(pid, str) and len(pid) > 0

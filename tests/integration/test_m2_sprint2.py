"""
Sprint 2 Integration Tests — LLM Nodes: Alerts & RFQ Draft
===========================================================

Tests cover:
  1. POST /api/v1/m2/analyze with trigger_source=manual → 200
  2. POST /api/v1/m2/analyze with trigger_source=cron   → 200
  3. Language echoing: language=en → response.language=en
  4. Language echoing: language=ar-EG → response.language=ar-EG
  5. Response schema: scan_summary, alerts, rfq_drafts, pricing_recs, language
  6. scan_summary has all required keys + numeric values
  7. Empty/invalid request body → 422 (if body is required)
  8. alert_type in each alert is a valid detection type
  9. rfq_drafts have rfq_id, product_id, draft_text
  10. alert_generator_node + rfq_builder_node import without error

Run:
    conda activate mlops
    python -m pytest tests/integration/test_m2_sprint2.py -v
"""

import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.main import app

BASE = "http://test"
VALID_ALERT_TYPES = {"low_stock", "predicted_shortage", "slow_moving", "near_expiry"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


# ═══════════════════════════════════════════════════════════════════
# 1. POST /analyze — basic HTTP contract
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_analyze_manual_trigger_returns_200():
    async with _client() as c:
        r = await c.post("/api/v1/m2/analyze", json={"trigger_source": "manual", "language": "en"})
    assert r.status_code == 200, r.text[:300]


@pytest.mark.anyio
async def test_analyze_cron_trigger_returns_200():
    async with _client() as c:
        r = await c.post("/api/v1/m2/analyze", json={"trigger_source": "cron", "language": "en"})
    assert r.status_code == 200, r.text[:300]


@pytest.mark.anyio
async def test_analyze_defaults_work_with_empty_body():
    """Both fields have defaults (manual + ar-EG), so empty body should succeed."""
    async with _client() as c:
        r = await c.post("/api/v1/m2/analyze", json={})
    assert r.status_code == 200, r.text[:300]


# ═══════════════════════════════════════════════════════════════════
# 2. Language echoing
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_analyze_language_en_echoed():
    async with _client() as c:
        r = await c.post("/api/v1/m2/analyze", json={"trigger_source": "manual", "language": "en"})
    assert r.json()["language"] == "en"


@pytest.mark.anyio
async def test_analyze_language_ar_echoed():
    async with _client() as c:
        r = await c.post("/api/v1/m2/analyze", json={"trigger_source": "manual", "language": "ar-EG"})
    assert r.json()["language"] == "ar-EG"


# ═══════════════════════════════════════════════════════════════════
# 3. Response schema
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_analyze_response_has_all_top_level_keys():
    async with _client() as c:
        r = await c.post("/api/v1/m2/analyze", json={"trigger_source": "manual", "language": "en"})
    data = r.json()
    for key in ("scan_summary", "alerts", "rfq_drafts", "pricing_recs", "language"):
        assert key in data, f"Response missing key: {key}"


@pytest.mark.anyio
async def test_analyze_response_lists_are_lists():
    async with _client() as c:
        r = await c.post("/api/v1/m2/analyze", json={"trigger_source": "manual", "language": "en"})
    data = r.json()
    assert isinstance(data["alerts"], list)
    assert isinstance(data["rfq_drafts"], list)
    assert isinstance(data["pricing_recs"], list)


@pytest.mark.anyio
async def test_analyze_scan_summary_has_required_keys():
    async with _client() as c:
        r = await c.post("/api/v1/m2/analyze", json={"trigger_source": "manual", "language": "en"})
    summary = r.json()["scan_summary"]
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
async def test_analyze_scan_summary_total_is_non_negative():
    async with _client() as c:
        r = await c.post("/api/v1/m2/analyze", json={"trigger_source": "manual", "language": "en"})
    summary = r.json()["scan_summary"]
    assert summary["total_products_checked"] >= 0


# ═══════════════════════════════════════════════════════════════════
# 4. Alert schema validation
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_analyze_alerts_have_required_fields():
    async with _client() as c:
        r = await c.post("/api/v1/m2/analyze", json={"trigger_source": "manual", "language": "en"})
    for alert in r.json()["alerts"]:
        assert "alert_id" in alert
        assert "product_id" in alert
        assert "alert_type" in alert
        assert "metadata" in alert


@pytest.mark.anyio
async def test_analyze_alert_type_is_valid():
    async with _client() as c:
        r = await c.post("/api/v1/m2/analyze", json={"trigger_source": "manual", "language": "en"})
    for alert in r.json()["alerts"]:
        assert alert["alert_type"] in VALID_ALERT_TYPES, (
            f"Unexpected alert_type: {alert['alert_type']}"
        )


# ═══════════════════════════════════════════════════════════════════
# 5. RFQ draft schema validation (only when drafts are generated)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_analyze_rfq_drafts_have_required_fields():
    async with _client() as c:
        r = await c.post("/api/v1/m2/analyze", json={"trigger_source": "manual", "language": "en"})
    for draft in r.json()["rfq_drafts"]:
        assert "rfq_id" in draft, "rfq_draft missing rfq_id"
        assert "product_id" in draft, "rfq_draft missing product_id"
        assert "draft_text" in draft, "rfq_draft missing draft_text"
        assert len(draft["draft_text"]) > 0, "draft_text is empty"


@pytest.mark.anyio
async def test_analyze_pricing_recs_have_required_fields():
    async with _client() as c:
        r = await c.post("/api/v1/m2/analyze", json={"trigger_source": "manual", "language": "en"})
    for rec in r.json()["pricing_recs"]:
        assert "product_id" in rec
        assert "recommendation" in rec
        assert len(rec["recommendation"]) > 0


# ═══════════════════════════════════════════════════════════════════
# 6. Node imports
# ═══════════════════════════════════════════════════════════════════

def test_alert_generator_node_imports():
    from agents.m2.nodes.alert_generator_node import alert_generator_node
    assert callable(alert_generator_node)


def test_rfq_builder_node_imports():
    from agents.m2.nodes.rfq_builder_node import rfq_builder_node
    assert callable(rfq_builder_node)

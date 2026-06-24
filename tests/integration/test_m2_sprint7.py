"""
Sprint 7 Integration Tests — Offer Intake + Offer Analysis
==========================================================

Tests cover:
  1. POST /api/v1/m2/offers — 404 for unknown RFQ
  2. POST /api/v1/m2/offers — 422 for missing/invalid offer data
  3. POST /api/v1/m2/offers — 409 for RFQ not in 'sent' status
  4. GET  /api/v1/m2/offers/{rfq_id} — returns empty list for new RFQ
  5. Full flow: analyze → approve → submit offers → get recommendation → final approve
     (skipped if no low_stock/predicted_shortage products exist)

Run:
    conda activate mlops
    # First seed DB:  python database/seeds/m2_seed_inventory.py
    python -m pytest tests/integration/test_m2_sprint7.py -v
"""

import sys
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.main import app

BASE = "http://test"
MOCK_OFFERS = [
    {
        "vendor_name": "Alpha Supplies Co.",
        "price_per_unit": 45.50,
        "lead_time_days": 7,
        "payment_terms": "Net 30",
        "notes": "Includes free delivery",
    },
    {
        "vendor_name": "Beta Trading LLC",
        "price_per_unit": 42.00,
        "lead_time_days": 14,
        "payment_terms": "Net 60",
        "notes": "Bulk discount available",
    },
    {
        "vendor_name": "Gamma Distributors",
        "price_per_unit": 48.75,
        "lead_time_days": 5,
        "payment_terms": "Immediate payment",
        "notes": "Premium quality guarantee",
    },
]


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE)


# ═══════════════════════════════════════════════════════════════════
# 1. POST /offers — 404 on unknown RFQ
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_submit_offers_unknown_rfq_returns_404():
    fake_id = str(uuid.uuid4())
    async with _client() as c:
        r = await c.post(
            "/api/v1/m2/offers",
            json={"rfq_id": fake_id, "offers": [MOCK_OFFERS[0]]},
        )
    assert r.status_code == 404, r.text[:300]


# ═══════════════════════════════════════════════════════════════════
# 2. POST /offers — 422 on missing offers list
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_submit_offers_empty_list_returns_422():
    fake_id = str(uuid.uuid4())
    async with _client() as c:
        r = await c.post(
            "/api/v1/m2/offers",
            json={"rfq_id": fake_id, "offers": []},
        )
    assert r.status_code == 422, r.text[:300]


@pytest.mark.anyio
async def test_submit_offers_negative_price_returns_422():
    fake_id = str(uuid.uuid4())
    async with _client() as c:
        r = await c.post(
            "/api/v1/m2/offers",
            json={
                "rfq_id": fake_id,
                "offers": [{"vendor_name": "X", "price_per_unit": -5.0}],
            },
        )
    assert r.status_code == 422, r.text[:300]


# ═══════════════════════════════════════════════════════════════════
# 3. GET /offers/{rfq_id} — always returns a list (empty for unknown)
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_list_offers_unknown_rfq_returns_empty():
    fake_id = str(uuid.uuid4())
    async with _client() as c:
        r = await c.get(f"/api/v1/m2/offers/{fake_id}")
    assert r.status_code == 200, r.text[:300]
    assert r.json() == []


# ═══════════════════════════════════════════════════════════════════
# 4. POST /offers — 409 when RFQ is not 'sent'
#    Creates a real draft RFQ via /analyze, then tries to submit offers
#    before approving it (status=draft → should 409).
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_submit_offers_on_draft_rfq_returns_409():
    # Trigger analyze to create draft RFQs
    async with _client() as c:
        analyze_r = await c.post(
            "/api/v1/m2/analyze",
            json={"trigger_source": "manual", "language": "en"},
        )
    assert analyze_r.status_code == 200

    async with _client() as c:
        list_r = await c.get("/api/v1/m2/rfqs")
    draft_rfqs = [r for r in list_r.json()["rfqs"] if r["status"] == "draft"]

    if not draft_rfqs:
        pytest.skip("No draft RFQs — run seed script first.")

    rfq_id = draft_rfqs[0]["id"]

    # Submit offers while RFQ is still draft → 409
    async with _client() as c:
        r = await c.post(
            "/api/v1/m2/offers",
            json={"rfq_id": rfq_id, "offers": [MOCK_OFFERS[0]]},
        )
    assert r.status_code == 409, r.text[:300]


# ═══════════════════════════════════════════════════════════════════
# 5. Full async loop: analyze → approve → submit offers → final approve
# ═══════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_full_async_procurement_loop():
    """
    Complete Sprint 7 end-to-end flow:
      1. POST /analyze          → get rfq_id (procurement product needed)
      2. POST /rfqs/{id}/approve (approved) → graph pauses at await_offers_node
      3. POST /offers           → submit 3 mock offers → offer_analysis runs
                                  → recommended_offer returned
                                  → graph pauses at final_approval_node
      4. POST /rfqs/{id}/approve (approved) → final approval
      5. GET  /offers/{rfq_id}  → 3 offers saved in DB
    """
    # Step 1 — trigger analysis
    async with _client() as c:
        analyze_r = await c.post(
            "/api/v1/m2/analyze",
            json={"trigger_source": "manual", "language": "en"},
        )
    assert analyze_r.status_code == 200

    async with _client() as c:
        list_r = await c.get("/api/v1/m2/rfqs")
    draft_rfqs = [r for r in list_r.json()["rfqs"] if r["status"] == "draft"]

    if not draft_rfqs:
        pytest.skip("No draft RFQs — run seed script first.")

    rfq = draft_rfqs[0]
    rfq_id = rfq["id"]

    # Step 2 — first approval (approve RFQ to send)
    async with _client() as c:
        approve_r = await c.post(
            f"/api/v1/m2/rfqs/{rfq_id}/approve",
            json={"approval_status": "approved", "notes": "Looks good."},
        )
    assert approve_r.status_code == 200, approve_r.text[:300]
    assert approve_r.json()["sent"] is True

    # RFQ should now be 'sent'
    async with _client() as c:
        list_r2 = await c.get("/api/v1/m2/rfqs")
    sent_rfq = next((r for r in list_r2.json()["rfqs"] if r["id"] == rfq_id), None)
    assert sent_rfq is not None
    assert sent_rfq["status"] == "sent", f"Expected 'sent', got '{sent_rfq['status']}'"

    # Step 3 — submit 3 offers
    async with _client() as c:
        offers_r = await c.post(
            "/api/v1/m2/offers",
            json={"rfq_id": rfq_id, "offers": MOCK_OFFERS, "language": "en"},
        )
    assert offers_r.status_code == 200, offers_r.text[:300]

    offers_data = offers_r.json()
    assert offers_data["offers_saved"] == 3
    assert "rfq_id" in offers_data
    assert "message" in offers_data

    # If m2_graph is available (checkpointer running), we get analysis
    if offers_data.get("analysis_triggered"):
        assert offers_data["recommended_offer"] is not None
        rec = offers_data["recommended_offer"]
        assert "vendor_name" in rec
        assert rec["price_per_unit"] > 0
        assert "justification" in rec

    # Step 4 — verify offers saved in DB
    async with _client() as c:
        db_offers_r = await c.get(f"/api/v1/m2/offers/{rfq_id}")
    assert db_offers_r.status_code == 200
    db_offers = db_offers_r.json()
    assert len(db_offers) == 3

    for offer in db_offers:
        assert "id" in offer
        assert offer["price_per_unit"] > 0

    # Step 5 — final approval (if analysis was triggered)
    if offers_data.get("analysis_triggered"):
        async with _client() as c:
            final_r = await c.post(
                f"/api/v1/m2/rfqs/{rfq_id}/approve",
                json={"approval_status": "approved", "notes": "Best price accepted."},
            )
        assert final_r.status_code == 200, final_r.text[:300]
        final_data = final_r.json()
        assert final_data["approval_status"] == "approved"
